"""Synthetic-only Level 11 descriptive burden and alternatives checks."""
from copy import deepcopy
from app.scientific_levels_nine_to_twenty import assess_levels_nine_to_twenty
from test_scientific_levels_nine_to_twenty import intake, reviewed_record, NCT


def burden():
    return {
        "disease": "Test disease", "subtype": "A",
        "region": "US", "population": "Adults", "measurementPeriod": "2025",
        "cases": 60, "populationDenominator": 120000,
        "measurementAsOf": "2026-01-01",
    }


def alternatives():
    return {key: val for key, val in burden().items()
            if key in {"disease", "subtype", "region", "population", "measurementPeriod"}} | {
                "namedAlternatives": ["Comparator A", "Supportive care"]}


def reviewed(measurements):
    item = reviewed_record()
    item["measurements"] = measurements
    return item


def assess(b=None, a=None):
    inputs = {"11.populationBurden": b if b is not None else reviewed(burden())}
    if a is not None:
        inputs["11.availableAlternatives"] = a
    return assess_levels_nine_to_twenty(
        intake(), trial_id=NCT, evidence=inputs)["11"]["therapeuticContext"]


def test_descriptive_rate_never_claims_population_prevalence_or_unmet_need():
    result = assess()
    assert result["status"] == "DESCRIPTIVE_BURDEN_ONLY"
    assert result["burden"]["reportedRatePer100k"] == 50
    assert result["burden"]["count"] == 60
    assert result["populationRepresentativeness"] == "NOT_ESTABLISHED"
    assert result["unmetNeedJudgment"] is None
    assert result["fdaPrediction"] == "ABSTAIN"
    assert result["score"] is None
    assert result["alternativesContext"] == "NOT_ASSESSED"


def test_alternatives_context_match_still_no_claim_of_therapeutic_gap():
    result = assess(a=reviewed(alternatives()))
    assert result["status"] == "DESCRIPTIVE_BURDEN_AND_ALTERNATIVE_INVENTORY"
    assert result["alternativesContext"] == "DECLARED_CONTEXT_MATCH"
    assert result["unmetNeedJudgment"] is None
    assert result["reportedNamedAlternatives"] == ["Comparator A", "Supportive care"]


def test_different_population_detected_instead_of_merged():
    changed = alternatives()
    changed["population"] = "Pediatric"
    changed["region"] = "EU"
    result = assess(a=reviewed(changed))
    assert result["alternativesContext"] == "CONTEXT_MISMATCH_REQUIRES_REVIEW"
    assert result["contextDifferences"] == ["region", "population"]


def test_bad_counts_future_measurements_and_bool_are_rejected():
    for mutation in (
        {"cases": True},
        {"cases": -1},
        {"cases": 200000},
        {"populationDenominator": 0},
        {"populationDenominator": 2 ** 54},
        {"measurementAsOf": "2026-02-02"},
    ):
        changed = burden()
        changed.update(mutation)
        result = assess(b=reviewed(changed))
        assert result["status"] == "REJECTED_MEASUREMENTS"


def test_invalid_alternative_list_not_promoted_to_no_treatment():
    alt = alternatives()
    alt["namedAlternatives"] = ["Agent A", "agent a"]
    result = assess(a=reviewed(alt))
    assert result["alternativesContext"] == "INVALID_ALTERNATIVES_REQUIRES_REVIEW"
    assert result["unmetNeedJudgment"] is None
    alt["namedAlternatives"] = []
    assert assess(a=reviewed(alt))["unmetNeedJudgment"] is None


def test_wrong_trial_future_source_and_no_receipt_fail_closed():
    for change in ({"nctId": "NCT99999999"},
                   {"sourceRetrievedAt": "2026-03-01"},
                   {"sourceVerifiedBy": ""}):
        wrong = reviewed(burden())
        wrong.update(change)
        result = assess(b=wrong)
        assert result["status"] == "NOT_ASSESSED"
        assert "burden" not in result


def test_no_review_never_computes_missing_disease_population():
    result = assess_levels_nine_to_twenty(
        intake(phase="PHASE1", status="RECRUITING"), trial_id=NCT)["11"]["therapeuticContext"]
    assert result["status"] == "NOT_ASSESSED"
    assert result["unmetNeedJudgment"] is None
