"""Business-quality checks for the deterministic portfolio outputs."""

from __future__ import annotations

import json
import unittest

import pandas as pd

from src.config import RAW_DIR, ROOT, TABLE_DIR


class PortfolioOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        required = [TABLE_DIR / "conversion_funnel.csv", ROOT / "outputs" / "analysis_summary.json"]
        if not all(path.exists() for path in required):
            from src.pipeline import main

            main()

    def test_primary_keys_are_unique(self) -> None:
        for file_name, key in [
            ("users.csv", "user_id"),
            ("events.csv", "event_id"),
            ("transactions.csv", "transaction_id"),
        ]:
            frame = pd.read_csv(RAW_DIR / file_name)
            self.assertFalse(frame[key].duplicated().any(), f"duplicate {key} in {file_name}")

    def test_funnel_is_monotonic(self) -> None:
        funnel = pd.read_csv(TABLE_DIR / "conversion_funnel.csv")
        total = funnel[funnel.acquisition_channel == "ALL"].iloc[0]
        counts = [total.registered_users, total.visitors, total.opened_users, total.first_investors, total.repeat_investors]
        self.assertTrue(all(left >= right for left, right in zip(counts, counts[1:])))

    def test_experiment_assignment_is_balanced(self) -> None:
        experiment = pd.read_csv(RAW_DIR / "experiment_assignments.csv")
        counts = experiment.experiment_group.value_counts()
        self.assertLessEqual(int(counts.max() - counts.min()), 6)

    def test_high_value_segments_have_positive_aum(self) -> None:
        segments = pd.read_csv(TABLE_DIR / "user_segmentation.csv")
        high_value = segments[segments.strategy_segment.str.startswith("high_value")]
        self.assertTrue((high_value.aum > 0).all())

    def test_experiment_and_did_recover_known_effects(self) -> None:
        experiment = pd.read_csv(TABLE_DIR / "experiment_significance.csv")
        product = experiment[experiment.treatment == "product_recommendation"].iloc[0]
        self.assertGreater(product.absolute_lift, 0)
        self.assertLess(product.p_value, 0.05)
        did = pd.read_csv(TABLE_DIR / "did_results.csv")
        interaction = did[did.term == "interaction"].iloc[0]
        self.assertGreater(interaction.coefficient, 0.02)
        self.assertLess(interaction.coefficient, 0.12)
        self.assertLess(interaction.p_value, 0.05)

    def test_summary_metrics_are_valid_probabilities(self) -> None:
        summary = json.loads((ROOT / "outputs" / "analysis_summary.json").read_text())
        for value in summary["funnel"].values():
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 1)
        self.assertGreater(summary["model"]["churn_model_auc"], 0.5)


if __name__ == "__main__":
    unittest.main()

