-- RFM-style segmentation combining current AUM, trading frequency and risk profile.
WITH trade_metrics AS (
    SELECT
        u.user_id,
        COALESCE(SUM(CASE WHEN t.transaction_type = 'buy' THEN t.amount ELSE -t.amount END), 0) AS aum,
        SUM(CASE WHEN t.transaction_type = 'buy' THEN 1 ELSE 0 END) AS buy_frequency,
        MAX(CASE WHEN t.transaction_type = 'buy' THEN t.transaction_time END) AS last_buy_at
    FROM users u
    LEFT JOIN transactions t ON u.user_id = t.user_id
    GROUP BY u.user_id
),
ranked AS (
    SELECT
        tm.*,
        CASE WHEN aum > 0 THEN NTILE(4) OVER (
            PARTITION BY CASE WHEN aum > 0 THEN 1 ELSE 0 END ORDER BY aum
        ) ELSE 0 END AS aum_quartile,
        CASE WHEN buy_frequency > 0 THEN NTILE(4) OVER (
            PARTITION BY CASE WHEN buy_frequency > 0 THEN 1 ELSE 0 END ORDER BY buy_frequency
        ) ELSE 0 END AS frequency_quartile
    FROM trade_metrics tm
)
SELECT
    u.user_id,
    u.risk_profile,
    u.acquisition_channel,
    ROUND(r.aum, 2) AS aum,
    r.buy_frequency,
    r.last_buy_at,
    r.aum_quartile,
    r.frequency_quartile,
    CASE
        WHEN r.aum_quartile = 4 AND r.frequency_quartile >= 3
             AND julianday('2025-03-31') - julianday(r.last_buy_at) <= 90 THEN 'high_value_active'
        WHEN r.aum_quartile >= 3 AND julianday('2025-03-31') - julianday(r.last_buy_at) > 90 THEN 'high_value_at_risk'
        WHEN r.buy_frequency >= 1 THEN 'growth_investor'
        WHEN u.initial_cash_balance >= 20000 THEN 'cash_rich_noninvestor'
        ELSE 'low_engagement'
    END AS strategy_segment
FROM users u
JOIN ranked r ON u.user_id = r.user_id
ORDER BY aum DESC;
