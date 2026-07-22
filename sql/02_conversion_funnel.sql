-- A channel-level conversion funnel using one row per user to avoid join inflation.
WITH user_flags AS (
    SELECT
        u.user_id,
        u.acquisition_channel,
        MAX(CASE WHEN e.event_type = 'app_visit' THEN 1 ELSE 0 END) AS visited,
        MAX(CASE WHEN e.event_type = 'account_open' THEN 1 ELSE 0 END) AS opened
    FROM users u
    LEFT JOIN events e ON u.user_id = e.user_id
    GROUP BY u.user_id, u.acquisition_channel
),
trade_flags AS (
    SELECT
        user_id,
        MAX(CASE WHEN transaction_type = 'buy' THEN 1 ELSE 0 END) AS first_invested,
        CASE WHEN SUM(CASE WHEN transaction_type = 'buy' THEN 1 ELSE 0 END) >= 2 THEN 1 ELSE 0 END AS repeat_invested
    FROM transactions
    GROUP BY user_id
),
combined AS (
    SELECT
        f.*,
        COALESCE(t.first_invested, 0) AS first_invested,
        COALESCE(t.repeat_invested, 0) AS repeat_invested
    FROM user_flags f
    LEFT JOIN trade_flags t ON f.user_id = t.user_id
)
SELECT
    acquisition_channel,
    COUNT(*) AS registered_users,
    SUM(visited) AS visitors,
    SUM(opened) AS opened_users,
    SUM(first_invested) AS first_investors,
    SUM(repeat_invested) AS repeat_investors,
    ROUND(1.0 * SUM(visited) / COUNT(*), 4) AS visit_rate,
    ROUND(1.0 * SUM(opened) / COUNT(*), 4) AS account_open_rate,
    ROUND(1.0 * SUM(first_invested) / NULLIF(SUM(opened), 0), 4) AS first_invest_rate,
    ROUND(1.0 * SUM(repeat_invested) / NULLIF(SUM(first_invested), 0), 4) AS repeat_invest_rate,
    ROUND(1.0 * SUM(repeat_invested) / COUNT(*), 4) AS end_to_end_rate
FROM combined
GROUP BY acquisition_channel
UNION ALL
SELECT
    'ALL' AS acquisition_channel,
    COUNT(*), SUM(visited), SUM(opened), SUM(first_invested), SUM(repeat_invested),
    ROUND(1.0 * SUM(visited) / COUNT(*), 4),
    ROUND(1.0 * SUM(opened) / COUNT(*), 4),
    ROUND(1.0 * SUM(first_invested) / NULLIF(SUM(opened), 0), 4),
    ROUND(1.0 * SUM(repeat_invested) / NULLIF(SUM(first_invested), 0), 4),
    ROUND(1.0 * SUM(repeat_invested) / COUNT(*), 4)
FROM combined
ORDER BY acquisition_channel;

