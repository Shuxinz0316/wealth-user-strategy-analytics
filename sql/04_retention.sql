-- Monthly registration-cohort retention for the first six months.
WITH cohorts AS (
    SELECT
        user_id,
        date(registered_at, 'start of month') AS cohort_month
    FROM users
),
activity AS (
    SELECT DISTINCT
        user_id,
        date(event_time, 'start of month') AS activity_month
    FROM events
    -- Registration itself is month-0 activity; later months require an app visit.
    WHERE event_type IN ('register', 'app_visit')
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        CAST((strftime('%Y', a.activity_month) - strftime('%Y', c.cohort_month)) * 12
             + (strftime('%m', a.activity_month) - strftime('%m', c.cohort_month)) AS INTEGER) AS month_number,
        COUNT(DISTINCT a.user_id) AS retained_users
    FROM cohorts c
    JOIN activity a ON c.user_id = a.user_id AND a.activity_month >= c.cohort_month
    GROUP BY c.cohort_month, month_number
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
)
SELECT
    ca.cohort_month,
    ca.month_number,
    cs.cohort_size,
    ca.retained_users,
    ROUND(1.0 * ca.retained_users / cs.cohort_size, 4) AS retention_rate
FROM cohort_activity ca
JOIN cohort_sizes cs USING (cohort_month)
WHERE ca.month_number BETWEEN 0 AND 6
ORDER BY ca.cohort_month, ca.month_number;
