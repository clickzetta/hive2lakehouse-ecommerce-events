-- Lakehouse ODS 数据加载
-- 迁移说明：
--   Hive:      LOAD DATA LOCAL INPATH + staging 表 + INSERT INTO 分区表
--   Lakehouse: COPY INTO FROM VOLUME（无需 staging 表概念）
--              但 COPY INTO 不支持计算列（如从 event_time 提取 dt），
--              需要先 COPY INTO 到无分区 staging 表，再 INSERT INTO 分区主表
--
-- 步骤 1：建 staging 表（无分区，列顺序与 CSV 完全一致）
CREATE TABLE IF NOT EXISTS ecommerce_ods.ods_events_staging (
    event_time    STRING,
    event_type    STRING,
    product_id    BIGINT,
    category_id   BIGINT,
    category_code STRING,
    brand         STRING,
    price         DOUBLE,
    user_id       BIGINT,
    user_session  STRING
);

-- 步骤 2：COPY INTO staging（直接列映射，无需 SerDe 配置）
COPY INTO ecommerce_ods.ods_events_staging
FROM VOLUME ecommerce_ods.ecommerce_vol
USING CSV
OPTIONS ('header' = 'true', 'nullValue' = '')
FILES ('events_sample.csv')
ON_ERROR = CONTINUE;

-- 步骤 3：staging → 分区主表（过滤脏数据，提取分区列）
INSERT OVERWRITE TABLE ecommerce_ods.ods_events_raw
PARTITION (dt)
SELECT
    event_time, event_type, product_id, category_id,
    category_code, brand, price, user_id, user_session,
    SUBSTR(event_time, 1, 10) AS dt
FROM ecommerce_ods.ods_events_staging
WHERE event_type IN ('view', 'cart', 'purchase')
  AND user_id > 100000;
