"""Execute portfolio SQL analyses and export reproducible result tables."""

from __future__ import annotations

import sqlite3

import pandas as pd

from .config import DB_PATH, SQL_DIR, TABLE_DIR, ensure_directories


QUERIES = {
    "user_lifecycle": "01_user_lifecycle.sql",
    "conversion_funnel": "02_conversion_funnel.sql",
    "user_segmentation": "03_user_segmentation.sql",
    "retention": "04_retention.sql",
    "experiment_results": "05_experiment_results.sql",
    "monthly_kpis": "06_monthly_kpis.sql",
    "churn_features": "07_churn_features.sql",
}


def run_queries() -> None:
    ensure_directories()
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}. Run `make data` first.")
    with sqlite3.connect(DB_PATH) as connection:
        for output_name, sql_file in QUERIES.items():
            query = (SQL_DIR / sql_file).read_text(encoding="utf-8")
            frame = pd.read_sql_query(query, connection)
            output_path = TABLE_DIR / f"{output_name}.csv"
            frame.to_csv(output_path, index=False)
            print(f"exported {output_name:24s} {len(frame):>8,} rows")


if __name__ == "__main__":
    run_queries()

