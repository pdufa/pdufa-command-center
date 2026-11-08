from app.medical_grading_policy import grading_policy
from app.medical_method_projection import project_trial_history


def test_policy_discloses_limits_and_never_scores_unexamined_evidence():
    policy = grading_policy()
    assert [a["grade"] for a in policy["anchors"]] == list(range(6))
    assert policy["automaticGradingEnabled"] is False
    assert policy["historicalEventsCertifiedAgainstPolicy"] is False
    assert policy["certainty"] == "NOT_VALIDATED"
    assert set(policy["fdaPredictions"].values()) == {"ABSTAIN"}
    result = project_trial_history({"nct": "NCT06081894", "explicitGapEvents": [
        {"assessment_index": 1, "method_index": 1, "gap_code": "MISSING_FUTURE_PHASE_RESULTS"}
    ]}, assessment_index=1)
    assert result["gradingPolicy"] == policy
    assert result["counts"]["SCORED"] == 0
    assert result["selectedAssessment"]["scoreOutOf100"] is None
    policy["anchors"].clear()
    assert len(grading_policy()["anchors"]) == 6
