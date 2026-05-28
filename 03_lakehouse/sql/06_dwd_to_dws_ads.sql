-- Lakehouse DWD → DWS / ADS 聚合
-- 迁移说明：聚合逻辑与 Hive 完全一致，去掉所有 SET 语句即可

INSERT OVERWRITE TABLE ecommerce_dws.dws_user_behavior
PARTITION (dt)
SELECT
    user_id,
    SUM(CASE WHEN event_type = 'view'     THEN 1 ELSE 0 END) AS view_cnt,
    SUM(CASE WHEN event_type = 'cart'     THEN 1 ELSE 0 END) AS cart_cnt,
    SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS purchase_cnt,
    SUM(CASE WHEN event_type = 'purchase' THEN price ELSE 0 END) AS purchase_amt,
    dt
FROM ecommerce_dwd.dwd_events_clean
GROUP BY user_id, dt;

INSERT OVERWRITE TABLE ecommerce_ads.ads_funnel_daily
PARTITION (dt)
SELECT
    COUNT(DISTINCT CASE WHEN event_type = 'view'     THEN user_id END) AS view_users,
    COUNT(DISTINCT CASE WHEN event_type = 'cart'     THEN user_id END) AS cart_users,
    COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS purchase_users,
    ROUND(
        COUNT(DISTINCT CASE WHEN event_type = 'cart'     THEN user_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT CASE WHEN event_type = 'view' THEN user_id END), 0),
        4
    ) AS view_to_cart_rate,
    ROUND(
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT CASE WHEN event_type = 'cart' THEN user_id END), 0),
        4
    ) AS cart_to_purchase_rate,
    dt
FROM ecommerce_dwd.dwd_events_clean
GROUP BY dt;
