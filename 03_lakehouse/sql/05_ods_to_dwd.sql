-- Lakehouse ODS → DWD 清洗
-- 迁移说明：
--   Hive: SET hive.exec.dynamic.partition=true（必须）
--         SET hive.enforce.bucketing=true（分桶写入必须）
--         REGEXP_REPLACE + SPLIT + CASE WHEN SIZE(...) 语法完全一致
--   Lakehouse: 无需任何 SET 语句，动态分区默认支持
--              无分桶，去掉 CLUSTERED BY 相关配置
--              REGEXP_REPLACE / SPLIT / SIZE 函数语法完全兼容

INSERT OVERWRITE TABLE ecommerce_dwd.dwd_events_clean
PARTITION (dt)
SELECT
    CAST(REGEXP_REPLACE(event_time, ' UTC$', '') AS TIMESTAMP) AS event_ts,
    event_type,
    product_id,
    category_id,
    SPLIT(category_code, '\\.')[0]                              AS category_l1,
    CASE WHEN SIZE(SPLIT(category_code, '\\.')) > 1
         THEN SPLIT(category_code, '\\.')[1] END                AS category_l2,
    CASE WHEN SIZE(SPLIT(category_code, '\\.')) > 2
         THEN SPLIT(category_code, '\\.')[2] END                AS category_l3,
    brand,
    price,
    user_id,
    user_session,
    dt
FROM ecommerce_ods.ods_events_raw
WHERE price > 0 OR event_type != 'purchase';
