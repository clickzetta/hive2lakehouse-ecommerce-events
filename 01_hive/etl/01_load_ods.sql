-- 步骤 1：将 CSV 文件加载到 staging 表
-- staging 表是 EXTERNAL 表，LOAD DATA 只是移动文件，不做格式转换
-- 注意：Hive 的 LOAD DATA LOCAL INPATH 从本地文件系统加载（容器内路径）

LOAD DATA LOCAL INPATH '/tmp/ecommerce/sample/events_sample.csv'
OVERWRITE INTO TABLE ecommerce.ods_events_staging;

-- 步骤 2：从 staging 插入 ODS 分区表（动态分区）
-- SUBSTR(event_time, 1, 10) 从 "2019-10-01 00:00:00 UTC" 提取日期部分

SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

INSERT OVERWRITE TABLE ecommerce.ods_events_raw
PARTITION (dt)
SELECT
    event_time,
    event_type,
    CAST(product_id  AS BIGINT),
    CAST(category_id AS BIGINT),
    category_code,
    brand,
    CAST(price AS DOUBLE),
    CAST(user_id AS BIGINT),
    user_session,
    SUBSTR(event_time, 1, 10) AS dt
FROM ecommerce.ods_events_staging
WHERE event_time IS NOT NULL
  AND event_time != 'event_time'
  AND event_type IN ('view', 'cart', 'purchase')
  AND CAST(user_id AS BIGINT) > 100000;
-- 注：OpenCSVSerde 遇到连续空字段（如 brand 为空）会导致列偏移，
-- user_id 异常小的行是解析错位的脏数据，过滤掉
