"""MAIN R45 synthetic anti-overclaim tests for current registry text concordance."""
from __future__ import annotations
import hashlib,json
from copy import deepcopy
import pytest
from scripts.build_focus_registry_endpoint_concordance_r45 import registered_and_posted,run

def study(n,posted=True):
    d={"protocolSection":{
      "identificationModule":{"nctId":n},
      "outcomesModule":{"primaryOutcomes":[
          {"measure":"Change from baseline A","timeFrame":"Week 24"},
          {"measure":"Change from baseline B","timeFrame":"Week 36"}]},
      "statusModule":{"lastUpdatePostDateStruct":{"date":"2026-11-05"}}}}
    if posted:
        d["resultsSection"]={"outcomeMeasuresModule":{"outcomeMeasures":[
          {"type":"PRIMARY","title":"Change from baseline A","timeFrame":"Week 24"},
          {"type":"PRIMARY","title":"Change from baseline B","timeFrame":"Week 36"},
          {"type":"SECONDARY","title":"Some secondary","timeFrame":"Week 30"}]}}
    return d

def manifest():
    ids=[f"NCT{i:08d}" for i in range(1,30)]
    return {"asOf":"2026-11-09","trialCount":29,"applicationCount":23,
        "trialRows":[{"nct":n,"registryUrl":"https://clinicaltrials.gov/api/v2/studies/"+n+"?format=json"} for n in ids],
        "applicationGroups":[{"cycleId":f"group-{i}","ncts":[ids[i]]+([ids[23+i]] if i<6 else [])}
                             for i in range(23)]}

def fetch(url):
    n=url.split("?")[0].rsplit("/",1)[-1]
    raw=json.dumps(study(n,posted=int(n[-8:])<=12)).encode()
    return {"status":"FETCHED","url":url,"sha256":hashlib.sha256(raw).hexdigest()},raw

def test_exact_current_text_comparison_is_not_locked_sap_signoff():
    p=registered_and_posted(study("NCT00000001"),"NCT00000001",{},["a"])
    assert p["exactCurrentTitleAndTimeFrameCount"]==2
    assert p["registeredPrimaryCountInCurrentVersion"]==2
    assert p["postedPrimaryCountInCurrentVersion"]==2
    assert p["lockedSapVerified"] is False
    assert p["preReadoutRegistryVersionVerified"] is False
    assert p["originalMultiplicityHierarchyVerified"] is False
    assert p["scientificMethodGrade"] is None
    assert p["officialFdaForecast"]=="ABSTAIN"

def test_changed_timeframe_is_discrepancy_not_prespec_proof():
    d=study("NCT00000001")
    d["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]["timeFrame"]="Week 12"
    x=registered_and_posted(d,"NCT00000001",{},["a"])
    assert x["titleOnlyTimeFrameDifferenceCount"]==1
    assert x["exactCurrentTitleAndTimeFrameCount"]==1
    assert x["postedPrimaryTextComparisons"][0]["currentRecordTextComparison"]=="TITLE_ONLY_TIME_FRAME_DIFFERENCE"
    assert x["sourceSnapshotStatus"]=="CURRENT_SNAPSHOT_TEXT_DISCREPANCY_REQUIRES_REVIEW"

def test_duplicate_posted_rows_cannot_reuse_one_registered_endpoint():
    d=study("NCT00000001")
    o=d["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"]
    o.append(deepcopy(o[0]))
    x=registered_and_posted(d,"NCT00000001",{},["a"])
    assert x["postedPrimaryCountInCurrentVersion"]==3
    assert x["exactCurrentTitleAndTimeFrameCount"]==2
    assert x["unmatchedPostedPrimaryCount"]==1
    assert x["sourceSnapshotStatus"]=="CURRENT_SNAPSHOT_TEXT_DISCREPANCY_REQUIRES_REVIEW"

def test_absent_posted_table_is_not_negative_trial_or_fda_outcome():
    x=registered_and_posted(study("NCT00000001",False),"NCT00000001",{},["a"])
    assert x["sourceSnapshotStatus"]=="NO_POSTED_PRIMARY_IN_CURRENT_REGISTRY"
    assert x["registeredPrimaryCountInCurrentVersion"]==2
    assert x["postedPrimaryCountInCurrentVersion"]==0
    assert x["officialFdaForecast"]=="ABSTAIN"

def test_exact_29_roster_and_23_application_census_is_source_only(tmp_path):
    r=run(manifest(),fetch,tmp_path)
    assert (r["nctCount"],r["applicationCount"],r["sourceFetched"],r["trialsWithResults"])==(29,23,29,12)
    assert (r["currentRegisteredPrimaryCount"],r["postedPrimaryCount"],r["currentExactTitleTimeFrameCount"])==(58,24,24)
    assert r["scientificGrades"]==0 and r["qualifiedClinicalSignoffs"]==0
    assert r["independentlyValidatedFdaForecasts"]==0
    assert r["historicalIndependentBacktests"]==0
    assert r["officialFutureOutcome"]=="ABSTAIN"
    assert r["modelTrainingAuthorized"] is False
    for x in r["records"]:
        raw=(tmp_path/(x["nct"]+".json")).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==x["sourceResponseSha256"]

def test_identity_and_hash_tamper_fail_closed(tmp_path):
    with pytest.raises(ValueError,match="IDENTITY_MISMATCH"):
        registered_and_posted(study("NCT00000001"),"NCT00000002",{},["a"])
    def bad(url):
        r,b=fetch(url);r["sha256"]="f"*64;return r,b
    with pytest.raises(ValueError,match="SOURCE_BYTES_SHA256_MISMATCH"):
        run(manifest(),bad,tmp_path)

def test_missing_source_never_becomes_posted_or_pass_grade():
    def missing(url):return {"status":"HTTP_UNAVAILABLE","url":url},None
    r=run(manifest(),missing)
    assert r["sourceFetched"]==0
    assert r["currentExactTitleTimeFrameCount"]==0
    assert r["scientificGrades"]==0 and r["officialFutureOutcome"]=="ABSTAIN"
