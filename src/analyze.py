"""Statistical analysis, causal inference, churn modeling and visualization."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import norm
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize, proportions_ztest

from .config import CHART_DIR, DB_PATH, RANDOM_SEED, ROOT, TABLE_DIR, ensure_directories


COLORS = ["#173F5F", "#20639B", "#3CAEA3", "#F6D55C", "#ED553B"]


def save_figure(name: str) -> None:
    plt.tight_layout()
    plt.savefig(CHART_DIR / name, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close()


def plot_funnel(funnel: pd.DataFrame) -> None:
    total = funnel.loc[funnel.acquisition_channel == "ALL"].iloc[0]
    labels = ["Registered", "Visited", "Account opened", "First invested", "Repeat invested"]
    values = [total.registered_users, total.visitors, total.opened_users, total.first_investors, total.repeat_investors]
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(labels[::-1], values[::-1], color=COLORS[: len(values)][::-1])
    for bar, value in zip(bars, values[::-1]):
        ax.text(bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height() / 2, f"{int(value):,}", va="center")
    ax.set_title("New-user conversion funnel")
    ax.set_xlabel("Users")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure("conversion_funnel.png")


def plot_channel_conversion(funnel: pd.DataFrame) -> None:
    frame = funnel[funnel.acquisition_channel != "ALL"].sort_values("end_to_end_rate", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=frame, x="end_to_end_rate", y="acquisition_channel", color=COLORS[1], ax=ax)
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    ax.set(title="Repeat-investor conversion by acquisition channel", xlabel="Registered → repeat investor", ylabel="")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure("channel_conversion.png")


def plot_retention(retention: pd.DataFrame) -> None:
    curve = retention.groupby("month_number", as_index=False).agg(retained_users=("retained_users", "sum"), cohort_size=("cohort_size", "sum"))
    curve["retention_rate"] = curve.retained_users / curve.cohort_size
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(curve.month_number, curve.retention_rate, marker="o", linewidth=2.5, color=COLORS[2])
    for x, y in zip(curve.month_number, curve.retention_rate):
        ax.text(x, y + 0.012, f"{y:.1%}", ha="center", fontsize=9)
    ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    ax.set(title="Weighted monthly cohort retention", xlabel="Months after registration", ylabel="Active-user retention", ylim=(0, 1.12))
    ax.grid(axis="y", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    save_figure("retention_curve.png")


def analyze_experiment(experiment: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    control = experiment[experiment.experiment_group == "control"]
    rows = []
    for group_name in ["education_content", "product_recommendation"]:
        treatment = experiment[experiment.experiment_group == group_name]
        count = np.array([treatment.purchased_30d.sum(), control.purchased_30d.sum()])
        nobs = np.array([len(treatment), len(control)])
        z_stat, p_value = proportions_ztest(count, nobs)
        treatment_rate, control_rate = count / nobs
        se = math_sqrt(
            treatment_rate * (1 - treatment_rate) / nobs[0]
            + control_rate * (1 - control_rate) / nobs[1]
        )
        lift = treatment_rate - control_rate
        rows.append(
            {
                "treatment": group_name,
                "control_rate": control_rate,
                "treatment_rate": treatment_rate,
                "absolute_lift": lift,
                "relative_lift": treatment_rate / control_rate - 1,
                "ci_low": lift - 1.96 * se,
                "ci_high": lift + 1.96 * se,
                "z_stat": z_stat,
                "p_value": p_value,
            }
        )
    tests = pd.DataFrame(rows)
    tests.to_csv(TABLE_DIR / "experiment_significance.csv", index=False)

    by_risk = (
        experiment.groupby(["risk_profile", "experiment_group"], as_index=False)
        .agg(purchase_rate=("purchased_30d", "mean"), users=("user_id", "count"))
    )
    by_risk.to_csv(TABLE_DIR / "experiment_heterogeneity.csv", index=False)

    summary = experiment.groupby("experiment_group", as_index=False).agg(
        purchase_rate=("purchased_30d", "mean"), retention_rate=("retained_30d", "mean")
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=summary, x="experiment_group", y="purchase_rate", hue="experiment_group", palette=COLORS[:3], legend=False, ax=ax)
    for patch, value in zip(ax.patches, summary.purchase_rate):
        ax.text(patch.get_x() + patch.get_width() / 2, value + 0.002, f"{value:.1%}", ha="center")
    ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    ax.set(title="Dormant-user experiment: 30-day purchase rate", xlabel="", ylabel="Purchase rate")
    ax.tick_params(axis="x", rotation=12)
    ax.spines[["top", "right"]].set_visible(False)
    save_figure("experiment_purchase_lift.png")

    base_rate = float(control.purchased_30d.mean())
    target_rate = base_rate + 0.02
    effect_size = proportion_effectsize(target_rate, base_rate)
    required_n = int(np.ceil(NormalIndPower().solve_power(effect_size=effect_size, alpha=0.05, power=0.8, ratio=1.0)))
    best = tests.sort_values("absolute_lift", ascending=False).iloc[0]
    return tests, {
        "control_purchase_rate": base_rate,
        "best_treatment": best.treatment,
        "best_absolute_lift": float(best.absolute_lift),
        "best_p_value": float(best.p_value),
        "sample_size_per_arm_for_2pp_mde": required_n,
    }


def math_sqrt(value: float) -> float:
    return float(np.sqrt(value))


def analyze_did(panel: pd.DataFrame) -> dict:
    panel = panel.copy()
    panel["interaction"] = panel.pilot_group * panel.post_period
    # Month fixed effects absorb the common post-period change; the interaction is the DiD estimate.
    model = smf.ols("active_30d ~ pilot_group + interaction + C(month)", data=panel).fit(
        cov_type="cluster", cov_kwds={"groups": panel.user_id}
    )
    result = pd.DataFrame(
        {
            "term": model.params.index,
            "coefficient": model.params.values,
            "std_error": model.bse.values,
            "p_value": model.pvalues.values,
        }
    )
    result.to_csv(TABLE_DIR / "did_results.csv", index=False)
    trends = panel.groupby(["month", "pilot_group"], as_index=False).active_30d.mean()
    trends["month"] = pd.to_datetime(trends["month"]).dt.strftime("%Y-%m")
    trends["group"] = trends.pilot_group.map({0: "Comparison", 1: "Pilot"})
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.lineplot(data=trends, x="month", y="active_30d", hue="group", marker="o", palette=[COLORS[0], COLORS[4]], ax=ax)
    ax.axvline(2.5, linestyle="--", color="gray", linewidth=1, label="Rollout")
    ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    ax.set(title="Recall-campaign difference-in-differences", xlabel="Month", ylabel="30-day active rate")
    ax.tick_params(axis="x", rotation=25)
    ax.spines[["top", "right"]].set_visible(False)
    save_figure("did_parallel_trends.png")
    return {
        "did_active_rate_effect": float(model.params["interaction"]),
        "did_p_value": float(model.pvalues["interaction"]),
        "did_ci_low": float(model.conf_int().loc["interaction", 0]),
        "did_ci_high": float(model.conf_int().loc["interaction", 1]),
    }


def roc_auc(y_true: np.ndarray, score: np.ndarray) -> float:
    order = np.argsort(score)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(score) + 1)
    positives = y_true == 1
    n_pos = positives.sum()
    n_neg = len(y_true) - n_pos
    return float((ranks[positives].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def fit_churn_model(features: pd.DataFrame) -> dict:
    frame = features.copy()
    target = frame.pop("churned_next_90d").astype(int)
    frame = frame.drop(columns=["user_id"])
    categorical = ["acquisition_channel", "risk_profile", "city_tier"]
    x = pd.get_dummies(frame, columns=categorical, drop_first=True, dtype=float)
    numeric = [c for c in x.columns if c not in {c for c in x.columns if any(c.startswith(prefix + "_") for prefix in categorical)}]
    means = x[numeric].mean()
    stds = x[numeric].std().replace(0, 1)
    x[numeric] = (x[numeric] - means) / stds
    rng = np.random.default_rng(RANDOM_SEED)
    test_mask = rng.random(len(x)) < 0.25
    x_train = sm.add_constant(x.loc[~test_mask], has_constant="add")
    x_test = sm.add_constant(x.loc[test_mask], has_constant="add")
    y_train = target.loc[~test_mask]
    y_test = target.loc[test_mask]
    model = sm.GLM(y_train, x_train, family=sm.families.Binomial()).fit()
    prediction = model.predict(x_test)
    auc = roc_auc(y_test.to_numpy(), prediction.to_numpy())
    threshold = float(np.quantile(prediction, 0.80))
    high_risk = prediction >= threshold
    precision_at_20 = float(y_test.loc[high_risk].mean())

    coefficients = pd.DataFrame(
        {
            "feature": model.params.index,
            "coefficient": model.params.values,
            "odds_ratio": np.exp(model.params.values),
            "p_value": model.pvalues.values,
        }
    ).sort_values("coefficient")
    coefficients.to_csv(TABLE_DIR / "churn_model_coefficients.csv", index=False)
    important = coefficients[coefficients.feature != "const"].copy()
    important["abs_coefficient"] = important.coefficient.abs()
    important = important.nlargest(10, "abs_coefficient").sort_values("coefficient")
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = [COLORS[4] if x > 0 else COLORS[2] for x in important.coefficient]
    ax.barh(important.feature, important.coefficient, color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set(title="Churn model: strongest standardized signals", xlabel="Log-odds coefficient", ylabel="")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure("churn_model_coefficients.png")
    (ROOT / "outputs" / "model_summary.txt").write_text(model.summary().as_text(), encoding="utf-8")
    return {
        "churn_model_auc": auc,
        "test_churn_rate": float(y_test.mean()),
        "top_20pct_precision": precision_at_20,
        "top_20pct_threshold": threshold,
    }


def main() -> None:
    ensure_directories()
    sns.set_theme(style="whitegrid", context="notebook")
    funnel = pd.read_csv(TABLE_DIR / "conversion_funnel.csv")
    retention = pd.read_csv(TABLE_DIR / "retention.csv")
    churn = pd.read_csv(TABLE_DIR / "churn_features.csv")
    plot_funnel(funnel)
    plot_channel_conversion(funnel)
    plot_retention(retention)

    with sqlite3.connect(DB_PATH) as connection:
        experiment = pd.read_sql_query(
            "SELECT e.*, u.risk_profile, u.acquisition_channel FROM experiment_assignments e JOIN users u USING(user_id)",
            connection,
        )
        panel = pd.read_sql_query("SELECT * FROM campaign_observations", connection)
    _, experiment_summary = analyze_experiment(experiment)
    did_summary = analyze_did(panel)
    model_summary = fit_churn_model(churn)

    lifecycle = pd.read_csv(TABLE_DIR / "user_lifecycle.csv")
    segments = pd.read_csv(TABLE_DIR / "user_segmentation.csv")
    funnel_total = funnel[funnel.acquisition_channel == "ALL"].iloc[0]
    summary = {
        "dataset": {
            "users": int(funnel_total.registered_users),
            "experiment_users": int(len(experiment)),
            "dormant_share": float((lifecycle.lifecycle_stage == "dormant").mean()),
            "cash_rich_noninvestors": int((segments.strategy_segment == "cash_rich_noninvestor").sum()),
        },
        "funnel": {
            "visit_rate": float(funnel_total.visit_rate),
            "account_open_rate": float(funnel_total.account_open_rate),
            "first_invest_rate": float(funnel_total.first_invest_rate),
            "repeat_invest_rate": float(funnel_total.repeat_invest_rate),
            "end_to_end_rate": float(funnel_total.end_to_end_rate),
        },
        "experiment": experiment_summary,
        "causal_inference": did_summary,
        "model": model_summary,
    }
    (ROOT / "outputs" / "analysis_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
