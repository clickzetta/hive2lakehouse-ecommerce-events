#!/usr/bin/env python3
"""
e2e.py — 端到端验证：上传数据 → ODS → DWD → DWS/ADS → 断言检查

用法：
  python 03_lakehouse/e2e.py               # 完整流程
  python 03_lakehouse/e2e.py --skip-upload # 跳过上传（文件已在 Volume）
  python 03_lakehouse/e2e.py --reset       # 先清空所有表再跑
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(line_buffering=True)

SKIP_UPLOAD = "--skip-upload" in sys.argv
DO_RESET    = "--reset" in sys.argv

try:
    from clickzetta.zettapark.session import Session
except ImportError:
    print("请先安装依赖: pip install clickzetta_zettapark_python python-dotenv")
    sys.exit(1)

from includes.configuration import (
    SCHEMA_NAME, VOLUME_NAME, VOLUME_PATH,
    ods_schema, dwd_schema, dws_schema, ads_schema,
)

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "sample"

EXPECTED = {
    "ods_row_count":      19,
    "dwd_row_count":      19,
    "dws_row_count":       6,
    "funnel_view_users":   6,
    "funnel_cart_users":   4,
    "funnel_purchase_users": 3,
    "funnel_view_to_cart": 0.6667,
    "funnel_cart_to_purchase": 0.75,
    "top_spender_user_id": 526595547,
    "top_spender_amt":     1422.0,
}

passed = 0
failed = 0


def check(label, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  ✓ {label}: {actual}")
        passed += 1
    else:
        print(f"  ✗ {label}: got {actual}, expected {expected}")
        failed += 1


def get_session():
    required = ["CLICKZETTA_SERVICE", "CLICKZETTA_INSTANCE", "CLICKZETTA_WORKSPACE",
                "CLICKZETTA_USERNAME", "CLICKZETTA_PASSWORD", "CLICKZETTA_SCHEMA"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"[ERROR] .env 缺少必填项: {', '.join(missing)}")
        sys.exit(1)
    return Session.builder.configs({
        "username":  os.environ["CLICKZETTA_USERNAME"],
        "password":  os.environ["CLICKZETTA_PASSWORD"],
        "service":   os.environ["CLICKZETTA_SERVICE"],
        "instance":  os.environ["CLICKZETTA_INSTANCE"],
        "workspace": os.environ["CLICKZETTA_WORKSPACE"],
        "schema":    SCHEMA_NAME,
        "vcluster":  os.environ.get("CLICKZETTA_VCLUSTER", "default_ap"),
    }).create()


def sql(session, stmt):
    return session.sql(stmt).collect()


def main():
    session = get_session()
    try:
        if DO_RESET:
            print("=== 清空所有表 ===")
            for t in [f"{ods_schema}.ods_events_staging", f"{ods_schema}.ods_events_raw",
                      f"{dwd_schema}.dwd_events_clean",
                      f"{dws_schema}.dws_user_behavior", f"{ads_schema}.ads_funnel_daily"]:
                sql(session, f"TRUNCATE TABLE {t}")
                print(f"  清空 {t}")

        if not SKIP_UPLOAD:
            print("\n=== 上传 sample 数据 ===")
            vol_dest = f"{VOLUME_PATH}/raw/"
            for f in SAMPLE_DIR.glob("*.csv"):
                print(f"  上传 {f.name}...", end=" ", flush=True)
                session.file.put(str(f), vol_dest, auto_compress=False, overwrite=True)
                print("完成")

        print("\n=== COPY INTO ODS ===")
        # 先建 staging 表（无分区，列顺序与 CSV 一致）
        sql(session, f"""
            CREATE TABLE IF NOT EXISTS {ods_schema}.ods_events_staging (
                event_time STRING, event_type STRING, product_id BIGINT,
                category_id BIGINT, category_code STRING, brand STRING,
                price DOUBLE, user_id BIGINT, user_session STRING
            )
        """)
        sql(session, f"TRUNCATE TABLE {ods_schema}.ods_events_staging")
        # COPY INTO staging（Lakehouse 不支持 $1 列引用，直接按列顺序映射）
        sql(session, f"""
            COPY INTO {ods_schema}.ods_events_staging
            FROM VOLUME {ods_schema}.{VOLUME_NAME}
            USING CSV
            OPTIONS ('header' = 'true', 'nullValue' = '')
            FILES ('raw/events_sample.csv')
            ON_ERROR = CONTINUE
        """)
        # staging → 分区主表（过滤脏数据，提取分区列）
        sql(session, f"""
            INSERT OVERWRITE TABLE {ods_schema}.ods_events_raw PARTITION (dt)
            SELECT event_time, event_type, product_id, category_id,
                category_code, brand, price, user_id, user_session,
                SUBSTR(event_time, 1, 10) AS dt
            FROM {ods_schema}.ods_events_staging
            WHERE event_type IN ('view', 'cart', 'purchase') AND user_id > 100000
        """)
        ods_cnt = sql(session, f"SELECT COUNT(*) FROM {ods_schema}.ods_events_raw")[0][0]
        print(f"  ODS 行数: {ods_cnt}")

        print("\n=== ODS → DWD ===")
        sql(session, f"""
            INSERT OVERWRITE TABLE {dwd_schema}.dwd_events_clean PARTITION (dt)
            SELECT
                CAST(REGEXP_REPLACE(event_time, ' UTC$', '') AS TIMESTAMP),
                event_type, product_id, category_id,
                SPLIT(category_code, '\\.')[0],
                CASE WHEN SIZE(SPLIT(category_code, '\\.')) > 1
                     THEN SPLIT(category_code, '\\.')[1] END,
                CASE WHEN SIZE(SPLIT(category_code, '\\.')) > 2
                     THEN SPLIT(category_code, '\\.')[2] END,
                brand, price, user_id, user_session, dt
            FROM {ods_schema}.ods_events_raw
            WHERE price > 0 OR event_type != 'purchase'
        """)
        dwd_cnt = sql(session, f"SELECT COUNT(*) FROM {dwd_schema}.dwd_events_clean")[0][0]
        print(f"  DWD 行数: {dwd_cnt}")

        print("\n=== DWD → DWS ===")
        sql(session, f"""
            INSERT OVERWRITE TABLE {dws_schema}.dws_user_behavior PARTITION (dt)
            SELECT user_id,
                SUM(CASE WHEN event_type='view'     THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type='cart'     THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END),
                SUM(CASE WHEN event_type='purchase' THEN price ELSE 0 END),
                dt
            FROM {dwd_schema}.dwd_events_clean GROUP BY user_id, dt
        """)
        dws_cnt = sql(session, f"SELECT COUNT(*) FROM {dws_schema}.dws_user_behavior")[0][0]
        print(f"  DWS 行数: {dws_cnt}")

        print("\n=== DWD → ADS ===")
        sql(session, f"""
            INSERT OVERWRITE TABLE {ads_schema}.ads_funnel_daily PARTITION (dt)
            SELECT
                COUNT(DISTINCT CASE WHEN event_type='view'     THEN user_id END),
                COUNT(DISTINCT CASE WHEN event_type='cart'     THEN user_id END),
                COUNT(DISTINCT CASE WHEN event_type='purchase' THEN user_id END),
                ROUND(COUNT(DISTINCT CASE WHEN event_type='cart'     THEN user_id END)*1.0/
                      NULLIF(COUNT(DISTINCT CASE WHEN event_type='view' THEN user_id END),0),4),
                ROUND(COUNT(DISTINCT CASE WHEN event_type='purchase' THEN user_id END)*1.0/
                      NULLIF(COUNT(DISTINCT CASE WHEN event_type='cart' THEN user_id END),0),4),
                dt
            FROM {dwd_schema}.dwd_events_clean GROUP BY dt
        """)
        funnel = sql(session, f"SELECT * FROM {ads_schema}.ads_funnel_daily")[0]
        print(f"  漏斗: view={funnel[0]}, cart={funnel[1]}, purchase={funnel[2]}, "
              f"v→c={funnel[3]}, c→p={funnel[4]}")

        print("\n=== 断言检查 ===")
        check("ODS 行数",            ods_cnt,    EXPECTED["ods_row_count"])
        check("DWD 行数",            dwd_cnt,    EXPECTED["dwd_row_count"])
        check("DWS 行数",            dws_cnt,    EXPECTED["dws_row_count"])
        check("漏斗 view_users",     funnel[0],  EXPECTED["funnel_view_users"])
        check("漏斗 cart_users",     funnel[1],  EXPECTED["funnel_cart_users"])
        check("漏斗 purchase_users", funnel[2],  EXPECTED["funnel_purchase_users"])
        check("漏斗 view→cart 率",   funnel[3],  EXPECTED["funnel_view_to_cart"])
        check("漏斗 cart→purchase 率", funnel[4], EXPECTED["funnel_cart_to_purchase"])

        top = sql(session, f"""
            SELECT user_id, purchase_amt FROM {dws_schema}.dws_user_behavior
            ORDER BY purchase_amt DESC LIMIT 1
        """)[0]
        check("最高消费用户 ID",  top[0], EXPECTED["top_spender_user_id"])
        check("最高消费金额",     top[1], EXPECTED["top_spender_amt"])

    finally:
        session.close()

    total = passed + failed
    print(f"\n{'='*40}")
    print(f"验证结果：{passed}/{total} 通过")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
