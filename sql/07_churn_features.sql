-- Leakage-safe features at 2024-12-31; label uses the following 90 days.
WITH pre_events AS (
    SELECT
        user_id,
        COUNT(CASE WHEN event_type = 'app_visit' THEN 1 END) AS visits_lifetime,
        COUNT(CASE WHEN event_type = 'content_view' THEN 1 END) AS content_views,
        MAX(CASE WHEN event_type = 'app_visit' THEN event_time END) AS last_visit_at,
        COUNT(CASE WHEN event_type = 'app_visit' AND event_time >= '2024-10-02' THEN 1 END) AS visits_90d
    FROM events
    WHERE event_time < '2025-01-01'
    GROUP BY user_id
),
pre_trades AS (
    SELECT
        user_id,
        COUNT(CASE WHEN transaction_type = 'buy' THEN 1 END) AS buys_lifetime,
        SUM(CASE WHEN transaction_type = 'buy' THEN amount ELSE -amount END) AS aum,
        COUNT(CASE WHEN transaction_type = 'buy' AND transaction_time >= '2024-10-02' THEN 1 END) AS buys_90d
    FROM transactions
    WHERE transaction_time < '2025-01-01'
    GROUP BY user_id
),
future_activity AS (
    SELECT user_id, 1 AS returned_next_90d
    FROM events
    WHERE event_type = 'app_visit' AND event_time >= '2025-01-01' AND event_time < '2025-04-01'
    GROUP BY user_id
)
SELECT
    u.user_id,
    u.acquisition_channel,
    u.risk_profile,
    u.city_tier,
    u.initial_cash_balance,
    COALESCE(e.visits_lifetime, 0) AS visits_lifetime,
    COALESCE(e.visits_90d, 0) AS visits_90d,
    COALESCE(e.content_views, 0) AS content_views,
    COALESCE(t.buys_lifetime, 0) AS buys_lifetime,
    COALESCE(t.buys_90d, 0) AS buys_90d,
    COALESCE(t.aum, 0) AS aum,
    CAST(julianday('2025-01-01') - julianday(COALESCE(e.last_visit_at, u.registered_at)) AS INTEGER) AS days_since_last_visit,
    CASE WHEN f.returned_next_90d IS NULL THEN 1 ELSE 0 END AS churned_next_90d
FROM users u
JOIN pre_events e ON u.user_id = e.user_id
LEFT JOIN pre_trades t ON u.user_id = t.user_id
LEFT JOIN future_activity f ON u.user_id = f.user_id
WHERE u.registered_at < '2024-10-01'
ORDER BY u.user_id;

