-- ODS 层：原始事件日志
-- 用 CSV SerDe 加载原始文件，按日期分区，存储为 ORC
-- 这是 Hive 迁移的典型模式：staging 表用 TextFile/CSV 接收原始数据，再 INSERT INTO 到 ORC 表

-- 1. 外部 staging 表（TextFile + CSV SerDe，直接映射原始 CSV）
CREATE DATABASE IF NOT EXISTS ecommerce;

CREATE EXTERNAL TABLE IF NOT EXISTS ecommerce.ods_events_staging (
    event_time  STRING,
    event_type  STRING,
    product_id  BIGINT,
    category_id BIGINT,
    category_code STRING,
    brand       STRING,
    price       DOUBLE,
    user_id     BIGINT,
    user_session STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    "separatorChar" = ",",
    "quoteChar"     = "\"",
    "escapeChar"    = "\\"
)
STORED AS TEXTFILE
TBLPROPERTIES ("skip.header.line.count"="1");

-- 2. ODS 主表（ORC 格式，按日期分区）
CREATE TABLE IF NOT EXISTS ecommerce.ods_events_raw (
    event_time  STRING,
    event_type  STRING,
    product_id  BIGINT,
    category_id BIGINT,
    category_code STRING,
    brand       STRING,
    price       DOUBLE,
    user_id     BIGINT,
    user_session STRING
)
PARTITIONED BY (dt STRING)
STORED AS ORC
TBLPROPERTIES ("orc.compress"="SNAPPY");
