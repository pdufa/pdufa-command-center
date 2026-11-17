"""Synthetic-only tests for benefit/harm context comparison."""
from copy import deepcopy

from app.scientific_levels_nine_to_twenty import assess_levels_nine_to_twenty
from test_scientific_levels_nine_to_twenty import intake, reviewed_record, NCT


def review(measurement):
    record = reviewed_record()
    record["measurements"] = measurement
    return record


def population(endpoint):
    return {
        "endpoint": endpoint,
        "population": "Randomized ITT",
        "treatmentArm": "Study drug",
        "comparatorArm": "Placebo",
        "timeOrigin": "Randomization",
        "followupDays": 90,
    }


def assess(benefit, harm):
    return assess_levels_nine_to_twenty(
        intake(), trial_id=NCT, evidence={
            "9.benefitEvidence": benefit, "9.harmEvidence": harm,
        }
    )["9"]


def test_matching_metadata_is_not_a_positive_benefit_risk_judgment():
    result = assess(review(population("Response rate")), review(population("Adverse events")))
    comparison = result["benefitHarmContextComparison"]
    assert comparison["status"] == "DESCRIPTIVE_CONTEXT_ALIGNMENT_ONLY"
    assert comparison["differences"] == []
    assert comparison["comparability"] == "SAME_DECLARED_CONTEXT"
    assert comparison["score"] is None
    assert comparison["clinicalBenefitRiskConclusion"] is None
    assert comparison["fdaPrediction"] == "ABSTAIN"
    assert result["integrationStatus"] == "BLOCKED_UPSTREAM_EVIDENCE"


def test_different_population_followup_and_arms_do_not_get_pooled():
    harm = population("Adverse events")
    harm["population"] = "Safety treated"
    harm["comparatorArm"] = "Active comparator"
    harm["followupDays"] = 180
    value = assess(review(population("Response")), review(harm))
    comparison = value["benefitHarmContextComparison"]
    assert comparison["status"] == "CONTEXT_DIFFERENCES_REQUIRE_OWNER_REVIEW"
    assert comparison["differences"] == ["population", "comparatorArm", "followupDays"]
    assert comparison["comparability"] == "NOT_ESTABLISHED"
    assert comparison["clinicalBenefitRiskConclusion"] is None


def test_source_cutoff_wrong_trial_and_missing_provenance_fail_closed():
    a = review(population("Response"))
    b = review(population("Adverse events"))
    for change in (
        {"nctId": "NCT00000002"},
        {"sourceRetrievedAt": "2026-03-01"},
        {"sourceVerifiedBy": ""},
        {"conflict": True},
    ):
        bad = deepcopy(a)
        bad.update(change)
        comparison = assess(bad, b)["benefitHarmContextComparison"]
        assert comparison["status"] == "NOT_ASSESSED"
        assert "checks" not in comparison
    a.pop("sourceRetrievedAt")
    assert assess(a, b)["benefitHarmContextComparison"]["status"] == "NOT_ASSESSED"


def test_invalid_measurements_are_rejected_without_coercion():
    a = review(population("Response"))
    b = review(population("Adverse events"))
    for change in (
        {"followupDays": True},
        {"followupDays": -1},
        {"followupDays": 0},
        {"followupDays": 36526},
        {"treatmentArm": ""},
        {"population": None},
    ):
        bad = deepcopy(a)
        bad["measurements"].update(change)
        comparison = assess(bad, b)["benefitHarmContextComparison"]
        assert comparison["status"] == "REJECTED_MEASUREMENTS"
        assert comparison["clinicalBenefitRiskConclusion"] is None


def test_no_owner_review_and_pretrial_results_still_abstain():
    value = assess_levels_nine_to_twenty(
        intake(phase="PHASE1", status="RECRUITING"), trial_id=NCT)
    assert value["9"]["benefitHarmContextComparison"]["status"] == "NOT_ASSESSED"
    assert value["9"]["score"] is None
    assert value["9"]["fdaPrediction"] == "ABSTAIN"
