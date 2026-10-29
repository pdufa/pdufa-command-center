"""Fail-closed acquisition action plan tests."""
from research.official_acquisition_next_actions import build_acquisition_next_actions


def test_action_plan_covers_each_case_and_document():
    report = build_acquisition_next_actions()
    assert report["case_count"] == 6
    ids = [a["document_id"] for c in report["cases"].values() for a in c["required_actions"]]
    assert ids and len(ids) == len(set(ids))


def test_action_plan_never_promotes_unverified_evidence():
    report = build_acquisition_next_actions()
    assert report["external_operator_required"] is True
    assert report["official_originals_acquired_by_this_report"] == 0
    assert report["independently_verified_decisions"] == 0
    assert report["prediction_action"] == "ABSTAIN"
    for case in report["cases"].values():
        assert case["ready_for_independent_adjudication"] is False
        assert case["eligible_for_backtesting"] is False
        for action in case["required_actions"]:
            assert action["requires_authorized_original_bytes"] is True
            assert action["requires_independent_review"] is True
