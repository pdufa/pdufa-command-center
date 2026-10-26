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
        manifest = report["blocking_gate_manifest"]
        self.assertFalse(manifest["all_prediction_gates_passed"])
        self.assertEqual(manifest["blocking_condition_count"], 5)
        self.assertEqual(manifest["blocking_conditions"]["unresolved_fda_receipt_boundaries"], 3)
        self.assertEqual(manifest["blocking_conditions"]["uncertified_structured_review_cycles"], 17)

    def test_denominator_inconsistency_fails_closed(self):
        with patch("outcome_fda_dual_readiness_grades.build_receipt_boundary_gap_report",
                   return_value={
                       "selected_action_denominator": 20,
                       "structured_timeline_count": 17,
                       "unlinked_actions_count": 2,
                   }):
            with self.assertRaises(ValueError):
                build_outcome_readiness_grades()

    def test_unverified_denominator_and_probability_cannot_be_overridden(self):
        base = {
            "selected_action_denominator": 20,
            "structured_timeline_count": 17,
            "unlinked_actions_count": 3,
            "independently_certified_review_cycles": 0,
            "model_eligible_records": 0,
            "fda_exact_receipt_days_independently_verified": 0,
            "complete_application_denominator_verified": False,
            "prediction_probability": None,
        }
        for change in (
            {"complete_application_denominator_verified": True},
            {"prediction_probability": 0.9},
            {"fda_exact_receipt_days_independently_verified": 1},
        ):
            with self.subTest(change=change):
                with patch("outcome_fda_dual_readiness_grades.build_receipt_boundary_gap_report",
                           return_value={**base, **change}):
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
