import unittest
from unittest.mock import patch
from outcome_fda_readiness_panel import build_outcome_readiness_panel

class ReadinessPanelTests(unittest.TestCase):
    def test_primary_and_collapsed_secondary_display(self):
        panel = build_outcome_readiness_panel()
        primary = panel["primary"]
        secondary = panel["secondary"]
        self.assertEqual(primary["documented_timeline_coverage_percent"], 85.0)
        self.assertEqual(primary["documented_timeline_numerator"], 17)
        self.assertEqual(primary["selected_action_denominator"], 20)
        self.assertEqual(primary["prediction_grade"], "NOT_READY")
        self.assertFalse(primary["prediction_ready"])
        self.assertIsNone(primary["prediction_probability"])
        self.assertIsNone(primary["prediction_accuracy_estimate"])
        self.assertTrue(secondary["collapsible"])
        self.assertTrue(secondary["initially_collapsed"])
        self.assertEqual(secondary["blocking_condition_count"], 5)
        self.assertEqual(len(secondary["blocking_conditions"]), 5)
        self.assertEqual([x["affected_count"] for x in secondary["blocking_conditions"]
                          if x["affected_count"] is not None], [3, 17])

    def test_missing_gate_is_rejected(self):
        from outcome_fda_dual_readiness_grades import build_outcome_readiness_grades
        grades = build_outcome_readiness_grades()
        del grades["blocking_gate_manifest"]["blocking_conditions"][
            "no_held_out_chronological_calibration"]
        with patch("outcome_fda_readiness_panel.build_outcome_readiness_grades",
                   return_value=grades):
            with self.assertRaises(ValueError):
                build_outcome_readiness_panel()

    def test_no_authorized_prediction_in_research_panel(self):
        from outcome_fda_dual_readiness_grades import build_outcome_readiness_grades
        grades = build_outcome_readiness_grades()
        grades["prediction_grade"]["ready_for_prediction_analysis"] = True
        with patch("outcome_fda_readiness_panel.build_outcome_readiness_grades",
                   return_value=grades):
            with self.assertRaises(ValueError):
                build_outcome_readiness_panel()
