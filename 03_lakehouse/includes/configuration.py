import os

SCHEMA_NAME  = os.environ.get("CLICKZETTA_SCHEMA", "public")
VOLUME_NAME  = os.environ.get("CLICKZETTA_VOLUME", "ecommerce_vol")
VOLUME_PATH  = f"vol://{SCHEMA_NAME}.{VOLUME_NAME}"

ods_schema = "ecommerce_ods"
dwd_schema = "ecommerce_dwd"
dws_schema = "ecommerce_dws"
ads_schema = "ecommerce_ads"
