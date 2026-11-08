"""Exact 800-source-method audit worker: durable progress, idempotency, fail-closed."""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app import medical_method_audit_worker as audit
from app import medical_scientific_triage as triage


@pytest.fixture
def db(tmp_path, monkeypatch):
    engine=create_engine("sqlite:///"+str(tmp_path/"source-audit.sqlite"),
                         connect_args={"check_same_thread":False})
    engine.dialect.name="sqlite"
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE medical_scientific_triage_snapshots (
            snapshot_id TEXT PRIMARY KEY,nct_id TEXT NOT NULL,output_json TEXT NOT NULL)"""))
    audit.initialize(engine,test_only=True)
    source={
        "nct":audit.NCT,"methodPositions":800,"assessmentCount":40,
        "sourceInputSha256":"a"*64,"catalogSha256":"b"*64,
        "scientificSignoff":False,
        "fdaPredictions":{"APPROVAL":"ABSTAIN","CRL":"ABSTAIN","REVIEW_DELAY":"ABSTAIN"},
        "assessments":[{
           "assessmentId":f"{ai//5+1}.{ai%5+1}",
           "methods":[{"methodIndex":mi,
             "sourceClassification":"RESEARCH_LEADS_ONLY",
             "sourceCount":1,
             "sourceLeads":[{"source":"https://clinicaltrials.gov/study/"+audit.NCT}]}
             for mi in range(1,21)]}
           for ai in range(40)]
    }
    sid=str(uuid.uuid4())
    with engine.begin() as c:
        c.execute(text("""INSERT INTO medical_scientific_triage_snapshots
            (snapshot_id,nct_id,output_json) VALUES(:id,:nct,:output)"""),
            {"id":sid,"nct":audit.NCT,"output":json.dumps(source)})
    monkeypatch.setattr(triage,"latest",lambda engine,nct:{"snapshotId":sid,**source})
    yield engine,source,sid
    engine.dispose()


def test_real_800_method_source_classifications_are_audited_once_without_grades(db):
    engine,packet,sid=db
    started=audit.start(engine,audit.NCT,submit=False)
    assert started["status"]=="PENDING"
    assert started["completedPositions"]==0
    assert started["sourceSnapshotId"]==sid
    audit.run(engine,started["runId"])
    complete=audit.snapshot(engine,audit.NCT)
    assert complete["status"]=="COMPLETE"
    assert complete["completedPositions"]==800
    assert complete["completedAssessmentGroups"]==40
    assert complete["currentMethodIndex"] is None
    assert complete["gradeEventsWritten"]==0
    assert complete["scientificReviewEventsWritten"]==0
    assert complete["prediction"]=={"APPROVAL":"ABSTAIN","CRL":"ABSTAIN","REVIEW_DELAY":"ABSTAIN"}
    assert complete["accuracy"]=="NOT_CALIBRATED"
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_pilot_method_audit_events")).scalar_one()==800
        assert c.execute(text("SELECT COUNT(DISTINCT assessment_index) FROM medical_pilot_method_audit_events")).scalar_one()==40
        assert c.execute(text("SELECT COUNT(*) FROM medical_pilot_method_audit_runs")).scalar_one()==1
        tables={x[0] for x in c.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).all()}
    assert "medical_assessment_review_events" not in tables
    assert "medical_assessment_phase_events" not in tables
    assert audit.start(engine,audit.NCT,submit=False)["runId"]==started["runId"]
    audit.run(engine,started["runId"])
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_pilot_method_audit_events")).scalar_one()==800


def test_partial_400_events_resumes_exactly_with_no_duplicate_methods(db):
    engine,packet,sid=db
    started=audit.start(engine,audit.NCT,submit=False)
    # Simulate a restart after genuine persisted first-half observation receipts.
    with engine.begin() as c:
        for i in range(1,401):
            c.execute(text("""INSERT INTO medical_pilot_method_audit_events
                (run_id,position_index,assessment_index,method_index,source_class,
                source_count,observed_at) VALUES(:run,:position,:a,:m,'RESEARCH_LEADS_ONLY',1,:date)"""),
                {"run":started["runId"],"position":i,
                 "a":(i-1)//20+1,"m":(i-1)%20+1,"date":audit.stamp()})
        c.execute(text("UPDATE medical_pilot_method_audit_runs SET processed_methods=400,status='RUNNING'"))
    audit.run(engine,started["runId"])
    report=audit.snapshot(engine,audit.NCT)
    assert report["completedPositions"]==800
    assert report["status"]=="COMPLETE"
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_pilot_method_audit_events")).scalar_one()==800


def test_wrong_trial_rejected_and_missing_positions_not_written(db,monkeypatch):
    engine,packet,sid=db
    with pytest.raises(ValueError,match="restricted"):
        audit.start(engine,"NCT99999999",submit=False)
    packet["assessments"][3]["methods"].pop()
    with pytest.raises(ValueError,match="20 method"):
        audit.start(engine,audit.NCT,submit=False)
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_pilot_method_audit_runs")).scalar_one()==0


def test_changed_input_digest_fails_without_any_grade_or_complete_claim(db):
    engine,packet,sid=db
    snap=audit.start(engine,audit.NCT,submit=False)
    with engine.begin() as c:
        c.execute(text("""UPDATE medical_scientific_triage_snapshots SET output_json=:json
            WHERE snapshot_id=:sid"""),{"json":json.dumps({**packet,"sourceInputSha256":"0"*64}),"sid":sid})
    audit.run(engine,snap["runId"])
    failed=audit.snapshot(engine,audit.NCT)
    assert failed["status"]=="FAILED"
    assert failed["completedPositions"]==0
    assert failed["failureKind"]=="ValueError"
    assert failed["prediction"]["APPROVAL"]=="ABSTAIN"


def test_preview_only_endpoints_have_read_and_operational_write_gates(db):
    engine,packet,sid=db
    app=FastAPI()
    def read_auth():
        raise HTTPException(401,"Read key required")
    def operational_auth():
        raise HTTPException(401,"Operator key required")
    audit.install_routes(app,lambda:engine,read_auth,operational_auth,lambda:None)
    with TestClient(app) as client:
        assert client.get("/api/internal/medical-method-audit/"+audit.NCT+"/latest").status_code==401
        assert client.post("/api/internal/medical-method-audit/"+audit.NCT+"/runs").status_code==401
    app2=FastAPI()
    audit.install_routes(app2,lambda:engine,lambda:None,lambda:None,lambda:None)
    with TestClient(app2) as client:
        assert client.get("/api/internal/medical-method-audit/"+audit.NCT+"/latest").status_code==404
        assert client.post("/api/internal/medical-method-audit/NCT99999999/runs").status_code==422
        response=client.post("/api/internal/medical-method-audit/"+audit.NCT+"/runs")
        assert response.status_code==200
        assert response.json()["auditKind"]=="SAVED_TRIAGE_SOURCE_CLASSIFICATION_VERIFICATION"
