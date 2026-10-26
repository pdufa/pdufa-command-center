"""Regression guards: incomplete FDA receipt evidence cannot become model clearance."""
from outcome_fda_dual_readiness_grades import build_outcome_readiness_grades
from outcome_fda_receipt_asof_audit import build_receipt_asof_audit
from outcome_fda_receipt_boundary_gap_report import build_receipt_boundary_gap_report


def test_open_receipt_boundaries_remain_uncertified():
    report = build_receipt_boundary_gap_report()
    assert report["selected_action_denominator"] >= report["structured_timeline_count"]
    assert report["unlinked_actions_count"] == len(report["unlinked_actions"])
    assert report["fda_exact_receipt_days_independently_verified"] == 0
    assert report["model_eligible_records"] == 0
    assert report["complete_application_denominator_verified"] is False
    for action in report["unlinked_actions"]:
        assert action["exact_submission_received_date"] is None
        assert action["receipt_date_verified"] is False
        assert action["review_cycle_independently_certified"] is False
        assert action["model_eligible"] is False


def test_historical_asof_audit_does_not_leak_retrospective_labels():
    audit = build_receipt_asof_audit("2024-01-01")
    assert audit["model_eligible_records"] == 0
    assert audit["prediction_probability"] is None
    assert audit["retrospective_action_labels_excluded_from_features"] is True
    for record in audit["records"]:
        assert record["final_fda_action_date_asof"] is None
        assert record["historical_feature_asof_certified"] is False
        assert record["fda_exact_receipt_day"] is None
        assert record["model_eligible"] is False


def test_prediction_grade_remains_blocked_without_certification():
    grades = build_outcome_readiness_grades()
    assert grades["prediction_grade"]["ready_for_prediction_analysis"] is False
    assert grades["prediction_grade"]["prediction_accuracy_estimate"] is None
    assert grades["prediction_grade"]["prediction_probability"] is None
    assert grades["blocking_gate_manifest"]["all_prediction_gates_passed"] is False
