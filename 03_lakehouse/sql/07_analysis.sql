-- Lakehouse 分析查询
-- 迁移说明：
--   Hive: 分桶 ORC 表 GROUP BY 在 Hive 4.0 + Tez 下有 bug，需要 SET hive.input.format
--   Lakehouse: 无分桶概念，无此 bug，所有查询直接运行

-- 分析 1：每日 PV / UV
SELECT
    dt,
    COUNT(*)                AS pv,
    COUNT(DISTINCT user_id) AS uv,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT user_id), 2) AS pv_per_uv
FROM ecommerce_dwd.dwd_events_clean
WHERE event_type = 'view'
GROUP BY dt
ORDER BY dt;

-- 分析 2：用户消费排行（窗口函数）
SELECT
    user_id,
    view_cnt,
    cart_cnt,
    purchase_cnt,
    purchase_amt,
    RANK() OVER (ORDER BY purchase_amt DESC) AS spending_rank
FROM ecommerce_dws.dws_user_behavior
WHERE dt = '2019-10-01'
ORDER BY spending_rank;

-- 分析 3：用户购买路径分析
SELECT
    user_id,
    user_session,
    event_cnt,
    view_cnt,
    cart_cnt,
    purchase_cnt,
    session_type
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
    FROM ecommerce_dwd.dwd_events_clean
    GROUP BY user_id, user_session
) t
ORDER BY purchase_cnt DESC, cart_cnt DESC;
