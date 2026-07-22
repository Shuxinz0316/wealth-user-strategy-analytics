"""Generate a realistic, privacy-safe synthetic wealth-platform dataset."""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
import pandas as pd

from .config import EXPERIMENT_DATE, N_USERS, OBSERVATION_END, RANDOM_SEED, RAW_DIR, ensure_directories


def sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1 / (1 + np.exp(-x))


def clipped_date(base: pd.Timestamp, days: int, end: pd.Timestamp) -> pd.Timestamp:
    return min(base + pd.Timedelta(days=max(0, int(days))), end)


def generate_users(rng: np.random.Generator) -> pd.DataFrame:
    registration_start = pd.Timestamp("2024-01-01")
    registration_end = pd.Timestamp("2024-12-31")
    registered_at = registration_start + pd.to_timedelta(
        rng.integers(0, (registration_end - registration_start).days + 1, N_USERS), unit="D"
    )
    channels = rng.choice(
        ["organic", "paid_search", "social", "referral", "bank_partner"],
        N_USERS,
        p=[0.30, 0.22, 0.19, 0.16, 0.13],
    )
    age_groups = rng.choice(["18-25", "26-35", "36-45", "46-55", "56+"], N_USERS, p=[0.15, 0.34, 0.27, 0.16, 0.08])
    risk_profiles = rng.choice(["cautious", "balanced", "aggressive"], N_USERS, p=[0.38, 0.44, 0.18])
    city_tiers = rng.choice(["T1", "T2", "T3+"], N_USERS, p=[0.31, 0.37, 0.32])
    consent = rng.binomial(1, np.where(channels == "referral", 0.82, 0.72))
    cash = np.exp(rng.normal(9.1, 1.05, N_USERS))
    cash *= np.select([age_groups == "18-25", age_groups == "46-55", age_groups == "56+"], [0.55, 1.35, 1.55], default=1.0)
    cash = np.clip(cash, 500, 350_000).round(2)
    return pd.DataFrame(
        {
            "user_id": np.arange(1, N_USERS + 1),
            "registered_at": registered_at,
            "acquisition_channel": channels,
            "age_group": age_groups,
            "city_tier": city_tiers,
            "risk_profile": risk_profiles,
            "initial_cash_balance": cash,
            "marketing_consent": consent,
        }
    )


def generate_products() -> pd.DataFrame:
    rows = [
        (1, "Cash Plus", "money_market", 1, 0.021, 1),
        (2, "Stable Income", "bond_fund", 2, 0.038, 100),
        (3, "Short Duration", "bond_fund", 2, 0.034, 100),
        (4, "Balanced Growth", "mixed_fund", 3, 0.061, 100),
        (5, "China Equity Select", "equity_fund", 4, 0.095, 100),
        (6, "Global Index", "equity_fund", 4, 0.087, 100),
        (7, "Retirement Annuity", "insurance", 2, 0.032, 1_000),
        (8, "Bank Wealth 90D", "bank_wealth", 2, 0.036, 10_000),
    ]
    return pd.DataFrame(rows, columns=["product_id", "product_name", "product_type", "risk_level", "expected_return", "minimum_investment"])


def preferred_product_ids(risk: str) -> list[int]:
    return {
        "cautious": [1, 1, 2, 3, 7, 8],
        "balanced": [1, 2, 3, 4, 4, 6],
        "aggressive": [2, 4, 5, 5, 6, 6],
    }[risk]


