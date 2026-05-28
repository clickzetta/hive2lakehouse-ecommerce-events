-- 分析 2：Top 用户消费排行
-- 基于 DWS 层（已聚合），使用窗口函数 RANK() 排名
-- 注：直接对分桶 ORC 表（dwd_events_clean）做 GROUP BY 在 Hive 4.0 + Tez 下有 bug，
--     生产中应基于 DWS/ADS 层做分析，不直接查 DWD

SELECT
    user_id,
    view_cnt,
    cart_cnt,
    purchase_cnt,
    purchase_amt,
    RANK() OVER (ORDER BY purchase_amt DESC) AS spending_rank
FROM ecommerce.dws_user_behavior
WHERE dt = '2019-10-01'
ORDER BY spending_rank;
