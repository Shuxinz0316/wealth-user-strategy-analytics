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


def ensure_directories() -> None:
    for path in (RAW_DIR, TABLE_DIR, CHART_DIR):
        path.mkdir(parents=True, exist_ok=True)

