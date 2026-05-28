-- Lakehouse ODS 层建表
-- 迁移说明：
--   Hive: ROW FORMAT SERDE 'OpenCSVSerde' + STORED AS TEXTFILE (staging)
--         + STORED AS ORC + PARTITIONED BY (dt STRING) (主表)
--   Lakehouse: 无需声明存储格式（原生 Parquet），PARTITIONED BY 语法不变
--              无 EXTERNAL TABLE 概念，数据通过 COPY INTO 从 Volume 加载
--              无需 staging 表，直接 COPY INTO 到分区主表

CREATE SCHEMA IF NOT EXISTS ecommerce_ods;

CREATE TABLE IF NOT EXISTS ecommerce_ods.ods_events_raw (
    event_time    STRING,
    event_type    STRING,
    product_id    BIGINT,
    category_id   BIGINT,
    category_code STRING,
    brand         STRING,
    price         DOUBLE,
    user_id       BIGINT,
    user_session  STRING
)
PARTITIONED BY (dt STRING);
