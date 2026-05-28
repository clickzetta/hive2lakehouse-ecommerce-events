#!/usr/bin/env python3
"""
teardown.py — 完整清理：删除所有 Schema 和 Volume（不可恢复）

用法：
  python 03_lakehouse/teardown.py
  python 03_lakehouse/teardown.py --dry-run
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DRY_RUN = "--dry-run" in sys.argv

sys.path.insert(0, str(Path(__file__).parent))

try:
    from clickzetta.zettapark.session import Session
except ImportError:
    print("请先安装依赖: pip install clickzetta_zettapark_python python-dotenv")
    sys.exit(1)

from includes.configuration import (
    SCHEMA_NAME, VOLUME_NAME,
    ods_schema, dwd_schema, dws_schema, ads_schema,
)


def execute(session, stmt, label=""):
    if DRY_RUN:
        print(f"  [DRY] {stmt}")
        return
    try:
        session.sql(stmt).collect()
        print(f"  OK: {label or stmt[:80]}")
    except Exception as e:
        print(f"  WARN [{label}]: {e}")


def main():
    if DRY_RUN:
        print("=== DRY RUN — 不会实际删除任何对象 ===\n")

    session = Session.builder.configs({
        "username":  os.environ["CLICKZETTA_USERNAME"],
        "password":  os.environ["CLICKZETTA_PASSWORD"],
        "service":   os.environ["CLICKZETTA_SERVICE"],
        "instance":  os.environ["CLICKZETTA_INSTANCE"],
        "workspace": os.environ["CLICKZETTA_WORKSPACE"],
        "schema":    SCHEMA_NAME,
        "vcluster":  os.environ.get("CLICKZETTA_VCLUSTER", "default_ap"),
    }).create()

    try:
        print(f"删除 Volume {ods_schema}.{VOLUME_NAME} ...")
        execute(session, f"DROP VOLUME IF EXISTS {ods_schema}.{VOLUME_NAME}",
                f"{ods_schema}.{VOLUME_NAME}")

        for schema in [ods_schema, dwd_schema, dws_schema, ads_schema]:
            print(f"删除 Schema {schema} (CASCADE) ...")
            execute(session, f"DROP SCHEMA IF EXISTS {schema} CASCADE", schema)
    finally:
        session.close()

    if DRY_RUN:
        print("\n=== DRY RUN 完成，未执行任何删除 ===")
    else:
        print("\n完整清理完成。重新初始化：python 03_lakehouse/setup.py")


if __name__ == "__main__":
    main()
