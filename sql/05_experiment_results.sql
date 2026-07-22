-- Intent-to-treat A/B test summary with lift against control.
WITH group_metrics AS (
    SELECT
        experiment_group,
        COUNT(*) AS assigned_users,
        SUM(delivered) AS delivered_users,
        AVG(clicked_7d) AS click_rate,
        AVG(purchased_30d) AS purchase_rate,
        AVG(purchase_amount_30d) AS purchase_amount_per_assigned_user,
        AVG(retained_30d) AS retention_rate
    FROM experiment_assignments
    GROUP BY experiment_group
),
control AS (
    SELECT purchase_rate AS control_purchase_rate
    FROM group_metrics
    WHERE experiment_group = 'control'
)
SELECT
    g.experiment_group,
    g.assigned_users,
    g.delivered_users,
    ROUND(g.click_rate, 4) AS click_rate,
    ROUND(g.purchase_rate, 4) AS purchase_rate,
    ROUND(g.purchase_rate - c.control_purchase_rate, 4) AS absolute_purchase_lift,
    ROUND((g.purchase_rate / c.control_purchase_rate) - 1, 4) AS relative_purchase_lift,
    ROUND(g.purchase_amount_per_assigned_user, 2) AS purchase_amount_per_assigned_user,
    ROUND(g.retention_rate, 4) AS retention_rate
FROM group_metrics g
CROSS JOIN control c
ORDER BY CASE g.experiment_group
    WHEN 'control' THEN 1 WHEN 'education_content' THEN 2 ELSE 3 END;
