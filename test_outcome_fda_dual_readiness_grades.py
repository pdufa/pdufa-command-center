import unittest
from unittest.mock import patch
from outcome_fda_dual_readiness_grades import build_outcome_readiness_grades

class DualReadinessGradeTests(unittest.TestCase):
    def test_research_coverage_is_not_prediction_readiness(self):
        report = build_outcome_readiness_grades()
        evidence = report["evidence_grade"]
        prediction = report["prediction_grade"]
        self.assertEqual(evidence["structured_timelines"], 17)
        self.assertEqual(evidence["selected_action_denominator"], 20)
        self.assertEqual(evidence["documented_timeline_coverage_percent"], 85.0)
        self.assertEqual(evidence["missing_exact_receipt_boundary_actions"], 3)
        self.assertFalse(evidence["ready_for_full_cycle_analysis"])
        self.assertEqual(prediction["label"], "NOT_READY")
        self.assertFalse(prediction["ready_for_prediction_analysis"])
        self.assertEqual(prediction["model_eligible_records"], 0)
        self.assertIsNone(prediction["prediction_probability"])
        self.assertIsNone(prediction["prediction_accuracy_estimate"])

    def test_denominator_inconsistency_fails_closed(self):
        with patch("outcome_fda_dual_readiness_grades.build_receipt_boundary_gap_report",
                   return_value={
                       "selected_action_denominator": 20,
                       "structured_timeline_count": 17,
                       "unlinked_actions_count": 2,
                   }):
            with self.assertRaises(ValueError):
                build_outcome_readiness_grades()

    def test_impossible_certification_fails_closed(self):
        with patch("outcome_fda_dual_readiness_grades.build_receipt_boundary_gap_report",
                   return_value={
                       "selected_action_denominator": 20,
                       "structured_timeline_count": 17,
                       "unlinked_actions_count": 3,
                       "independently_certified_review_cycles": 0,
                       "model_eligible_records": 1,
                   }):
            with self.assertRaises(ValueError):
                build_outcome_readiness_grades()
