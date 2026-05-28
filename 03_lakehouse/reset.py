#!/usr/bin/env python3
"""
reset.py — 清空所有表（保留 Schema 和 Volume，可直接重跑 e2e.py）

用法：
  python 03_lakehouse/reset.py
  python 03_lakehouse/reset.py --dry-run
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DRY_RUN = "--dry-run" in sys.argv

sys.path.insert(0, str(Path(__file__).parent))

try:
    import clickzetta
except ImportError:
    print("请先安装依赖: pip install clickzetta_zettapark_python python-dotenv")
    sys.exit(1)

from includes.configuration import (
    SCHEMA_NAME, ods_schema, dwd_schema, dws_schema, ads_schema,
)

TABLES = [
    f"{ods_schema}.ods_events_staging",
    f"{ods_schema}.ods_events_raw",
    f"{dwd_schema}.dwd_events_clean",
    f"{dws_schema}.dws_user_behavior",
    f"{ads_schema}.ads_funnel_daily",
]


def get_conn():
    required = ["CLICKZETTA_SERVICE", "CLICKZETTA_INSTANCE", "CLICKZETTA_WORKSPACE",
                "CLICKZETTA_USERNAME", "CLICKZETTA_PASSWORD", "CLICKZETTA_SCHEMA"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"[ERROR] .env 缺少必填项: {', '.join(missing)}")
        sys.exit(1)
    return clickzetta.connect(
        service=os.environ["CLICKZETTA_SERVICE"],
        instance=os.environ["CLICKZETTA_INSTANCE"],
        workspace=os.environ["CLICKZETTA_WORKSPACE"],
        username=os.environ["CLICKZETTA_USERNAME"],
        password=os.environ["CLICKZETTA_PASSWORD"],
        schema=SCHEMA_NAME,
        vcluster=os.environ.get("CLICKZETTA_VCLUSTER", "default_ap"),
    )


def execute(cur, stmt):
    if DRY_RUN:
        print(f"  [DRY] {stmt}")
        return
    try:
        cur.execute(stmt)
        print(f"  OK: {stmt[:80]}")
    except Exception as e:
        print(f"  WARN: {e}")


def main():
    if DRY_RUN:
        print("=== DRY RUN — 不会实际删除任何数据 ===\n")

    conn = get_conn()
    cur = conn.cursor()
    try:
        for table in TABLES:
            print(f"清空 {table} ...")
            execute(cur, f"TRUNCATE TABLE IF EXISTS {table}")
    finally:
        cur.close()
        conn.close()

    if DRY_RUN:
        print("\n=== DRY RUN 完成，未执行任何操作 ===")
    else:
        print("\n清空完成。重新跑流程：python 03_lakehouse/e2e.py --skip-upload")


if __name__ == "__main__":
    main()
