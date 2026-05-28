#!/usr/bin/env python3
"""
setup.py — 初始化 Lakehouse 环境并上传数据

执行内容：
  1. 创建四个 Schema（ecommerce_ods/dwd/dws/ads）
  2. 创建 Volume（ecommerce_ods.ecommerce_vol）
  3. 上传 data/sample/ 或 datasets/ 中的 CSV 文件到 Volume
  4. 建表（ODS / DWD / DWS / ADS）

用法：
  cd hive2lakehouse-ecommerce-events
  python 03_lakehouse/setup.py                  # 上传 data/sample/（快速验证）
  python 03_lakehouse/setup.py --full           # 上传 datasets/（完整数据集）
  python 03_lakehouse/setup.py --skip-upload    # 只建表，不上传
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(line_buffering=True)

FULL_DATA   = "--full" in sys.argv
SKIP_UPLOAD = "--skip-upload" in sys.argv

try:
    from clickzetta.zettapark.session import Session
except ImportError:
    print("请先安装依赖: pip install clickzetta_zettapark_python python-dotenv")
    sys.exit(1)

from includes.configuration import (
    SCHEMA_NAME, VOLUME_NAME, VOLUME_PATH,
    ods_schema, dwd_schema, dws_schema, ads_schema,
)

REPO_ROOT    = Path(__file__).parent.parent
SAMPLE_DIR   = REPO_ROOT / "data" / "sample"
DATASETS_DIR = REPO_ROOT / "datasets"
SQL_DIR      = Path(__file__).parent / "sql"


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


def run(session, stmt, label=""):
    try:
        session.sql(stmt).collect()
        if label:
            print(f"  OK: {label}")
    except Exception as e:
        print(f"  WARN [{label}]: {e}")


def main():
    session = get_session()
    try:
        print("=== 1. 创建 Schema ===")
        for schema in [ods_schema, dwd_schema, dws_schema, ads_schema]:
            run(session, f"CREATE SCHEMA IF NOT EXISTS {schema}", schema)

        print("\n=== 2. 创建 Volume ===")
        run(session, f"CREATE VOLUME IF NOT EXISTS {ods_schema}.{VOLUME_NAME}",
            f"{ods_schema}.{VOLUME_NAME}")

        print("\n=== 3. 建表 ===")
        run(session, f"""
            CREATE TABLE IF NOT EXISTS {ods_schema}.ods_events_raw (
                event_time STRING, event_type STRING, product_id BIGINT,
                category_id BIGINT, category_code STRING, brand STRING,
                price DOUBLE, user_id BIGINT, user_session STRING
            ) PARTITIONED BY (dt STRING)
        """, "ods_events_raw")

        run(session, f"""
            CREATE TABLE IF NOT EXISTS {dwd_schema}.dwd_events_clean (
                event_ts TIMESTAMP, event_type STRING, product_id BIGINT,
                category_id BIGINT, category_l1 STRING, category_l2 STRING,
                category_l3 STRING, brand STRING, price DOUBLE,
                user_id BIGINT, user_session STRING
            ) PARTITIONED BY (dt STRING)
        """, "dwd_events_clean")

        run(session, f"""
            CREATE TABLE IF NOT EXISTS {dws_schema}.dws_user_behavior (
                user_id BIGINT, view_cnt INT, cart_cnt INT,
                purchase_cnt INT, purchase_amt DOUBLE
            ) PARTITIONED BY (dt STRING)
        """, "dws_user_behavior")

        run(session, f"""
            CREATE TABLE IF NOT EXISTS {ads_schema}.ads_funnel_daily (
                view_users BIGINT, cart_users BIGINT, purchase_users BIGINT,
                view_to_cart_rate DOUBLE, cart_to_purchase_rate DOUBLE
            ) PARTITIONED BY (dt STRING)
        """, "ads_funnel_daily")

        if not SKIP_UPLOAD:
            print("\n=== 4. 上传数据到 Volume ===")
            data_dir = DATASETS_DIR if FULL_DATA else SAMPLE_DIR
            csv_files = list(data_dir.glob("*.csv"))
            if not csv_files:
                print(f"  [WARN] {data_dir} 中没有 CSV 文件")
            else:
                vol_dest = f"{VOLUME_PATH}/raw/"
                for f in csv_files:
                    size_kb = f.stat().st_size // 1024
                    print(f"  上传 {f.name} ({size_kb} KB)...", end=" ", flush=True)
                    session.file.put(str(f), vol_dest, auto_compress=False, overwrite=True)
                    print("完成")

    finally:
        session.close()

    print("\n初始化完成。接下来运行：python 03_lakehouse/e2e.py")


if __name__ == "__main__":
    main()
