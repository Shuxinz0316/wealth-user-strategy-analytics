-- Identify each user's furthest lifecycle stage and inactivity state.
WITH event_summary AS (
    SELECT
        user_id,
        MIN(CASE WHEN event_type = 'account_open' THEN event_time END) AS account_opened_at,
        MAX(CASE WHEN event_type = 'app_visit' THEN event_time END) AS last_visit_at
    FROM events
    GROUP BY user_id
),
trade_summary AS (
    SELECT
        user_id,
        MIN(CASE WHEN transaction_type = 'buy' THEN transaction_time END) AS first_buy_at,
        SUM(CASE WHEN transaction_type = 'buy' THEN 1 ELSE 0 END) AS buy_count
    FROM transactions
    GROUP BY user_id
)
SELECT
    u.user_id,
    u.registered_at,
    u.acquisition_channel,
    u.risk_profile,
    e.account_opened_at,
    t.first_buy_at,
    COALESCE(t.buy_count, 0) AS buy_count,
    e.last_visit_at,
    CAST(julianday('2025-03-31') - julianday(COALESCE(e.last_visit_at, u.registered_at)) AS INTEGER) AS days_since_last_visit,
    CASE
        WHEN COALESCE(t.buy_count, 0) >= 2 AND julianday('2025-03-31') - julianday(e.last_visit_at) <= 60 THEN 'repeat_active'
        WHEN COALESCE(t.buy_count, 0) >= 1 AND julianday('2025-03-31') - julianday(e.last_visit_at) <= 60 THEN 'first_invest_active'
        WHEN e.account_opened_at IS NOT NULL AND julianday('2025-03-31') - julianday(COALESCE(e.last_visit_at, u.registered_at)) <= 60 THEN 'opened_not_invested'
        WHEN julianday('2025-03-31') - julianday(COALESCE(e.last_visit_at, u.registered_at)) > 60 THEN 'dormant'
        ELSE 'registered_only'
    END AS lifecycle_stage
FROM users u
LEFT JOIN event_summary e ON u.user_id = e.user_id
LEFT JOIN trade_summary t ON u.user_id = t.user_id
ORDER BY u.user_id;

