"""Reference-image GEM page contract: source data, ranked controls and disclosures."""
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from gem_visual_page import _show, _rankings

ROOT = Path(__file__).resolve().parents[1]


class GemVisualPageTests(unittest.TestCase):
    def test_missing_data_is_never_represented_as_an_actual_score(self):
        self.assertEqual(_show(None), "NOT AVAILABLE")
        self.assertEqual(_show("nan"), "NOT AVAILABLE")
        self.assertEqual(_show("  "), "NOT AVAILABLE")
        self.assertEqual(_show("2026-10-15"), "2026-10-15")

    @patch("gem_visual_page.assess_gem_trade")
    @patch("gem_visual_page.exact_event", return_value={"company": "Test"})
    @patch("gem_visual_page.load_market_rows", return_value={})
    def test_junior_research_does_not_gain_gem_trade_scores(
        self, market, event, assess
    ):
        assess.return_value = {"base": {"status": "NO SOURCE"}, "bars": [],
                               "recommendation": "WAIT"}
        candidates = [{"Ticker": "TEST", "Exact program": "TEST|TRIAL1",
                       "Drug": "Research only"}]
        rows = _rankings("GEM JR", candidates, "data", date(2026, 10, 15))
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0][4]["entry"])
        self.assertIsNone(rows[0][4]["exit_risk"])
        self.assertIsNone(rows[0][4]["quality"])

    def test_image_sections_and_real_w_t_callbacks_are_present(self):
        source = (ROOT / "gem_visual_page.py").read_text(encoding="utf-8")
        for text in (
            "Candidate Priority Table", "Selected Candidate · Full Profile",
            "Three-Level Nested Clinical Trials", "Financing, SEC Verification",
            "Trading Chart · Price, Base, Breakout & Volume",
            "Technical Entry / Exit Signals", "ENTRY READINESS",
            "EXIT RISK", "Timeline · PDUFA · Dead Zone",
            "Hard Stops · PDUFA Decision", "News · Alerts",
            "Scan Scheduler · Diagnostics", "Promotion · Exit History",
            "LEVEL 1 · COMPANY", "LEVEL 2 · DRUG", "LEVEL 3 · PHASE 3",
            'on_click=_toggle, args=(symbol, "watch")',
            'on_click=open_trade_workspace, args=(symbol,)',
        ):
            with self.subTest(section=text):
                self.assertIn(text, source)
        self.assertNotIn('with st.expander("LEVEL 1', source)
        self.assertIn('key="visual_" + stageid + "_level1"', source)
        self.assertIn('key="visual_" + stageid + "_level2"', source)


if __name__ == "__main__":
    unittest.main()
