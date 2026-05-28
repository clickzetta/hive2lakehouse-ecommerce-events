-- Lakehouse DWS / ADS 层建表
-- 迁移说明：与 Hive 语法完全一致，去掉 STORED AS ORC 和 TBLPROPERTIES 即可

CREATE SCHEMA IF NOT EXISTS ecommerce_dws;

CREATE TABLE IF NOT EXISTS ecommerce_dws.dws_user_behavior (
    user_id       BIGINT,
    view_cnt      INT,
    cart_cnt      INT,
    purchase_cnt  INT,
    purchase_amt  DOUBLE
)
PARTITIONED BY (dt STRING);

CREATE SCHEMA IF NOT EXISTS ecommerce_ads;

CREATE TABLE IF NOT EXISTS ecommerce_ads.ads_funnel_daily (
    view_users            BIGINT,
    cart_users            BIGINT,
    purchase_users        BIGINT,
    view_to_cart_rate     DOUBLE,
    cart_to_purchase_rate DOUBLE
)
PARTITIONED BY (dt STRING);
