"""Independent unit checks of descriptive source arithmetic; no FDA/clinical scoring."""
from decimal import Decimal
import pytest

from app.medical_pilot_source_reconciliation import (
    CountCitation, arithmetic_audit, cross_source_counts, pilot_research_docket)


def test_pilot_safety_differences_are_kept_unreconciled_without_clinical_grades():
    d=pilot_research_docket()
    assert d["nct"]=="NCT06081894"
    assert d["reconciliation"]["reportCountDifferences"]==["TREATED","PLACEBO"]
    assert d["reconciliation"]["status"]=="NEEDS_ORIGINAL_EVENT_DEFINITION_WINDOW_RECONCILIATION"
    assert d["reconciliation"]["clinicalDefinitionAndWindowAgreement"]=="NOT_VERIFIED"
    assert d["reconciliation"]["scientificGrade"] is None
    assert d["reconciliation"]["phaseReviewerSignoff"] is False
    assert d["reconciliation"]["predictionAccuracy"]=="NOT_CALIBRATED"
    assert set(d["methodAssignments"])=={"5.3","8.2"}
    assert d["officialMethodGradesWritten"]==0
    assert d["fdaPrediction"]=="ABSTAIN"


def test_original_secondary_interruption_percentages_do_not_fit_randomized_denominators():
    d=pilot_research_docket()["secondaryInterruptionArithmetic"]
    assert d["recordedCounts"]==[14,1]
    assert d["providedDenominators"]==[258,259]
    assert d["reportedPercentages"]==["2.7","0.8"]
    assert d["arithmeticFromProvidedDenominators"]==["5.4","0.4"]
    assert d["needsOriginalDenominatorReview"]==["TREATED","PLACEBO"]
    assert d["status"]=="PERCENT_DENOMINATOR_RECHECK"


def test_expected_arm_level_percentages_are_arithmetically_compatible():
    example=CountCitation(
        "https://clinicaltrials.gov/study/NCT06081894",
        "Serious adverse events of heart failure",11,258,1,259,
        Decimal("4.3"),Decimal("0.4"),"Unknown original event-set cutoff and trial safety denominator")
    audit=arithmetic_audit(example)
    assert audit["arithmeticFromProvidedDenominators"]==["4.3","0.4"]
    assert audit["needsOriginalDenominatorReview"]==[]
    assert audit["status"]=="ARITHMETIC_CONSISTENT_NOT_CLINICALLY_ADJUDICATED"


def test_missing_reported_percentages_remain_unknown_not_automatically_zero():
    example=CountCitation(
        "https://clinicaltrials.gov/study/NCT06081894",
        "Serious adverse events of heart failure",0,258,0,259,
        None,None,"Synthetic counts for purely arithmetic verification, not actual results")
    audit=arithmetic_audit(example)
    assert audit["reportedPercentages"]==[None,None]
    assert audit["status"]=="ARITHMETIC_CONSISTENT_NOT_CLINICALLY_ADJUDICATED"


@pytest.mark.parametrize("bad", [
    {"treated":True},{"treated":259},{"treated_denominator":0},
    {"control":-1},{"control_denominator":0},
    {"published_treated_percent":Decimal("-1")},
    {"published_control_percent":Decimal("100.1")},
])
def test_invalid_counts_and_rates_fail_closed(bad):
    props=dict(source_url="https://clinicaltrials.gov/study/NCT06081894",
         outcome_definition="Serious adverse events of heart failure",
         treated=11,treated_denominator=258,control=1,control_denominator=259,
         published_treated_percent=Decimal("4.3"),
         published_control_percent=Decimal("0.4"),
         source_context="Source window and clinical definition not independently reconciled")
    props.update(bad)
    with pytest.raises(ValueError):
        arithmetic_audit(CountCitation(**props))


def test_mismatched_event_categories_cannot_be_compared_as_equivalent():
    a=CountCitation("https://clinicaltrials.gov/study/NCT06081894",
      "Any serious adverse event",52,258,38,259,None,None,
      "Randomized arms only; safety population and period not adjudicated")
    b=CountCitation("https://clinicaltrials.gov/study/NCT06081894",
      "Serious adverse events of heart failure",12,258,3,259,None,None,
      "Randomized arms only; safety population and period not adjudicated")
    with pytest.raises(ValueError,match="Different event definitions"):
        cross_source_counts(a,b)
