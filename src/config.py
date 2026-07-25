from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "wealth_analytics.db"
SQL_DIR = ROOT / "sql"
TABLE_DIR = ROOT / "outputs" / "tables"
CHART_DIR = ROOT / "outputs" / "charts"

RANDOM_SEED = 20260721
N_USERS = 12_000
OBSERVATION_END = "2025-03-31"
EXPERIMENT_DATE = "2025-01-15"

# Explicit business assumptions used by the synthetic experiment.
RISK_LEVEL_LIMIT = {"cautious": 2, "balanced": 3, "aggressive": 4}
CAMPAIGN_UNIT_COST = {
    "control": 0.0,
    "education_content": 0.45,
    "product_recommendation": 1.20,
}
ROLLOUT_BASE_USERS = 10_000
BUSINESS_GUARDRAILS = {
    "max_complaint_rate": 0.01,
    "max_redemption_rate_among_buyers": 0.20,
    "min_suitability_pass_rate": 1.0,
}


def ensure_directories() -> None:
    for path in (RAW_DIR, TABLE_DIR, CHART_DIR):
        path.mkdir(parents=True, exist_ok=True)
