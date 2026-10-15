"""Regression checks for retiring the standalone Prediction Engine page.

The GEM/PDUFA scanner and underlying historical/model files remain available.
Saved retired navigation paths redirect to the main PDUFA workflow.
"""
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"


class RetiredPredictionNavigationTests(unittest.TestCase):
    def test_primary_navigation_has_no_prediction_engine(self):
        app = AppTest.from_file(str(APP), default_timeout=120)
        app.run()
        self.assertFalse(list(app.exception), [str(e.message) for e in app.exception])
        nav = app.radio(key="nav")
        self.assertEqual(list(nav.options), ["PDUFA", "SCANS", "2. PDUFA CALENDAR"])
        self.assertEqual(nav.value, "PDUFA")
        self.assertEqual(app.session_state["pdufa_subtab"], "PIPELINE")
        visible = [t.label for t in app.get("tab") if t.label in
                   {"PIPELINE", "GEM JR + GEM", "SCANS", "PRE PHASE 3", "POST PHASE 3"}]
        self.assertEqual(visible, ["PIPELINE", "GEM JR + GEM", "SCANS"])

    def test_old_prediction_and_optimizer_bookmarks_redirect_to_pipeline(self):
        for legacy in ("9. PREDICTION ENGINE", "10. MATCH OPTIMIZER"):
            with self.subTest(legacy=legacy):
                app = AppTest.from_file(str(APP), default_timeout=120)
                app.session_state["nav"] = legacy
                app.session_state["detail_return_page"] = legacy
                app.run()
                self.assertFalse(list(app.exception), [
                    str(e.message) for e in app.exception])
                self.assertEqual(app.radio(key="nav").value, "PDUFA")
                self.assertEqual(app.session_state["pdufa_subtab"], "PIPELINE")
                self.assertEqual(app.session_state["detail_return_page"], "PDUFA")

    def test_prediction_ui_retired_but_saved_model_sources_untouched(self):
        source = APP.read_text(encoding="utf-8")
        self.assertNotIn('elif page == "9. PREDICTION ENGINE":', source)
        self.assertNotIn('elif page == "10. MATCH OPTIMIZER":', source)
        self.assertNotIn('["PDUFA","2. PDUFA CALENDAR","9. PREDICTION ENGINE"]', source)
        self.assertIn('with nightly_report_tab:', source)
        self.assertIn('render_nightly_scan_report()', source)
        self.assertIn('load_prediction_history', source)
        self.assertIn('def all_source_probability_value', source)
        self.assertIn('Historical', source)
        self.assertTrue((ROOT / "data" / "prediction_engine_history.csv").is_file())


if __name__ == "__main__":
    unittest.main()