def generate_behavior(
    users: pd.DataFrame, products: pd.DataFrame, rng: np.random.Generator
) -> tuple[pd.DataFrame, pd.DataFrame]:
    end = pd.Timestamp(OBSERVATION_END)
    log_cash = np.log1p(users["initial_cash_balance"].to_numpy())
    channel_open = users["acquisition_channel"].map(
        {"organic": 0.10, "paid_search": -0.18, "social": -0.30, "referral": 0.28, "bank_partner": 0.43}
    ).to_numpy()
    p_open = sigmoid(-1.15 + 0.13 * (log_cash - 9) + 0.36 * users["marketing_consent"].to_numpy() + channel_open)
    opened = rng.binomial(1, p_open)
    risk_buy = users["risk_profile"].map({"cautious": -0.18, "balanced": 0.17, "aggressive": 0.06}).to_numpy()
    p_buy = sigmoid(-0.60 + 0.22 * (log_cash - 9) + risk_buy)
    bought = opened * rng.binomial(1, p_buy)

    events: list[tuple] = []
    transactions: list[tuple] = []
    event_id = 1
    transaction_id = 1

    for i, user in users.iterrows():
        uid = int(user.user_id)
        reg = pd.Timestamp(user.registered_at)
        events.append((event_id, uid, reg + pd.Timedelta(hours=int(rng.integers(7, 23))), "register", "app", None))
        event_id += 1
        account_date: pd.Timestamp | None = None
        if opened[i]:
            account_date = clipped_date(reg, int(rng.gamma(2.0, 3.2)) + 1, end)
            events.append((event_id, uid, account_date + pd.Timedelta(hours=10), "account_open", "app", None))
            event_id += 1

        lifespan = max(1, (end - reg).days)
        visit_count = int(rng.poisson(2.5 + 2.2 * opened[i] + 3.5 * bought[i]))
        if visit_count:
            # Most engagement occurs soon after registration, with a smaller long-tail component.
            early_days = rng.exponential(scale=52, size=visit_count)
            long_tail_days = rng.integers(0, lifespan + 1, visit_count)
            visit_days = np.where(rng.random(visit_count) < 0.78, early_days, long_tail_days)
            visit_days = np.sort(np.clip(visit_days.astype(int), 0, lifespan))
        else:
            visit_days = []
        for day in visit_days:
            visit_time = reg + pd.Timedelta(days=int(day), hours=int(rng.integers(7, 23)))
            events.append((event_id, uid, visit_time, "app_visit", "app", None))
            event_id += 1
            if rng.random() < (0.50 if bought[i] else 0.34):
                pid = int(rng.choice(preferred_product_ids(user.risk_profile)))
                events.append((event_id, uid, visit_time + pd.Timedelta(minutes=int(rng.integers(1, 20))), "content_view", "app", pid))
                event_id += 1
                if rng.random() < 0.46:
                    events.append((event_id, uid, visit_time + pd.Timedelta(minutes=int(rng.integers(20, 50))), "product_detail", "app", pid))
                    event_id += 1

        if bought[i] and account_date is not None:
            first_buy_date = clipped_date(account_date, int(rng.gamma(2.0, 5.0)) + 1, end)
            pid = int(rng.choice(preferred_product_ids(user.risk_profile)))
            base_amount = min(float(user.initial_cash_balance) * rng.uniform(0.08, 0.45), 80_000)
            amount = round(max(100, base_amount), 2)
            transactions.append((transaction_id, uid, pid, first_buy_date + pd.Timedelta(hours=14), "buy", amount))
            transaction_id += 1
            repeat_count = int(rng.poisson(1.2 + 0.45 * (user.risk_profile == "aggressive") + 0.25 * (user.initial_cash_balance > 20_000)))
            last_date = first_buy_date
            for _ in range(repeat_count):
                last_date = clipped_date(last_date, int(rng.gamma(2.0, 22.0)) + 7, end)
                if last_date >= end:
                    break
                pid = int(rng.choice(preferred_product_ids(user.risk_profile)))
                amount = round(max(100, min(float(user.initial_cash_balance) * rng.uniform(0.03, 0.20), 50_000)), 2)
                transactions.append((transaction_id, uid, pid, last_date + pd.Timedelta(hours=15), "buy", amount))
                transaction_id += 1
                if rng.random() < 0.18:
                    redeem_date = clipped_date(last_date, int(rng.integers(20, 100)), end)
                    transactions.append((transaction_id, uid, pid, redeem_date + pd.Timedelta(hours=11), "redeem", round(amount * rng.uniform(0.25, 0.90), 2)))
                    transaction_id += 1

    events_df = pd.DataFrame(events, columns=["event_id", "user_id", "event_time", "event_type", "channel", "product_id"])
    transactions_df = pd.DataFrame(
        transactions,
        columns=["transaction_id", "user_id", "product_id", "transaction_time", "transaction_type", "amount"],
    )
    events_df["product_id"] = events_df["product_id"].astype("Int64")
    return events_df.sort_values("event_time"), transactions_df.sort_values("transaction_time")


