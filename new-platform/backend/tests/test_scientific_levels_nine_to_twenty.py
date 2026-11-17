"""Synthetic-only Level 9–20 contract regressions; no real-world clinical conclusions."""
from datetime import date
from app.scientific_levels_nine_to_twenty import LEVELS, assess_levels_nine_to_twenty
from app.candidate_assessments import score_candidate

NCT = "NCT00000001"

def intake(phase="PHASE3", status="COMPLETED"):
    return {
        "executionStatus": "INTAKE_ONLY",
        "scientificValidation": "NOT_VERIFIED",
        "fdaPrediction": "ABSTAIN",
        "assessmentCutoff": "2026-02-01",
        "phase": phase,
        "trialStatus": status,
    }

def reviewed_record():
    return {
        "nctId": NCT,
        "source": f"https://clinicaltrials.gov/study/{NCT}",
        "sourceDate": "2026-01-01",
        "sourceRetrievedAt": "2026-01-05",
        "sourceVerified": True,
        "sourceVerifiedAt": "2026-01-06",
        "sourceVerifiedBy": "owner",
        "sourceVerificationMethod": "REGISTRY_RECORD_REVIEW",
        "reviewedAt": "2026-01-07",
        "judgment": "INCONCLUSIVE",
        "rationale": "Synthetic fixture, not a clinical finding",
        "reviewerId": "owner",
        "documentType": "SYNTHETIC_FIXTURE",
        "evidenceExcerpt": "Synthetic evidence only.",
    }

def test_full_numbering_is_12_distinct_contracts_and_never_scores():
    result = assess_levels_nine_to_twenty(intake(), trial_id=NCT)
    assert tuple(LEVELS) == tuple(range(9, 21))
    assert set(result) == {str(i) for i in range(9, 21)}
    for level in result.values():
        assert level["score"] is None
        assert level["fdaPrediction"] == "ABSTAIN"
        assert level["scientificValidation"] == "NOT_VERIFIED"
        assert level["validationStatus"] == "NOT_VALIDATED"
        assert "NOT_IMPLEMENTED" in level["methodStatus"] or "PARTIAL" in level["methodStatus"]

def test_no_upstream_data_never_creates_positive_benefit_risk_conclusion():
    result = assess_levels_nine_to_twenty(intake(), trial_id=NCT)
    assert result["9"]["integrationStatus"] == "BLOCKED_UPSTREAM_EVIDENCE"
    assert result["9"]["benefitRiskEvidenceAlignment"]["benefitEvidenceReviewed"] is False
    assert result["9"]["criteria"]["benefitEvidence"] == "NOT_ASSESSED"

def test_forged_or_future_review_not_accepted():
    valid = reviewed_record()
    wrong = {**valid, "nctId": "NCT00000002"}
    late = {**valid, "sourceRetrievedAt": "2026-03-01"}
    unverifiable = {**valid, "sourceVerifiedBy": ""}
    for case in (wrong, late, unverifiable):
        result = assess_levels_nine_to_twenty(
            intake(), trial_id=NCT, evidence={"9.benefitEvidence": case})
        assert result["9"]["acceptedEvidence"] == {}
        assert result["9"]["criteria"]["benefitEvidence"] == "REJECTED_EVIDENCE"

def test_a_valid_review_is_only_coverage_not_scientific_acceptance():
    result = assess_levels_nine_to_twenty(
        intake(), trial_id=NCT, evidence={"9.benefitEvidence": reviewed_record()})
    assert result["9"]["criteria"]["benefitEvidence"] == "INCONCLUSIVE"
    assert result["9"]["reviewedCount"] == 1
    assert result["9"]["score"] is None
    assert result["9"]["integrationStatus"] == "BLOCKED_UPSTREAM_EVIDENCE"

def test_pre_application_does_not_count_unavailable_filing_as_deficiency():
    result = assess_levels_nine_to_twenty(
        intake(phase="PHASE1", status="RECRUITING"), trial_id=NCT)
    assert result["13"]["criteria"]["acceptedFiling"] == "NOT_YET_EXPECTED"
    assert result["16"]["criteria"]["inspectionEvidence"] == "NOT_YET_EXPECTED"
    assert result["20"]["criteria"]["officialActionAndDate"] == "NOT_YET_EXPECTED"
    assert result["9"]["criteria"]["benefitEvidence"] == "NOT_YET_EXPECTED"

def test_wrong_phase_fails_closed_all_levels():
    result = assess_levels_nine_to_twenty(
        {**intake(), "phase": "NOT_REAL"}, trial_id=NCT,
        evidence={"9.benefitEvidence": reviewed_record()})
    assert all(value["status"] == "BLOCKED_UNVERIFIED_PHASE" for value in result.values())

def test_candidate_scoring_returns_contracts_without_fda_prediction():
    reg = {
        "nct_id": NCT, "phases": ["PHASE3"], "status": "COMPLETED",
        "last_update_posted": {"date": "2026-01-15"},
    }
    result = score_candidate(
        {"id": f"TRIAL|{NCT}", "nctId": NCT}, reg,
        registry_checked="2026-01-20T09:00:00+00:00",
        today=date(2026, 2, 1),
    )
    for number in range(9, 21):
        value = result["levelsSevenToTwenty"][str(number)]
        assert value["score"] is None
        assert value["fdaPrediction"] == "ABSTAIN"
    assert result["scientificReadiness"]["scientificEngineLevels"] == list(range(1, 9))
    assert result["scientificReadiness"]["contractOnlyLevels"] == list(range(9, 21))
