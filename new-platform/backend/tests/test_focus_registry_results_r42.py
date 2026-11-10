"""Synthetic R42 exact-NCT published results test; never a real FDA prediction."""
from __future__ import annotations
import hashlib,json
from copy import deepcopy
import pytest
from scripts.build_focus_registry_results_r42 import extract,run

def study(nct,with_results=True,with_primary=True):
    doc={"protocolSection":{"identificationModule":{"nctId":nct},
        "statusModule":{"resultsFirstPostDateStruct":{"date":"2026-09-01"}},
        "outcomesModule":{"primaryOutcomes":[{"measure":"Synthetic outcome"}]}}}
    if with_results:
        results=[]
        if with_primary:results=[{"type":"PRIMARY","title":"Synthetic outcome",
            "timeFrame":"Week 36","unitOfMeasure":"points","paramType":"MEAN",
            "groups":[{"id":"G1","title":"Active"},{"id":"G2","title":"Control"}],
            "denoms":[{"groupId":"G1","value":"100"},{"groupId":"G2","value":"100"}],
            "classes":[{"title":"Overall","categories":[{"title":"Total","measurements":[
                {"groupId":"G1","value":"14.5","spread":"3.2"},
                {"groupId":"G2","value":"7.5","spread":"4.5"}]}]}],
            "analyses":[{"groupIds":["G1","G2"],"pValue":"0.0123",
                          "ciPctValue":95,"ciLowerLimit":"1.0","ciUpperLimit":"8.0"}]}]
        else:results=[{"type":"SECONDARY","title":"Synthetic secondary"}]
        doc["resultsSection"]={"outcomeMeasuresModule":{"outcomeMeasures":results}}
    return doc

def manifest():
    return {"trialCount":29,"applicationCount":23,"asOf":"2026-11-09",
       "trialRows":[{"nct":f"NCT{i:08d}",
       "registryUrl":f"https://clinicaltrials.gov/api/v2/studies/NCT{i:08d}?format=json"}
       for i in range(1,30)]}

def getter(url):
    nct=url.split("?")[0].rsplit("/",1)[-1]
    contents=json.dumps(study(nct,int(nct[-8:])<=12)).encode()
    return {"url":url,"status":"FETCHED","sha256":hashlib.sha256(contents).hexdigest(),
            "bytes":len(contents)},contents

def test_exact_primary_measurements_and_p_value_reported_not_interpreted():
    d=study("NCT00000001")
    o=extract(d,"NCT00000001",{"url":"https://clinicaltrials.gov/api/v2/studies/NCT00000001",
       "sha256":"a"*64,"bytes":234})
    assert o["postedPrimaryOutcomeTableCount"]==1
    assert o["primaryOutcomeTables"][0]["measurements"][0]["valueAsPublished"]=="14.5"
    assert o["primaryOutcomeTables"][0]["statisticalAnalyses"][0]["pValueAsPublished"]=="0.0123"
    assert o["primaryOutcomeTables"][0]["statisticalAnalyses"][0]["ciPercentAsPublished"]=="95"
    assert o["clinicalReviewerSignoff"] is False and o["clinicalMethodGrade"] is None
    assert o["officialFdaForecast"]=="ABSTAIN"

def test_missing_results_or_primary_table_does_not_imply_failed_phase3():
    a=extract(study("NCT00000001",False),"NCT00000001",{})
    b=extract(study("NCT00000002",True,False),"NCT00000002",{})
    assert a["extractStatus"]=="NO_CURRENT_REGISTRY_RESULTS_SECTION"
    assert b["extractStatus"]=="RESULTS_SECTION_WITHOUT_POSTED_PRIMARY_TABLE"
    assert a["clinicalMethodGrade"] is None
    assert b["officialFdaForecast"]=="ABSTAIN"

def test_29_source_receipts_preserve_full_raw_json_with_exact_sha(tmp_path):
    r=run(manifest(),getter,tmp_path)
    assert r["nctCount"]==29 and r["applicationGroupCount"]==23
    assert r["registryFetched"]==29 and r["registryWithResultsSection"]==12
    assert r["registryWithPrimaryTables"]==12 and r["postedPrimaryOutcomeTableCount"]==12
    assert len(list(tmp_path.glob("NCT*.json")))==29
    for row in r["records"]:
        raw=(tmp_path/(row["nct"]+".json")).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==row["sourceResponseSha256"]
        assert row["clinicalMethodGrade"] is None
        assert row["officialFdaForecast"]=="ABSTAIN"
    assert r["independentClinicalGrades"]==0
    assert r["validatedApplicationPredictions"]==0
    assert r["realHistoricalBacktests"]==0
    assert r["calibratedAccuracy"] is None
    assert r["trainedFdaModelAuthorized"] is False

def test_mismatched_nct_or_modified_digest_cannot_be_accepted(tmp_path):
    with pytest.raises(ValueError,match="IDENTITY_MISMATCH"):
        extract(study("NCT00000001"),"NCT00000002",{})
    def wrong(url):
        r,b=getter(url);r["sha256"]="0"*64;return r,b
    with pytest.raises(ValueError,match="SOURCE_BYTES_SHA256_MISMATCH"):
        run(manifest(),wrong,tmp_path)

def test_invalid_json_never_yields_clinical_grade_or_prediction(tmp_path):
    def bad(url):
        b=b"abc";return {"url":url,"status":"FETCHED",
           "sha256":hashlib.sha256(b).hexdigest(),"bytes":3},b
    r=run(manifest(),bad,tmp_path)
    assert r["registryFetched"]==0
    assert all(x["extractStatus"]=="INVALID_OR_MISMATCHED_ORIGINAL" for x in r["records"])
    assert r["futureFdaApprovalCrlForecast"]=="ABSTAIN"
    assert r["validatedApplicationPredictions"]==0