def generate_experiment(
    users: pd.DataFrame, events: pd.DataFrame, transactions: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    exp_date = pd.Timestamp(EXPERIMENT_DATE)
    visits = events[(events.event_type == "app_visit") & (events.event_time < exp_date)]
    last_visit = visits.groupby("user_id").event_time.max()
    pre_visits = visits[visits.event_time >= exp_date - pd.Timedelta(days=90)].groupby("user_id").size()
    pre_trades = transactions[
        (transactions.transaction_type == "buy")
        & (transactions.transaction_time < exp_date)
        & (transactions.transaction_time >= exp_date - pd.Timedelta(days=90))
    ].groupby("user_id").size()

    frame = users.copy()
    frame["last_visit"] = frame.user_id.map(last_visit).fillna(frame.registered_at)
    frame["days_since_last_visit"] = (exp_date - frame.last_visit).dt.days.clip(lower=0)
    frame["pre_90d_visits"] = frame.user_id.map(pre_visits).fillna(0).astype(int)
    frame["pre_90d_trades"] = frame.user_id.map(pre_trades).fillna(0).astype(int)
    eligible = frame[(frame.marketing_consent == 1) & (frame.registered_at <= exp_date - pd.Timedelta(days=60)) & (frame.days_since_last_visit >= 45)].copy()

    groups = ["control", "education_content", "product_recommendation"]
    assignment = pd.Series(index=eligible.index, dtype="object")
    for _, idx in eligible.groupby(["risk_profile", "city_tier"]).groups.items():
        shuffled = rng.permutation(np.array(list(idx)))
        assignment.loc[shuffled] = np.resize(groups, len(shuffled))
    eligible["experiment_group"] = assignment
    eligible["delivered"] = rng.binomial(1, 0.965, len(eligible))

    group_click_effect = eligible.experiment_group.map({"control": -2.2, "education_content": -0.55, "product_recommendation": -0.35}).to_numpy()
    rec_affinity = (eligible.risk_profile != "cautious").astype(float).to_numpy()
    edu_affinity = (eligible.risk_profile == "cautious").astype(float).to_numpy()
    p_click = sigmoid(-1.65 + group_click_effect + 0.18 * eligible.pre_90d_visits.to_numpy() + 0.30 * rec_affinity)
    clicked = eligible.delivered.to_numpy() * rng.binomial(1, p_click)

    treatment_purchase = np.where(
        eligible.experiment_group == "education_content",
        0.35 + 0.25 * edu_affinity,
        np.where(eligible.experiment_group == "product_recommendation", 0.50 + 0.30 * rec_affinity, 0.0),
    )
    p_purchase = sigmoid(-3.30 + treatment_purchase + 0.20 * clicked + 0.16 * eligible.pre_90d_trades.to_numpy() + 0.10 * (np.log1p(eligible.initial_cash_balance) - 9))
    purchased = eligible.delivered.to_numpy() * rng.binomial(1, p_purchase)
    amount = purchased * np.exp(rng.normal(8.15, 0.85, len(eligible)))
    amount = np.clip(amount, 0, 60_000).round(2)
    retention_bonus = np.where(eligible.experiment_group == "education_content", 0.32, np.where(eligible.experiment_group == "product_recommendation", 0.08, 0.0))
    p_retained = sigmoid(-1.85 + 1.05 * purchased + retention_bonus + 0.10 * eligible.pre_90d_visits.to_numpy())
    retained = rng.binomial(1, p_retained)

    return pd.DataFrame(
        {
            "user_id": eligible.user_id.to_numpy(),
            "experiment_name": "dormant_user_reactivation_v1",
            "assigned_at": exp_date,
            "experiment_group": eligible.experiment_group.to_numpy(),
            "delivered": eligible.delivered.to_numpy(),
            "clicked_7d": clicked,
            "purchased_30d": purchased,
            "purchase_amount_30d": amount,
            "retained_30d": retained,
            "pre_90d_visits": eligible.pre_90d_visits.to_numpy(),
            "pre_90d_trades": eligible.pre_90d_trades.to_numpy(),
            "days_since_last_visit": eligible.days_since_last_visit.to_numpy(),
        }
    )


def generate_campaign_panel(users: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    sample = users[users.registered_at <= pd.Timestamp("2024-06-01")].sample(n=4_000, random_state=RANDOM_SEED).copy()
    sample["pilot_group"] = (sample.city_tier == "T2").astype(int)
    user_effect = rng.normal(0, 0.55, len(sample))
    months = pd.date_range("2024-06-01", "2024-12-01", freq="MS")
    rows: list[pd.DataFrame] = []
    for month_index, month in enumerate(months):
        post = int(month >= pd.Timestamp("2024-09-01"))
        seasonal = [-0.08, -0.03, -0.04, 0.02, 0.08, 0.04, -0.01][month_index]
        treatment_effect = 0.34 * sample.pilot_group.to_numpy() * post
        base = -1.25 + user_effect + 0.18 * sample.marketing_consent.to_numpy() + seasonal
        active = rng.binomial(1, sigmoid(base + treatment_effect))
        inflow_mean = 650 + 240 * sample.pilot_group.to_numpy() + 720 * sample.pilot_group.to_numpy() * post
        net_inflow = active * np.maximum(0, rng.normal(inflow_mean, 1_200, len(sample)))
        rows.append(
            pd.DataFrame(
                {
                    "user_id": sample.user_id.to_numpy(),
                    "month": month,
                    "pilot_group": sample.pilot_group.to_numpy(),
                    "post_period": post,
                    "active_30d": active,
                    "net_inflow": net_inflow.round(2),
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def main() -> None:
    ensure_directories()
    rng = np.random.default_rng(RANDOM_SEED)
    users = generate_users(rng)
    products = generate_products()
    events, transactions = generate_behavior(users, products, rng)
    experiment = generate_experiment(users, events, transactions, rng)
    campaign = generate_campaign_panel(users, rng)

    datasets = {
        "users": users,
        "products": products,
        "events": events,
        "transactions": transactions,
        "experiment_assignments": experiment,
        "campaign_observations": campaign,
    }
    for name, frame in datasets.items():
        frame.to_csv(RAW_DIR / f"{name}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
        print(f"generated {name:24s} {len(frame):>8,} rows")


if __name__ == "__main__":
    main()
