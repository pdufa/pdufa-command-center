"""Regression tests for per-exact-trial GEM JR/GEM lifecycle display."""
from supported_dashboard_checks import run_frontend_contract
import ast
import unittest
from pathlib import Path

from gem_trial_hierarchy_ui import trial_card_rows, _benchmark_rows

ROOT = Path(__file__).resolve().parents[1]


class GemLifecycleCardTests(unittest.TestCase):
    def test_same_ticker_two_trials_receive_distinct_cards(self):
        rows = [
            {"Pipeline ID": "TRIAL|NCT11111111", "Ticker": "ABC",
             "Drug": "alpha"},
            {"Pipeline ID": "TRIAL|NCT22222222", "Ticker": "ABC",
             "Drug": "beta"},
            {"Pipeline ID": "TRIAL|NCT11111111", "Ticker": "ABC",
             "Drug": "duplicate"},
            {"Pipeline ID": "", "Ticker": "ABC", "Drug": "unlinked"},
        ]
        selected = trial_card_rows(rows)
        self.assertEqual([x["Pipeline ID"] for x in selected],
                         ["TRIAL|NCT11111111", "TRIAL|NCT22222222"])

    def test_gem_jr_missing_results_not_marked_as_verified(self):
        sample = {"Pipeline ID": "TRIAL|NCT12345678", "Ticker": "ABC",
                  "Evidence type": "Issuer Phase 3 readout (review)",
                  "SEC documents rechecked": 0}
        observations = _benchmark_rows(sample, junior=True)
        self.assertIn("review", observations[0]["Observed"])
        self.assertIn("AWAITING", observations[-1]["Observed"])
        self.assertIn("NOT VERIFIED", observations[1]["Observed"])

    def test_supported_gem_cards_preserve_exact_program_evidence_and_membership(self):
        """Retained product contract, executed against supported Next.js code."""
        self.assertGreater(run_frontend_contract('gem-evidence-rendering.test.cjs'), 0)
        self.assertGreater(run_frontend_contract('gem-research-defaults.test.cjs'), 0)


if __name__ == "__main__":
    unittest.main()

