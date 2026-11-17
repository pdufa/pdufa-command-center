"""Level 10 synthetic, dated guideline and comparator context regressions."""
from copy import deepcopy

from app.scientific_levels_nine_to_twenty import assess_levels_nine_to_twenty
from test_scientific_levels_nine_to_twenty import intake, reviewed_record, NCT


def guideline():
    return {
        "disease": "Rare disease", "subtype": "Subtype A",
        "setting": "Second line", "region": "US",
        "guidelineName": "Synthetic consensus", "guidelineEffectiveDate": "2026-01-01",
    }


def comparator():
    return {
        "disease": "Rare disease", "subtype": "Subtype A",
        "setting": "Second line", "region": "US",
        "comparatorName": "Synthetic standard treatment",
    }


def evidence(value):
    item = reviewed_record()
    item["measurements"] = value
    return item


def assess(a=None, b=None):
    return assess_levels_nine_to_twenty(
        intake(), trial_id=NCT,
        evidence={"10.datedGuidelines": a if a is not None else evidence(guideline()),
                  "10.standardOfCare": b if b is not None else evidence(comparator())},
    )["10"]


def test_source_reviewed_comparator_context_is_not_an_appropriateness_verdict():
    level = assess()
    result = level["standardOfCareContext"]
    assert result["status"] == "CONTEXT_MATCH_REQUIRES_CLINICAL_REVIEW"
    assert result["guidelineEffectiveDate"] == "2026-01-01"
    assert result["contextDifferences"] == []
    assert result["applicabilityEvidenceReviewed"] is False
    assert result["guidelineCurrent"] is None
    assert result["comparatorClinicallyAppropriate"] is None
    assert result["fdaPrediction"] == "ABSTAIN"
    assert level["score"] is None


def test_region_subtype_or_setting_difference_requires_review():
    alt = comparator()
    alt["region"] = "EU"
    alt["subtype"] = "Subtype B"
    alt["setting"] = "First line"
    result = assess(b=evidence(alt))["standardOfCareContext"]
    assert result["status"] == "CONTEXT_DIFFERENCE_REQUIRES_REVIEW"
    assert result["contextDifferences"] == ["subtype", "setting", "region"]


def test_guideline_after_cutoff_is_not_available_as_of_assessment():
    late = guideline()
    late["guidelineEffectiveDate"] = "2026-02-02"
    result = assess(a=evidence(late))["standardOfCareContext"]
    assert result["status"] == "REJECTED_MEASUREMENTS"
    assert result["reason"] == "GUIDELINE_POSTDATES_ASSESSMENT"


def test_wrong_trial_or_future_retrieval_rejects_context():
    a = evidence(guideline())
    for change in ({"nctId": "NCT00000002"},
                   {"sourceRetrievedAt": "2026-03-02"},
                   {"sourceVerifiedBy": ""}):
        wrong = deepcopy(a)
        wrong.update(change)
        result = assess(a=wrong)["standardOfCareContext"]
        assert result["status"] == "NOT_ASSESSED"
        assert "contextChecks" not in result


def test_missing_or_invalid_structure_never_invents_comparator():
    for mutation in ({"comparatorName": ""},
                     {"region": None},
                     {"setting": True}):
        value = comparator()
        value.update(mutation)
        result = assess(b=evidence(value))["standardOfCareContext"]
        assert result["status"] == "REJECTED_MEASUREMENTS"


def test_pre_application_no_review_means_unassessed():
    result = assess_levels_nine_to_twenty(
        intake(phase="PHASE1", status="RECRUITING"), trial_id=NCT)["10"]
    assert result["standardOfCareContext"]["status"] == "NOT_ASSESSED"
    assert result["fdaPrediction"] == "ABSTAIN"
