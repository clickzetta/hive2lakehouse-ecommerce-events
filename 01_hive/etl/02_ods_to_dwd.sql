-- 步骤 3：ODS → DWD 清洗
-- 主要处理：
--   1. event_time STRING → TIMESTAMP（去掉末尾 " UTC"）
--   2. category_code 按 "." 拆分为三级（electronics.smartphone → l1=electronics, l2=smartphone）
--   3. 过滤 price <= 0 的异常记录

SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;
SET hive.enforce.bucketing=true;

INSERT OVERWRITE TABLE ecommerce.dwd_events_clean
PARTITION (dt)
SELECT
    CAST(REGEXP_REPLACE(event_time, ' UTC$', '') AS TIMESTAMP) AS event_ts,
    event_type,
    product_id,
    category_id,
    -- 拆分 category_code：取第 1 段
    SPLIT(category_code, '\\.')[0]                             AS category_l1,
    -- 取第 2 段（不存在时为 NULL）
    CASE WHEN SIZE(SPLIT(category_code, '\\.')) > 1
         THEN SPLIT(category_code, '\\.')[1] END               AS category_l2,
    -- 取第 3 段
    CASE WHEN SIZE(SPLIT(category_code, '\\.')) > 2
         THEN SPLIT(category_code, '\\.')[2] END               AS category_l3,
    brand,
    price,
    user_id,
    user_session,
    dt
FROM ecommerce.ods_events_raw
WHERE price > 0 OR event_type != 'purchase';
