-- Monthly transaction KPIs, including net flow and cumulative AUM.
WITH RECURSIVE months(month) AS (
    SELECT date('2024-01-01')
    UNION ALL
    SELECT date(month, '+1 month') FROM months WHERE month < date('2025-03-01')
),
monthly AS (
    SELECT
        date(transaction_time, 'start of month') AS month,
        COUNT(DISTINCT CASE WHEN transaction_type = 'buy' THEN user_id END) AS buyers,
        SUM(CASE WHEN transaction_type = 'buy' THEN amount ELSE 0 END) AS gross_inflow,
        SUM(CASE WHEN transaction_type = 'redeem' THEN amount ELSE 0 END) AS redemption,
        SUM(CASE WHEN transaction_type = 'buy' THEN amount ELSE -amount END) AS net_flow
    FROM transactions
    GROUP BY date(transaction_time, 'start of month')
)
SELECT
    m.month,
    COALESCE(x.buyers, 0) AS buyers,
    ROUND(COALESCE(x.gross_inflow, 0), 2) AS gross_inflow,
    ROUND(COALESCE(x.redemption, 0), 2) AS redemption,
    ROUND(COALESCE(x.net_flow, 0), 2) AS net_flow,
    ROUND(SUM(COALESCE(x.net_flow, 0)) OVER (ORDER BY m.month ROWS UNBOUNDED PRECEDING), 2) AS cumulative_aum,
    ROUND(1.0 * COALESCE(x.net_flow, 0) / NULLIF(LAG(x.net_flow) OVER (ORDER BY m.month), 0) - 1, 4) AS net_flow_mom
FROM months m
LEFT JOIN monthly x USING (month)
ORDER BY m.month;

