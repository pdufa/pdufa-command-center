"""R52: current API alone does not establish original version; narrow internal-source probe."""
import hashlib,json
from pathlib import Path
import pytest
from scripts.probe_original_ctgov_history_r52 import (
    NCTS,HOST,CURRENT,history_changes,meta,run
)

def test_history_index_preserves_public_dates_and_zero_based_versions():
    raw=json.dumps({"history":{"changes":[{"version":4,"date":"2024-01-03"},
                        {"version":0,"date":"2021-05-05"},
                        {"version":2,"date":"2023-01-01"}]}}).encode()
    assert [x["version"] for x in history_changes(raw)]==[0,2,4]
    assert history_changes(raw)[0]["registryHistoryDateAsReported"]=="2021-05-05"

def test_study_version_identity_and_original_primary_endpoint_text():
    nct=NCTS[0]
    original={"studyVersion":0,"study":{"protocolSection":{
        "identificationModule":{"nctId":nct},
        "outcomesModule":{"primaryOutcomes":[{"measure":"DLCO Week 24",
            "timeFrame":"24 Weeks","description":"Initial registered wording"}]}}}}
    assert meta(json.dumps(original).encode(),nct,0)==[{
       "measure":"DLCO Week 24","timeFrame":"24 Weeks",
       "description":"Initial registered wording"}]
    with pytest.raises(ValueError,match="HISTORICAL_REGISTRY_VERSION_OR_BODY_MISMATCH"):
        meta(json.dumps(original).encode(),nct,1)
    with pytest.raises(ValueError,match="ORIGINAL_HISTORICAL_NCT_IDENTITY_MISMATCH"):
        meta(json.dumps(original).encode(),NCTS[1],0)

def make_fetcher(change_first=True,missing=None):
    def get(url):
        nct=next((n for n in NCTS if n in url),None)
        assert nct is not None
        if missing==nct and "?history=true" in url:
            return {"url":url,"status":"HTTP_UNAVAILABLE"},None
        if "?history=true" in url:
            data={"history":{"changes":[
                 {"version":0,"date":"2020-01-01"},
                 {"version":1,"date":"2022-01-15"}]}}
        elif "/history/0" in url:
            data={"studyVersion":0,"study":{"protocolSection":{
               "identificationModule":{"nctId":nct},
               "outcomesModule":{"primaryOutcomes":[{"measure":"Original primary",
                    "timeFrame":"Week 24","description":"Early public record"}]}}}}
        elif "?format=json" in url:
            data={"protocolSection":{
               "identificationModule":{"nctId":nct},
               "outcomesModule":{"primaryOutcomes":[{"measure":
                    "Updated primary" if change_first else "Original primary",
                    "timeFrame":"Week 24","description":
                    "Updated public record" if change_first else "Early public record"}]}}}
        else:raise AssertionError("unexpected source endpoint "+url)
        raw=json.dumps(data).encode()
        return {"url":url,"status":"FETCHED","sha256":hashlib.sha256(raw).hexdigest(),
                "bytes":len(raw),"contentType":"application/json"},raw
    return get

def test_three_exact_original_trials_archived_and_compared_without_clinical_prediction(tmp_path):
    r=run(make_fetcher(),tmp_path)
    assert (r["canonicalNctRosterCount"],r["applicationCycleCount"])==(29,23)
    assert r["priorityTrialCount"]==3
    assert r["historyIndexesRetrieved"]==3
    assert r["originalFirstVersionTextRecovered"]==3
    assert r["oldAndCurrentOutcomesCompared"]==3
    assert all(x["firstVsCurrentPrimaryWordingExactMatch"] is False for x in r["priorityTrials"])
    assert all(x["firstVersionInfo"]["registryVersionAsReported"]==0 for x in r["priorityTrials"])
    assert len(list(tmp_path.iterdir()))==9
    for rec in r["priorityTrials"]:
        for kind in ("historyIndex","firstVersionInfo","currentVersionInfo"):
            item=rec[kind]
            raw=(tmp_path/item["archiveFile"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==item["sourceSha256"]
    assert r["originalLockedStatisticalAnalysisPlansVerified"]==0
    assert r["applicationFdaOutcomePredictionsValidated"]==0
    assert r["calibratedAccuracy"] is None
    assert r["productionOrClinicalLedgerWrites"] is False
    assert r["officialFdaForecast"]=="ABSTAIN"

def test_unavailable_history_is_not_approvability_or_source_absence(tmp_path):
    r=run(make_fetcher(missing=NCTS[0]),tmp_path)
    assert r["historyIndexesRetrieved"]==2
    assert r["originalFirstVersionTextRecovered"]==2
    a=r["priorityTrials"][0]
    assert a["historyIndex"]["status"]=="HTTP_UNAVAILABLE"
    assert a["firstVersionPrimaryOutcomes"] is None
    assert a["qualifiedHistoricalFDAForecastInput"] is False
    assert a["officialFdaForecast"]=="ABSTAIN"

def test_alternate_official_host_restores_original_history_without_bypassing_source_identity(tmp_path):
    def first_host_blocked(url):
        if "www.clinicaltrials.gov/api/int/" in url:
            return {"url":url,"status":"HTTP_UNAVAILABLE","httpStatus":404},None
        return make_fetcher()(url)
    report=run(first_host_blocked,tmp_path)
    assert report["historyIndexesRetrieved"]==3
    assert report["originalFirstVersionTextRecovered"]==3
    for row in report["priorityTrials"]:
        assert row["historySourceAttempts"][0]["httpStatus"]==404
        assert row["historySourceAttempts"][1]["status"]=="FETCHED"
        assert row["firstVersionSourceAttempts"][0]["status"]=="HTTP_UNAVAILABLE"
        assert row["firstVersionInfo"]["status"]=="FETCHED"
        assert row["preUnblindingLockedSapVerified"] is False
    assert report["modelTrainingAuthorized"] is False

def test_same_outcome_text_still_not_locked_sap_proof(tmp_path):
    r=run(make_fetcher(change_first=False),tmp_path)
    assert all(x["firstVsCurrentPrimaryWordingExactMatch"] is True for x in r["priorityTrials"])
    assert all(x["preUnblindingLockedSapVerified"] is False for x in r["priorityTrials"])
    assert r["originalPreReadoutEndpointHierarchyVerified"]==0

@pytest.mark.parametrize("bad",[
 {"history":{"changes":[{"version":0,"date":"2021-01-01"},{"version":0,"date":"2022-01-01"}]}},
 {"history":{"changes":[{"version":-1,"date":"2021-01-01"}]}},
 {"history":{"changes":[{"version":0,"date":"2021-99-99"}]}},
 {"history":{"changes":[{"version":"0","date":"2021-01-01"}]}},
 {"history":{"changes":[]}},
 {"changes":[{"version":0,"date":"2020-01-01"}]}
])
def test_undocumented_endpoint_structure_drift_not_misclassified(bad):
    with pytest.raises(ValueError):
        history_changes(json.dumps(bad).encode())

def test_source_hash_forgery_fails_closed(tmp_path):
    def altered(url):
        rec,body=make_fetcher()(url)
        return {**rec,"sha256":"0"*64},body
    with pytest.raises(ValueError,match="REGISTRY_HISTORY_ORIGINAL_BYTES_SHA_INVALID"):
        run(altered,tmp_path)
