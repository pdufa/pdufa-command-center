"""Review work priority cannot leak into synthetic medical grades or FDA forecasts."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import medical_primary_evidence_queue as queue
from app import medical_continuous as core


POSTED = frozenset((
    "NCT05507203","NCT05507216","NCT04576949","NCT05206370",
    "NCT05811247","NCT05813275","NCT03697109","NCT04308590",
    "NCT05767346","NCT04544293","NCT06331299","NCT04716231",
))
AMBIGUOUS="NCT04871282"


@pytest.fixture
def stub(monkeypatch):
    canonical=sorted(core.roster())
    assert len(canonical)==29
    from app import medical_registry_reconciliation as registry
    from app import medical_scientific_triage as triage
    from app import medical_assessment_ledger as ledger
    monkeypatch.setattr(registry,"coverage",lambda engine:{
        "savedNcts":29,"status":"COMPLETE_REGISTRY_FACT_CAPTURE"})
    monkeypatch.setattr(triage,"coverage",lambda engine:{
        "savedNcts":29,"status":"COMPLETE_SOURCE_TRIAGE"})
    monkeypatch.setattr(ledger,"coverage",lambda engine:{
        "sourceComplete":29,"reviewEvents":0,"phaseVerifiedNcts":0})
    def registry_latest(engine,nct):
        return {
            "nct":nct,"sourceRunId":"saved-source-"+nct,
            "currentRegistryPhases":["PHASE2","PHASE3"] if nct==AMBIGUOUS else ["PHASE3"],
            "phaseAgreement":"MULTIPHASE_REVIEW_REQUIRED" if nct==AMBIGUOUS else "MATCHED_SINGLE_PHASE",
            "registryPostedPrimaryOutcomeMeasures":1 if nct in POSTED else 0,
            "registeredPrimaryOutcomeCount":1,
            "registryUrl":"https://clinicaltrials.gov/study/"+nct,
            "latestRecordUpdatePosted":"2026-09-22",
            "resultsInterpretation":"SPONSOR_REPORTED_NOT_ADJUDICATED" if nct in POSTED else "NO_POSTED_RESULTS_IN_RECORD",
            "snapshotId":"registry-"+nct,
            "scientificSignoff":False,
        }
    def triage_latest(engine,nct):
        return {"nct":nct,"sourceRunId":"saved-source-"+nct,
                "snapshotId":"triage-"+nct,"methodPositions":800,
                "sourceClassCounts":{"SOURCE_RECORD_UNADJUDICATED":0,
                                     "RESEARCH_LEADS_ONLY":800},
                "scientificSignoff":False}
    monkeypatch.setattr(registry,"latest",registry_latest)
    monkeypatch.setattr(triage,"latest",triage_latest)
    monkeypatch.setattr(ledger,"trial_history",lambda engine,nct:{"reviewEvents":[]})
    return canonical


def test_work_queue_separates_12_posted_16_missing_one_phase_conflict(stub):
    result=queue.build_queue(object())
    assert result["canonicalTrials"]==29
    assert len(result["reviewItems"])==29
    assert result["phaseReconciliationRequired"]==1
    assert result["postedPrimaryResultsNeedReview"]==12
    assert result["noPostedPrimaryResults"]==16
    assert result["postedPrimaryOutcomeMeasures"]==12
    assert result["reviewItems"][0]["nct"]==AMBIGUOUS
    assert result["reviewItems"][0]["reviewPriority"]==1
    assert [x["reviewQueuePosition"] for x in result["reviewItems"]]==list(range(1,30))
    assert all(x["methodPositions"]==800 for x in result["reviewItems"])
    assert all(x["scientificGradeStatus"]=="NOT_REVIEWED" for x in result["reviewItems"])
    assert all(x["clinicalFinding"] is None for x in result["reviewItems"])
    assert result["clinicalSignoff"] is False
    assert result["certainty"]=="NOT_VALIDATED"
    assert all(v=="ABSTAIN" for v in result["fdaPredictions"].values())


def test_queue_flags_review_work_not_predicted_medical_risk(stub):
    result=queue.build_queue(object())
    assert all("nextEvidenceAction" in x and "sourceRunId" in x and
               x["officialRegistryUrl"].endswith(x["nct"])
               for x in result["reviewItems"])
    assert all(x["reviewPriority"]==2 for x in result["reviewItems"][1:13])
    assert all(x["reviewPriority"]==3 for x in result["reviewItems"][13:])
    assert all(x["fdaPrediction"]=="ABSTAIN" for x in result["reviewItems"])


def test_queue_fails_closed_on_partial_registry_coverage(stub,monkeypatch):
    from app import medical_registry_reconciliation as registry
    monkeypatch.setattr(registry,"coverage",lambda engine:{
        "savedNcts":28,"status":"IN_PROGRESS"})
    status=queue.readiness(object())
    assert status["status"]=="INCOMPLETE"
    with pytest.raises(RuntimeError,match="29-trial"):
        queue.build_queue(object())


def test_queue_rejects_wrong_trial_identity_and_source_links(stub,monkeypatch):
    from app import medical_scientific_triage as triage
    old=triage.latest
    def mismatched(engine,nct):
        data=old(engine,nct)
        if nct=="NCT05507203":
            return {**data,"sourceRunId":"wrong-source-run"}
        return data
    monkeypatch.setattr(triage,"latest",mismatched)
    with pytest.raises(RuntimeError,match="Mismatched"):
        queue.build_queue(object())


def test_review_events_come_from_live_append_only_ledger_not_old_triage(stub,monkeypatch):
    from app import medical_assessment_ledger as ledger
    monkeypatch.setattr(ledger,"trial_history",
        lambda engine,nct:{"reviewEvents":[{"grade":3}]} if nct=="NCT05507203" else {"reviewEvents":[]})
    rows=queue.build_queue(object())["reviewItems"]
    item=next(x for x in rows if x["nct"]=="NCT05507203")
    assert item["scientificReviewEventCount"]==1
    assert item["scientificGradeStatus"]=="REVIEW_EVENTS_EXIST_RECONCILE_LATEST_PHASE"
    assert item["clinicalFinding"] is None


def test_coverage_routes_are_read_only(stub):
    app=FastAPI()
    queue.install_routes(app,lambda:object(),lambda:None,lambda:None)
    client=TestClient(app)
    assert client.get("/api/internal/medical-primary-evidence-review/readiness").json()["status"]=="READY_FOR_EVIDENCE_REVIEW"
    result=client.get("/api/internal/medical-primary-evidence-review/queue")
    assert result.status_code==200 and len(result.json()["reviewItems"])==29
    assert client.post("/api/internal/medical-primary-evidence-review/queue").status_code==405
