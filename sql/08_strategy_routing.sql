-- Segment-level evidence used to define the next routing experiment.
WITH observed AS (
    SELECT
        u.risk_profile,
        e.experiment_group,
        COUNT(*) AS assigned_users,
        AVG(e.purchased_30d) AS purchase_rate,
        AVG(e.retained_30d) AS retention_30d_rate,
        AVG(e.retained_aum_90d) AS retained_aum_90d_per_user,
        1.0 * SUM(e.redeemed_30d) / NULLIF(SUM(e.purchased_30d), 0) AS redemption_rate_among_buyers,
        AVG(e.complaint_30d) AS complaint_rate,
        AVG(e.campaign_cost) AS campaign_cost_per_user
    FROM experiment_assignments e
    JOIN users u USING (user_id)
    GROUP BY u.risk_profile, e.experiment_group
),
policy AS (
    SELECT 'cautious' AS risk_profile, 'education_content' AS proposed_strategy
    UNION ALL SELECT 'balanced', 'product_recommendation'
    UNION ALL SELECT 'aggressive', 'education_content'
)
SELECT
    o.risk_profile,
    o.experiment_group,
    o.assigned_users,
    ROUND(o.purchase_rate, 4) AS purchase_rate,
    ROUND(o.retention_30d_rate, 4) AS retention_30d_rate,
    ROUND(o.retained_aum_90d_per_user, 2) AS retained_aum_90d_per_user,
    ROUND(o.redemption_rate_among_buyers, 4) AS redemption_rate_among_buyers,
    ROUND(o.complaint_rate, 4) AS complaint_rate,
    ROUND(o.campaign_cost_per_user, 2) AS campaign_cost_per_user,
    CASE WHEN o.experiment_group = p.proposed_strategy THEN 1 ELSE 0 END AS proposed_for_next_test
FROM observed o
JOIN policy p USING (risk_profile)
ORDER BY CASE o.risk_profile
    WHEN 'cautious' THEN 1 WHEN 'balanced' THEN 2 ELSE 3 END,
    CASE o.experiment_group
    WHEN 'control' THEN 1 WHEN 'education_content' THEN 2 ELSE 3 END;
