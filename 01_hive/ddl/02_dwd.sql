-- DWD 层：清洗后事件表
-- 分桶表：按 user_id 分 8 桶，加速用户维度 JOIN
-- 同时按日期分区，兼顾时间范围过滤

SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;
SET hive.enforce.bucketing=true;

CREATE TABLE IF NOT EXISTS ecommerce.dwd_events_clean (
    event_ts    TIMESTAMP,
    event_type  STRING,
    product_id  BIGINT,
    category_id BIGINT,
    category_l1 STRING,
    category_l2 STRING,
    category_l3 STRING,
    brand       STRING,
    price       DOUBLE,
    user_id     BIGINT,
    user_session STRING
)
PARTITIONED BY (dt STRING)
CLUSTERED BY (user_id) INTO 8 BUCKETS
STORED AS ORC
TBLPROPERTIES ("orc.compress"="SNAPPY");
