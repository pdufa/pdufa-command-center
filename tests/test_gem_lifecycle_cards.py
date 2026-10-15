"""Regression tests for per-exact-trial GEM JR/GEM lifecycle display."""
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

    def test_card_and_previous_list_wiring(self):
        ui = (ROOT / "gem_trial_hierarchy_ui.py").read_text(encoding="utf-8")
        junior = (ROOT / "gem_jr_ui.py").read_text(encoding="utf-8")
        gem = (ROOT / "gem_potential_ui.py").read_text(encoding="utf-8")
        master = (ROOT / "gem_nested_master_ui.py").read_text(encoding="utf-8")
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        for name, code in [("ui", ui), ("junior", junior), ("gem", gem),
                           ("master", master), ("app", app)]:
            ast.parse(code, filename=name)
        self.assertIn('with st.container(border=True, key=namespace + "_program_" + uid)', ui)
        self.assertIn('args=(ticker, "watch")', ui)
        self.assertIn('args=(ticker, "trade")', ui)
        self.assertIn("LEVEL 1 — EXACT PROGRAM & LIST STATUS", ui)
        self.assertIn("LEVEL 2 — WHAT THIS CANDIDATE RECEIVED", ui)
        self.assertIn("LEVEL 3 — UNDERLYING EVIDENCE", ui)
        self.assertIn('render_trial_hierarchy(active, namespace="gem_jr"', junior)
        self.assertIn('render_trial_hierarchy(source_cleared,', gem)
        self.assertIn('show_previous=False', app)
        self.assertIn('value=True, key="gem_shared_show_master"', app)
        self.assertIn('key="gem_previous_candidates"', app)
        self.assertIn('if show_previous:', master)


if __name__ == "__main__":
    unittest.main()
