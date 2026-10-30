from research.fda_prediction_readiness import ReadinessInputs, evaluate_readiness


def test_default_research_readiness_abstains():
    result = evaluate_readiness(ReadinessInputs())
    assert result.ready is False
    assert result.decision == "ABSTAIN"
    assert "No scored prospective outcomes" in result.blockers


def test_even_all_assertions_cannot_certify_prediction():
    result = evaluate_readiness(ReadinessInputs(
        scientific_assessments_complete=True,
        independent_source_review_complete=True,
        original_fda_documents_authenticated=True,
        historical_cutoff_leakage_audit_passed=True,
        prospective_outcomes_scored=100,
        calibration_validated=True,
        model_frozen_before_outcomes=True,
    ))
    assert result.ready is False
    assert result.decision == "ABSTAIN"
    assert "Independent out-of-sample performance certification unavailable" in result.blockers
