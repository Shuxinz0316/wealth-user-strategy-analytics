"""Load generated CSV files into a constrained SQLite analytics database."""

from __future__ import annotations

import sqlite3

import pandas as pd

from .config import DB_PATH, RAW_DIR, SQL_DIR, ensure_directories


TABLES = ["users", "products", "events", "transactions", "experiment_assignments", "campaign_observations"]


def build_database() -> None:
    ensure_directories()
    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript((SQL_DIR / "00_schema.sql").read_text(encoding="utf-8"))
        for table in TABLES:
            frame = pd.read_csv(RAW_DIR / f"{table}.csv")
            frame.to_sql(table, connection, if_exists="append", index=False)
            print(f"loaded {table:24s} {len(frame):>8,} rows")
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {result}")
    print(f"database ready: {DB_PATH}")


if __name__ == "__main__":
    build_database()

