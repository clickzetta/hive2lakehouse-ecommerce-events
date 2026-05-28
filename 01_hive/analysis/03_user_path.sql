-- 分析 3：用户购买路径分析
-- 找出同一 session 内 view → cart → purchase 的完整路径用户
-- 注：直接对分桶 ORC 表做 GROUP BY 需要切换 InputFormat（Hive 4.0 + Tez bug）

SET hive.input.format=org.apache.hadoop.hive.ql.io.HiveInputFormat;

SELECT user_id, user_session, event_cnt, view_cnt, cart_cnt, purchase_cnt, session_type
FROM (
    SELECT
        user_id,
        user_session,
        COUNT(*) AS event_cnt,
        SUM(CASE WHEN event_type = 'view'     THEN 1 ELSE 0 END) AS view_cnt,
        SUM(CASE WHEN event_type = 'cart'     THEN 1 ELSE 0 END) AS cart_cnt,
        SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS purchase_cnt,
        CASE
            WHEN SUM(CASE WHEN event_type = 'view'     THEN 1 ELSE 0 END) > 0
             AND SUM(CASE WHEN event_type = 'cart'     THEN 1 ELSE 0 END) > 0
             AND SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) > 0
            THEN 'full_path'
            WHEN SUM(CASE WHEN event_type = 'cart'     THEN 1 ELSE 0 END) > 0
             AND SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) = 0
            THEN 'cart_abandon'
            ELSE 'browse_only'
        END AS session_type
    FROM ecommerce.dwd_events_clean
    GROUP BY user_id, user_session
) t
ORDER BY purchase_cnt DESC, cart_cnt DESC;
