-- Lakehouse DWD 层建表
-- 迁移说明：
--   Hive: CLUSTERED BY (user_id) INTO 8 BUCKETS + STORED AS ORC
--         SET hive.enforce.bucketing=true 才能保证分桶写入
--   Lakehouse: 不支持分桶，改用 Z-Order 索引加速 user_id 维度查询
--              无需任何 SET 语句，动态分区默认支持

CREATE SCHEMA IF NOT EXISTS ecommerce_dwd;

CREATE TABLE IF NOT EXISTS ecommerce_dwd.dwd_events_clean (
    event_ts      TIMESTAMP,
    event_type    STRING,
    product_id    BIGINT,
    category_id   BIGINT,
    category_l1   STRING,
    category_l2   STRING,
    category_l3   STRING,
    brand         STRING,
    price         DOUBLE,
    user_id       BIGINT,
    user_session  STRING
)
PARTITIONED BY (dt STRING);

-- Z-Order 索引替代 Hive 分桶，加速 user_id 过滤和 JOIN
-- 注：索引在表有数据后创建
-- CREATE INDEX ecommerce_dwd.dwd_events_clean_zorder ON ecommerce_dwd.dwd_events_clean
--     USING ZORDER (user_id);
