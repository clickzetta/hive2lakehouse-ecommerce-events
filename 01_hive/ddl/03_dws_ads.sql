-- DWS 层：用户行为日汇总
-- 每个用户每天的 view/cart/purchase 次数和消费金额

CREATE TABLE IF NOT EXISTS ecommerce.dws_user_behavior (
    user_id       BIGINT,
    view_cnt      INT,
    cart_cnt      INT,
    purchase_cnt  INT,
    purchase_amt  DOUBLE
)
PARTITIONED BY (dt STRING)
STORED AS ORC
TBLPROPERTIES ("orc.compress"="SNAPPY");

-- ADS 层：每日漏斗转化率
-- view → cart → purchase 各步骤用户数和转化率

CREATE TABLE IF NOT EXISTS ecommerce.ads_funnel_daily (
    view_users     BIGINT,
    cart_users     BIGINT,
    purchase_users BIGINT,
    view_to_cart_rate   DOUBLE,
    cart_to_purchase_rate DOUBLE
)
PARTITIONED BY (dt STRING)
STORED AS ORC;
