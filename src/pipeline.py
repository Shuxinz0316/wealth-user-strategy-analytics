"""Run the complete portfolio pipeline from synthetic data to decisions."""

from .analyze import main as analyze
from .build_database import build_database
from .generate_data import main as generate_data
from .run_sql_analysis import run_queries


def main() -> None:
    generate_data()
    build_database()
    run_queries()
    analyze()


if __name__ == "__main__":
    main()

