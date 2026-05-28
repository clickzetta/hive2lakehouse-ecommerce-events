-- 分析 1：每日 PV / UV 统计
-- PV = 总事件数，UV = 独立用户数

SELECT
    dt,
    COUNT(*)                    AS pv,
    COUNT(DISTINCT user_id)     AS uv,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT user_id), 2) AS pv_per_uv
FROM ecommerce.dwd_events_clean
WHERE event_type = 'view'
GROUP BY dt
ORDER BY dt;
