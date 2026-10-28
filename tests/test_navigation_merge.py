"""Supported navigation contracts after retirement of the Streamlit entry point.

Session-state names and widget positions from app.py are no longer runtime APIs.
The retained behavior is exercised on real Next.js components: unknown old deep
links fall back safely, SCANS has one published panel, and HOP stays research-only.
"""
import csv
from pathlib import Path
import unittest
from supported_dashboard_checks import run_frontend_contract

ROOT = Path(__file__).resolve().parents[1]


class RetiredPredictionNavigationTests(unittest.TestCase):
    def test_retired_bookmarks_do_not_restore_legacy_screens(self):
        self.assertGreater(run_frontend_contract("retired-navigation-migration.test.cjs"), 0)

    def test_scans_has_one_supported_published_panel(self):
        self.assertGreater(run_frontend_contract("scans-navigation-contract.test.cjs"), 0)
        self.assertGreater(run_frontend_contract("scans-new-results.test.cjs"), 0)

    def test_saved_model_history_remains_explicit_about_independence(self):
        with (ROOT / "data/prediction_engine_history.csv").open(newline="") as stream:
            reader = csv.DictReader(stream)
            self.assertIn("independence_status", reader.fieldnames)
            self.assertIn("event_key", reader.fieldnames)
            rows = list(reader)
        self.assertTrue(rows)
        self.assertTrue(any(row["independence_status"] for row in rows))
        # Existing retrospective probabilities never become HOP predictions.
        self.assertGreater(run_frontend_contract("hop-readiness-api.test.cjs"), 0)

    def test_current_prediction_sources_cannot_silently_enable_a_model(self):
        self.assertGreater(run_frontend_contract("science-outcome-gates.test.cjs"), 0)
        self.assertGreater(run_frontend_contract("hop-source-diagnostic.test.cjs"), 0)


if __name__ == "__main__":
    unittest.main()
