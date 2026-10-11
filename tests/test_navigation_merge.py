"""Regression checks for removing the standalone Match Optimizer page.

The prediction model's original histories and threshold functions must remain
available from Prediction Engine; the primary landing workflow is Pipeline.
"""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


class ConsolidatedPredictionNavigationTests(unittest.TestCase):
    def test_primary_landing_and_return_to_pdufa_open_pipeline(self):
        app = AppTest.from_file(str(APP), default_timeout=120)
        app.run()
        self.assertFalse(list(app.exception), [str(e.message) for e in app.exception])
        nav = app.radio(key="nav")
        self.assertEqual(nav.options[0], "PDUFA")
        self.assertEqual(nav.value, "PDUFA")
        self.assertNotIn("10. MATCH OPTIMIZER", nav.options)
        self.assertEqual(app.session_state["pdufa_subtab"], "PIPELINE")
        self.assertEqual([t.label for t in app.get("tab")][:3],
                         ["PIPELINE", "PRE PHASE 3", "POST PHASE 3"])

        app.session_state["pdufa_subtab"] = "PRE PHASE 3"
        app.radio(key="nav").set_value("9. PREDICTION ENGINE").run()
        self.assertFalse(list(app.exception))
        app.radio(key="nav").set_value("PDUFA").run()
        self.assertFalse(list(app.exception))
        self.assertEqual(app.session_state["pdufa_subtab"], "PIPELINE")

    def test_legacy_optimizer_redirects_to_preserved_validation(self):
        app = AppTest.from_file(str(APP), default_timeout=120)
        app.session_state["nav"] = "10. MATCH OPTIMIZER"
        app.session_state["detail_return_page"] = "10. MATCH OPTIMIZER"
        app.run()
        self.assertFalse(list(app.exception), [str(e.message) for e in app.exception])
        self.assertEqual(app.radio(key="nav").value, "9. PREDICTION ENGINE")
        self.assertEqual(app.session_state["detail_return_page"], "9. PREDICTION ENGINE")
        self.assertEqual(app.session_state["prediction_subtab"], "HISTORICAL MATCH VALIDATION")
        tabs = [tab.label for tab in app.get("tab")]
        self.assertIn("PREDICTIONS", tabs)
        self.assertIn("HISTORICAL MATCH VALIDATION", tabs)
        text = " ".join(item.body for item in app.markdown)
        self.assertIn("FDA-V3 decision-safe benchmark", text)
        self.assertIn("STEP 3 — Tune the high-confidence F gate", text)
        self.assertIn("STEP 5 — Lock thresholds and test the untouched holdout", text)

    def test_all_optimizer_features_stay_inside_prediction_page(self):
        source = APP.read_text(encoding="utf-8")
        self.assertNotIn('elif page == "10. MATCH OPTIMIZER":', source)
        self.assertIn('with validation_tab:', source)
        self.assertIn('if validation_tab.open:', source)
        for label in (
            "FDA-V3 decision-safe benchmark",
            "100% Directional Layer — full-coverage benchmark",
            "STEP 1 — Historical cohorts",
            "STEP 2 — Decision-safe eligibility gate",
            "STEP 3 — Tune the high-confidence F gate",
            "STEP 4 — Analyze every tune-year miss",
            "STEP 5 — Lock thresholds and test the untouched holdout",
            "STEP 6 — Recommended prospective F gate",
        ):
            self.assertIn(label, source)


if __name__ == "__main__":
    unittest.main()
