-- Intent-to-treat experiment scorecard: conversion, retained AUM, cost and guardrails.
WITH group_metrics AS (
    SELECT
        experiment_group,
        COUNT(*) AS assigned_users,
        SUM(delivered) AS delivered_users,
        AVG(clicked_7d) AS click_rate,
        AVG(purchased_30d) AS purchase_rate,
        AVG(purchase_amount_30d) AS purchase_amount_per_user,
        AVG(purchase_amount_30d - redeemed_amount_30d) AS net_aum_30d_per_user,
        AVG(retained_aum_90d) AS retained_aum_90d_per_user,
        AVG(retained_30d) AS retention_30d_rate,
        AVG(retained_90d) AS retention_90d_rate,
        1.0 * SUM(redeemed_30d) / NULLIF(SUM(purchased_30d), 0) AS redemption_rate_among_buyers,
        AVG(complaint_30d) AS complaint_rate,
        AVG(CASE WHEN recommended_product_id IS NOT NULL THEN suitability_passed END) AS suitability_pass_rate,
        SUM(campaign_cost) AS total_campaign_cost,
        AVG(campaign_cost) AS campaign_cost_per_user
    FROM experiment_assignments
    GROUP BY experiment_group
),
control AS (
    SELECT
        purchase_rate AS control_purchase_rate,
        retained_aum_90d_per_user AS control_retained_aum_90d_per_user
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
    ROUND((g.purchase_rate - c.control_purchase_rate) * 10000, 1) AS incremental_buyers_per_10k,
    ROUND(g.purchase_amount_per_user, 2) AS purchase_amount_per_user,
    ROUND(g.net_aum_30d_per_user, 2) AS net_aum_30d_per_user,
    ROUND(g.retained_aum_90d_per_user, 2) AS retained_aum_90d_per_user,
    ROUND((g.retained_aum_90d_per_user - c.control_retained_aum_90d_per_user) * 10000, 2)
        AS incremental_retained_aum_90d_per_10k,
    ROUND(g.retention_30d_rate, 4) AS retention_30d_rate,
    ROUND(g.retention_90d_rate, 4) AS retention_90d_rate,
    ROUND(g.redemption_rate_among_buyers, 4) AS redemption_rate_among_buyers,
    ROUND(g.complaint_rate, 4) AS complaint_rate,
    ROUND(g.suitability_pass_rate, 4) AS suitability_pass_rate,
    ROUND(g.campaign_cost_per_user, 2) AS campaign_cost_per_user,
    ROUND(
        g.total_campaign_cost /
        NULLIF((g.purchase_rate - c.control_purchase_rate) * g.assigned_users, 0),
        2
    ) AS cost_per_incremental_buyer
FROM group_metrics g
CROSS JOIN control c
ORDER BY CASE g.experiment_group
    WHEN 'control' THEN 1 WHEN 'education_content' THEN 2 ELSE 3 END;
