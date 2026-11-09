"""Revision 42 clinicaltrials posted primary outcomes: synthetic integrity tests only."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from scripts.extract_focus_registry_outcomes_r42 import (
    strict_roster, extract_registry_study, collect, _text
)
ROOT=Path(__file__).resolve().parents[1]
ROSTER=json.loads((ROOT/"app/data/focus_snapshot.json").read_text())
APPS=json.loads((ROOT/"app/data/focus_application_snapshot.json").read_text())
def sample(nct,with_results=True):
    registry={"hasResults":with_results,"protocolSection":{
      "identificationModule":{"nctId":nct},
      "statusModule":{"overallStatus":"COMPLETED",
          "lastUpdatePostDateStruct":{"date":"2026-10-01"}},
      "designModule":{"phases":["PHASE3"]}}}
    if with_results:
        registry["resultsSection"]={
          "outcomeMeasuresModule":{"outcomeMeasures":[
            {"type":"PRIMARY","title":"Change from baseline in synthetic endpoint",
             "timeFrame":"Week 36","unitOfMeasure":"points",
             "groups":[{"id":"A","title":"Drug"},{"id":"B","title":"Placebo"}],
             "analyses":[{"pValue":"0.004","method":"ANCOVA",
             "estimate":"1.9","ciLowerLimit":"0.8","ciUpperLimit":"3.0"}],
             "classes":[{"categories":[]}]},
            {"type":"SECONDARY","title":"Secondary","analyses":[]}]},
          "adverseEventsModule":{
            "seriousEvents":[{"term":"Unrelated fictional event","stats":[]}],
            "otherEvents":[{"term":"Other event","stats":[]}]},
          "participantFlowModule":{"groups":[]}
        }
    return registry
def fetched(nct,with_results=True):
    return sample(nct,with_results),{
      "status":"FETCHED","sourceUrl":"https://clinicaltrials.gov/api/v2/studies/"+nct+"?format=json",
      "sha256":"a"*64,"bytes":224,"contentType":"application/json"}
def test_current_29_and_23_crosswalk_is_exact():
    assert len(strict_roster(ROSTER,APPS))==29
    assert len({r["nct"] for r in ROSTER["records"]})==29
def test_report_primary_stats_are_raw_strings_not_derived_clinical_grades():
    nct="NCT05507203"
    obj=extract_registry_study(nct,"ABVX",*fetched(nct))
    assert obj["resultsPresent"] is True
    assert obj["primaryOutcomeCount"]==1
    assert obj["postedSeriousEventRows"]==1
    assert obj["primaryOutcomes"][0]["analysesShown"][0]["pValue"]=="0.004"
    assert obj["primaryOutcomes"][0]["analysesShown"][0]["ciLowerLimit"]=="0.8"
    assert obj["primaryOutcomes"][0]["analysisCount"]==1
    assert obj["primaryOutcomes"][0]["groupLabels"]==["Drug","Placebo"]
    assert obj["pivotalEfficacySigned"] is False
    assert obj["clinicalSafetyReviewed"] is False
    assert obj["originalFirstPublicDateAuthenticated"] is False
    assert obj["noScoresWritten"] is True
def test_absent_registry_results_not_mislabelled_as_failed_trial():
    nct="NCT06081894"
    obj=extract_registry_study(nct,"CYTK",*fetched(nct,False))
    assert obj["resultsPresent"] is False
    assert obj["primaryOutcomeCount"]==0
    assert obj["seriousEventsPresent"] is None
    assert obj["postedResultsEqualCompletePhase3Package"] is False
    assert obj["pivotalEfficacySigned"] is False
def test_nct_identity_or_results_flag_inconsistency_rejected():
    nct="NCT05507203"
    doc,receipt=fetched(nct)
    doc["protocolSection"]["identificationModule"]["nctId"]="NCT00000000"
    with pytest.raises(ValueError,match="REGISTRY_NCT_ID_MISMATCH"):
        extract_registry_study(nct,"ABVX",doc,receipt)
    doc,receipt=fetched(nct)
    doc["hasResults"]=False
    with pytest.raises(ValueError,match="RESULTS_MEMBERSHIP_INCONSISTENT"):
        extract_registry_study(nct,"ABVX",doc,receipt)
def test_all_29_records_and_23_groups_preserve_research_statuses_without_scores():
    known={r["nct"] for r in ROSTER["records"][:12]}
    def mock(nct):return fetched(nct,nct in known)
    x=collect(ROSTER,APPS,fetcher=mock)
    assert x["trialCount"]==29
    assert x["applicationCycleCount"]==23
    assert x["registryRecordsFetched"]==29
    assert x["registryResultsSectionsPresent"]==12
    assert x["registryResultsSectionsAbsent"]==17
    assert x["postedPrimaryOutcomeRecords"]==12
    assert x["trialsWithPostedPrimaryOutcomeRecords"]==12
    assert x["postedPrimaryOutcomeRecordsScientificallyReviewed"]==0
    assert x["independentClinicalReviews"]==0
    assert x["historicalFdaBacktestsCompleted"]==0
    assert x["fdaApprovalProbability"] is None
    assert x["calibratedAccuracy"] is None
    assert x["clinicalGradingAuthorized"] is False
    assert x["predictionsAuthorized"] is False
    assert x["noClinicalOrProductionWrites"] is True
    assert all(i["noScoresWritten"] for i in x["trials"])
    assert all(i["independentReviewerSignoff"] is False for i in x["trials"])
def test_unavailable_record_is_unknown_not_absent_results():
    def mock(nct):
        if nct=="NCT05507203":
            return None,{"status":"FETCH_BLOCKED","sourceUrl":"https://clinicaltrials.gov/api/v2/studies/"+nct,"errorClass":"TimeoutError"}
        return fetched(nct,False)
    x=collect(ROSTER,APPS,fetcher=mock)
    assert x["registryRecordsFetched"]==28
    assert x["registryResultsMembershipUnknown"]==1
    bad=next(r for r in x["trials"] if r["nct"]=="NCT05507203")
    assert bad["resultsPresent"] is None
    assert bad["primaryOutcomeCount"] is None
    assert bad["independentReviewerSignoff"] is False
def test_original_source_drift_and_application_cycle_tamper_refused():
    for mutate in [
      lambda r,a:r["records"].pop(),
      lambda r,a:r["records"].append(deepcopy(r["records"][0])),
      lambda r,a:r["records"][0].update(nct="NCT00000000"),
      lambda r,a:a["records"][0].update(nct="NCT00000000"),
      lambda r,a:a["records"][0]["candidateApplications"][0].update(cycleId="changed"),
      lambda r,a:a.update(clinicalSignoff=True)
    ]:
        r,a=deepcopy(ROSTER),deepcopy(APPS)
        mutate(r,a)
        with pytest.raises(ValueError):strict_roster(r,a)
def test_no_claimed_automatic_benefit_or_adverse_effect_recalculation():
    assert _text("0.003")=="0.003"
    assert _text(None) is None
    s=(ROOT/"scripts/extract_focus_registry_outcomes_r42.py").read_text()
    assert "MAIN_FOCUS_R42_POSTED_REGISTRY_RESULTS_RESEARCH" in s
    assert "noClinicalOrProductionWrites" in s
    assert "pValue" in s
    assert "hazardRatioCalculated" not in s
