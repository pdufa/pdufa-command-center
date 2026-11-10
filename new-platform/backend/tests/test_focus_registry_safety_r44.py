"""Synthetic R44 safety source integrity tests: not FDA evidence grades."""
from __future__ import annotations
from copy import deepcopy
import hashlib,json
import pytest
from scripts.build_focus_registry_safety_r44 import extract,run

def study(n,*,has_results=True,has_ae=True):
    d={"protocolSection":{"identificationModule":{"nctId":n},"statusModule":{
       "resultsFirstPostDateStruct":{"date":"2026-09-09"}}}}
    if has_results:
        d["resultsSection"]={}
        if has_ae:d["resultsSection"]["adverseEventsModule"]={
          "timeFrame":"Up to 52 weeks","frequencyThreshold":"5",
          "eventGroups":[
             {"id":"E1","title":"Drug","seriousNumAffected":7,"seriousNumAtRisk":100,
              "deathsNumAffected":1,"deathsNumAtRisk":100},
             {"id":"E2","title":"Placebo","seriousNumAffected":4,"seriousNumAtRisk":90,
              "deathsNumAffected":0,"deathsNumAtRisk":90}],
          "seriousEvents":[{"term":"Pneumonia","organSystem":"Infections",
              "stats":[{"groupId":"E1","numAffected":3,"numAtRisk":100},
                       {"groupId":"E2","numAffected":1,"numAtRisk":90}]}],
          "otherEvents":[{"term":"Nausea","organSystem":"Gastrointestinal disorders",
              "stats":[{"groupId":"E1","numAffected":8,"numAtRisk":100},
                       {"groupId":"E2","numAffected":6,"numAtRisk":90}]}]}
    return d

def manifest():
    ncts=[f"NCT{i:08d}" for i in range(1,30)]
    return {"asOf":"2026-11-09","trialCount":29,"applicationCount":23,
       "trialRows":[{"nct":n,"registryUrl":"https://clinicaltrials.gov/api/v2/studies/"+n+"?format=json"} for n in ncts],
       "applicationGroups":[{"cycleId":f"group-{i}","ncts":([ncts[i]]+[ncts[i+23]] if i<6 else [ncts[i]])}
                            for i in range(23)]}

def fetch(url):
    n=url.split("?")[0].rsplit("/",1)[-1]
    body=json.dumps(study(n,has_results=int(n[-8:])<=12)).encode()
    return {"status":"FETCHED","url":url,"sha256":hashlib.sha256(body).hexdigest(),"bytes":len(body)},body

def test_safety_arms_preserved_source_values_uninterpreted():
    r=extract(study("NCT00000001"),"NCT00000001",{"sha256":"a"*64},["group-1"])
    assert r["eventGroupCount"]==2 and r["seriousEventTermCount"]==1
    assert r["eventGroups"][0]["seriousNumAffectedAsReported"]=="7"
    assert r["eventGroups"][1]["deathsNumAtRiskAsReported"]=="90"
    assert r["seriousEventTerms"][0]["stats"][0]["numAtRiskAsReported"]=="100"
    assert r["frequencyThresholdAsReported"]=="5"
    assert r["independentlyAdjudicatedSafety"] is False
    assert r["authorizedScientificGrade"] is None
    assert r["officialFdaApprovalCrlPrediction"]=="ABSTAIN"

def test_results_section_without_ae_is_not_inferred_safety_failure():
    a=extract(study("NCT00000001",has_results=False),"NCT00000001",{},["group-1"])
    b=extract(study("NCT00000001",has_results=True,has_ae=False),"NCT00000001",{},["group-1"])
    assert a["extractStatus"]=="NO_CURRENT_REGISTRY_RESULTS_SECTION"
    assert b["extractStatus"]=="RESULTS_SECTION_NO_ADVERSE_EVENT_MODULE"
    assert a["officialFdaApprovalCrlPrediction"]=="ABSTAIN"

def test_exact_29_application_crosswalk_raw_hash_preserved(tmp_path):
    r=run(manifest(),fetch,tmp_path)
    assert r["nctCount"]==29 and r["provisionalApplicationCount"]==23
    assert r["trialsWithPostedAeModule"]==12
    assert r["seriousEventTermRows"]==12 and r["otherEventTermRows"]==12
    assert r["eventGroupRows"]==24
    assert r["independentClinicalGrades"]==0 and r["validatedApplicationPredictions"]==0
    assert r["realHistoricalBacktests"]==0 and r["numericalFdaProbability"] is None
    assert r["productionOrScientificLedgerWrites"] is False
    assert len(list(tmp_path.glob("NCT*.json")))==29
    for item in r["records"]:
        original=(tmp_path/(item["nct"]+".json")).read_bytes()
        assert hashlib.sha256(original).hexdigest()==item["sourceResponseSha256"]

def test_invalid_safety_group_mismatch_and_registry_identity_fail_closed(tmp_path):
    d=study("NCT00000001")
    d["resultsSection"]["adverseEventsModule"]["seriousEvents"][0]["stats"][0]["groupId"]="E9"
    with pytest.raises(ValueError,match="EVENT_GROUP_MISMATCH"):
        extract(d,"NCT00000001",{},["group-1"])
    with pytest.raises(ValueError,match="IDENTITY_MISMATCH"):
        extract(study("NCT00000001"),"NCT00000002",{},["group-1"])
    def wrong(url):
        receipt,body=fetch(url)
        receipt["sha256"]="0"*64
        return receipt,body
    with pytest.raises(ValueError,match="SOURCE_BYTES_SHA256_MISMATCH"):
        run(manifest(),wrong,tmp_path)

def test_no_averaging_across_crossover_groups_or_missing_source_invention(tmp_path):
    d=study("NCT00000001")
    d["resultsSection"]["adverseEventsModule"]["eventGroups"].append(
        {"id":"E3","title":"Crossover drug","seriousNumAffected":3,"seriousNumAtRisk":40})
    r=extract(d,"NCT00000001",{},["group-1"])
    assert r["eventGroupCount"]==3
    assert "pooledRisk" not in r
    assert r["eventGroups"][2]["seriousNumAtRiskAsReported"]=="40"
    def missing(url):
        return {"status":"HTTP_UNAVAILABLE","url":url},None
    summary=run(manifest(),missing)
    assert summary["registryFetched"]==0 and summary["trialsWithPostedAeModule"]==0
    assert summary["validatedApplicationPredictions"]==0
