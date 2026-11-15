from copy import deepcopy
from datetime import date
import pytest
from app.scientific_binary_effects import binary_effect
from app.candidate_assessments import score_candidate


def record():
    return {"nctId":"NCT00000001", "source":"https://clinicaltrials.gov/study/NCT00000001",
            "sourceDate":"2026-01-01", "sourceRetrievedAt":"2026-01-02", "sourceVerifiedAt":"2026-01-03",
            "reviewedAt":"2026-01-04", "reviewerId":"synthetic-test-owner", "sourceVerifiedBy":"synthetic-test-owner",
            "sourceVerificationMethod":"DIRECT_DOCUMENT_REVIEW", "documentType":"TRIAL_REPORT",
            "sourceVerified":True, "judgment":"INCONCLUSIVE", "rationale":"Synthetic test, not real review",
            "evidenceExcerpt":"Synthetic 20/100 versus 10/100 event counts", "retrievalProvenance":"RECORDED",
            "measurements":{"outcomeType":"BINARY_EVENT", "endpoint":"Synthetic event", "population":"ITT",
                "timeFrame":"12 weeks", "treatment":{"label":"A", "events":20, "total":100},
                "comparator":{"label":"B", "events":10, "total":100}}}


def test_exact_descriptive_arithmetic_without_invented_precision_or_prediction():
    result = binary_effect(record())
    assert result["absoluteRiskDifference"] == pytest.approx(.1)
    assert result["riskRatio"] == pytest.approx(2)
    assert result["confidenceInterval"] is None
    assert result["clinicalSignificance"] == "NOT_ASSESSED"
    assert result["fdaPrediction"] == "ABSTAIN"
    assert result["provenance"]["reviewerId"] == "synthetic-test-owner"


@pytest.mark.parametrize("events,total", [(101,100),(-1,100),(1,0),(True,100),(1.5,100),(1,float('inf'))])
def test_invalid_numerators_and_denominators_are_rejected(events,total):
    value=record();value["measurements"]["treatment"].update(events=events,total=total)
    assert binary_effect(value)["status"] == "REJECTED_MEASUREMENTS"


def test_zero_events_are_not_missing_and_no_continuity_correction_is_invented():
    value=record();value["measurements"]["comparator"]["events"]=0
    result=binary_effect(value)
    assert result["comparator"]["eventRate"] == 0
    assert result["riskRatio"] is None
    assert result["riskRatioStatus"] == "UNDEFINED_ZERO_COMPARATOR_EVENTS"


def test_unretrieved_and_incomplete_population_do_not_trigger_calculations():
    for change in [lambda x:x.update(retrievalProvenance="NOT_RECORDED"), lambda x:x["measurements"].update(population="")]:
        value=record();change(value)
        assert binary_effect(value)["status"] == "NOT_ASSESSED"


def test_level_three_and_four_calculate_only_after_exact_trial_source_review():
    registry={"nct_id":"NCT00000001", "phases":["PHASE3"], "status":"COMPLETED", "last_update_posted":{"date":"2026-01-01"}}
    reviews={"scientificLevelEvidence":{key:record() for key in ["3.effectSizeAndPrecision","4.adverseEvents","4.seriousAdverseEvents","4.discontinuations"]}}
    def assess(value):
        return score_candidate({"id":"TRIAL|NCT00000001"},registry,reviews=value,today=date(2026,2,1),registry_checked="2026-01-02T12:00:00Z")
    result=assess(reviews)
    for level in ["3","4"]:
        assert result["levelsTwoToSix"][level]["descriptiveCalculations"]
        assert result["levelsTwoToSix"][level]["score"] is None
        assert result["levelsTwoToSix"][level]["scientificValidation"] == "NOT_VERIFIED"
    for mutation in [{"nctId":"NCT00000002"},{"sourceRetrievedAt":"2026-03-01"},{"sourceVerified":False},{"conflict":True}]:
        rejected=deepcopy(reviews)
        for item in rejected["scientificLevelEvidence"].values(): item.update(mutation)
        result=assess(rejected)
        assert not result["levelsTwoToSix"]["3"]["descriptiveCalculations"]
        assert not result["levelsTwoToSix"]["4"]["descriptiveCalculations"]
