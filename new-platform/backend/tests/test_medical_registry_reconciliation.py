"""Exact-NCT official registry freshness and primary-source verification tests."""
import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,text

from app import medical_continuous as core
from app import medical_assessment_ledger as ledger
from app import medical_registry_reconciliation as sourcecheck

WHEN="2026-11-08T18:13:00+00:00"
CANARY="NCT06081894"


def official(nct, *, phases=None, posted=False, status="ACTIVE_NOT_RECRUITING"):
    phase=["PHASE3"] if phases is None else phases
    return {
        "protocolSection":{
            "identificationModule":{"nctId":nct,"briefTitle":"Saved trial registry primary record"},
            "designModule":{"phases":phase},
            "sponsorCollaboratorsModule":{"leadSponsor":{"name":"Research sponsor"}},
            "statusModule":{
                "overallStatus":status,
                "lastUpdatePostDateStruct":{"date":"2026-09-22"},
                "studyFirstPostDateStruct":{"date":"2023-10-13"},
                "primaryCompletionDateStruct":{"date":"2026-08-31","type":"ACTUAL"},
                "completionDateStruct":{"date":"2026-11","type":"ESTIMATED"}},
            "outcomesModule":{"primaryOutcomes":[
                {"measure":"Prespecified symptom scale","timeFrame":"Week 36"},
                {"measure":"Exercise capacity","timeFrame":"Week 36"}]},
        },
        "resultsSection":{"outcomeMeasuresModule":{"outcomeMeasures":[
            {"type":"PRIMARY","measure":"Sponsor reported endpoint"}
        ]}} if posted else {},
    }


@pytest.fixture
def db(tmp_path):
    engine=create_engine("sqlite:///"+str(tmp_path/"registry.sqlite"),
                         connect_args={"check_same_thread":False})
    core.initialize(engine)
    for_ncts=sorted(core.roster())
    with engine.begin() as c:
        for nct in for_ncts:
            run=str(uuid.uuid4())
            c.execute(text("""INSERT INTO medical_continuous_runs
                (run_id,request_key,nct_id,status,stage_index,created_at,updated_at,stop_requested)
                VALUES(:run,:request,:nct,'COMPLETE',12,:now,:now,FALSE)"""),
                {"run":run,"request":str(uuid.uuid4()),"nct":nct,"now":WHEN})
            for i in range(12):
                doc={"nct":nct,"source":"https://clinicaltrials.gov/study/"+nct,
                     "phases":["PHASE3"] if i==0 else []}
                c.execute(text("""INSERT INTO medical_continuous_stages
                    (run_id,stage_index,state,document,finished_at)
                    VALUES(:run,:idx,'SOURCE_RECORDED',:doc,:now)"""),
                    {"run":run,"idx":i,"doc":json.dumps(doc),"now":WHEN})
    ledger.initialize(engine,test_only=True)
    ledger.seed_roster(engine)
    sourcecheck.initialize(engine,test_only=True)
    yield engine
    engine.dispose()


def configure(monkeypatch, ncts=CANARY):
    monkeypatch.setenv("PDUFA_MEDICAL_REGISTRY_RECONCILE_AUTORUN","true")
    monkeypatch.setenv("PDUFA_MEDICAL_REGISTRY_RECONCILE_CAMPAIGN","NOV08_REG_A")
    monkeypatch.setenv("PDUFA_MEDICAL_REGISTRY_RECONCILE_NCTS",ncts)
    monkeypatch.setenv("PDUFA_MEDICAL_BATCH_AUTORUN","false")
    monkeypatch.setenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_BATCH_AUTORUN","false")


def test_registry_phase_match_is_primary_source_authentication_not_human_signoff(db):
    row=sourcecheck.build_report(db,CANARY,official(CANARY))
    assert row["nct"]==CANARY
    assert row["phaseAgreement"]=="MATCHED_SINGLE_PHASE"
    assert row["savedRegistryPhases"]==row["currentRegistryPhases"]==["PHASE3"]
    assert row["machineSourceIdentityVerified"] is True
    assert row["reviewerVerifiedCurrentPhase"] is False
    assert row["lastCompletedPhaseIndependentlyVerified"] is False
    assert row["registeredPrimaryOutcomeCount"]==2
    assert row["registryPostedPrimaryOutcomeMeasures"]==0
    assert row["primaryCompletion"]["type"]=="ACTUAL"
    assert row["resultsInterpretation"]=="NO_POSTED_RESULTS_IN_RECORD"
    assert row["scientificGradesWritten"]==0
    assert row["certainty"]=="NOT_VALIDATED"
    assert all(v=="ABSTAIN" for v in row["fdaPredictions"].values())


def test_real_registry_posted_results_still_not_clinical_signoff(db):
    row=sourcecheck.build_report(db,CANARY,official(CANARY,posted=True))
    assert row["resultsSectionPresent"] is True
    assert row["registryPostedPrimaryOutcomeMeasures"]==1
    assert row["resultsInterpretation"]=="POSTED_SPONSOR_REPORTED_NOT_CLINICALLY_ADJUDICATED"
    assert row["primarySourceChecks"]["fullTextPeerReviewedReadoutVerified"] is False
    assert row["primarySourceChecks"]["protocolAndSapIndependentlyVerified"] is False
    assert row["scientificSignoff"] is False


def test_changed_phase_and_multiphase_require_review_not_automatic_revision(db):
    drift=sourcecheck.build_report(db,CANARY,official(CANARY,phases=["PHASE2"]))
    assert drift["phaseAgreement"]=="SOURCE_PHASE_DRIFT_REVIEW"
    assert drift["phaseReassessmentNeeded"] is True
    multi=sourcecheck.build_report(db,CANARY,official(CANARY,phases=["PHASE2","PHASE3"]))
    assert multi["phaseAgreement"]=="MULTIPHASE_REVIEW_REQUIRED"
    no_phase=sourcecheck.build_report(db,CANARY,official(CANARY,phases=[]))
    assert no_phase["phaseAgreement"]=="NO_REGISTRY_PHASE_REVIEW"
    assert all(row["reviewerVerifiedCurrentPhase"] is False
               for row in (drift,multi,no_phase))


def test_source_identity_mismatch_unknown_phase_and_invalid_nct_fail_closed(db):
    with pytest.raises(ValueError,match="identity"):
        sourcecheck.build_report(db,CANARY,official("NCT05507203"))
    with pytest.raises(ValueError,match="Unrecognized"):
        sourcecheck.build_report(db,CANARY,official(CANARY,phases=["INVALID_PHASE"]))
    with pytest.raises(ValueError,match="Exact NCT"):
        sourcecheck.build_report(db,"NOT_NCT",official(CANARY))


def test_append_only_exact_registry_version_and_zero_clinical_review_writes(db):
    one=sourcecheck.persist(db,CANARY,live=official(CANARY),test_only=True)
    two=sourcecheck.persist(db,CANARY,live=official(CANARY),test_only=True)
    assert one["snapshotId"]==two["snapshotId"]
    changed=sourcecheck.persist(db,CANARY,
             live=official(CANARY,phases=["PHASE2"]),test_only=True)
    assert one["snapshotId"]!=changed["snapshotId"]
    with db.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_registry_reconciliation_snapshots")).scalar_one()==2
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_stages")).scalar_one()==348
        assert c.execute(text("SELECT COUNT(*) FROM medical_assessment_review_events")).scalar_one()==0
        assert c.execute(text("SELECT COUNT(*) FROM medical_assessment_phase_events")).scalar_one()==0
    coverage=sourcecheck.coverage(db)
    assert coverage["savedNcts"]==1
    assert coverage["canonicalTrials"]==29
    assert len(coverage["missingNcts"])==28
    assert coverage["humanVerifiedClinicalPhases"]==0


def test_explicit_1_to_3_nct_batch_preflights_all_before_any_write(db,monkeypatch):
    configure(monkeypatch,"NCT05507203,NCT05507216,NCT04576949")
    calls=[]
    def network(nct):
        calls.append(nct)
        if nct=="NCT04576949":
            return official("NCT99999999")
        return official(nct)
    with pytest.raises(ValueError,match="identity"):
        sourcecheck.run_selected(db,test_only=True,fetch=network)
    assert len(calls)==3
    with db.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_registry_reconciliation_snapshots")).scalar_one()==0


def test_bounded_batch_and_durable_postgres_gate(db,monkeypatch):
    configure(monkeypatch,"NCT05507203,NCT05507216")
    with pytest.raises(RuntimeError,match="PostgreSQL"):
        sourcecheck.run_selected(db,fetch=lambda nct:official(nct))
    saved=sourcecheck.run_selected(db,test_only=True,fetch=lambda nct:official(nct))
    again=sourcecheck.run_selected(db,test_only=True,fetch=lambda nct:official(nct))
    assert len(saved)==len(again)==2
    assert [r["snapshotId"] for r in saved]==[r["snapshotId"] for r in again]
    assert sourcecheck.coverage(db)["savedNcts"]==2
    for invalid in (
        "NCT05507203,NCT05507203",
        "NCT05507203,NCT05507216,NCT04576949,NCT05126758",
        "NCT99999999", "",
    ):
        monkeypatch.setenv("PDUFA_MEDICAL_REGISTRY_RECONCILE_NCTS",invalid)
        with pytest.raises((ValueError,RuntimeError)):
            sourcecheck._selection()


def test_read_only_authenticated_routes(db):
    sourcecheck.persist(db,CANARY,live=official(CANARY),test_only=True)
    app=FastAPI()
    sourcecheck.install_routes(app,lambda:db,lambda:None,lambda:None)
    client=TestClient(app)
    assert client.get("/api/internal/medical-registry-reconciliation/coverage").json()["savedNcts"]==1
    item=client.get(f"/api/internal/medical-registry-reconciliation/{CANARY}/latest")
    assert item.status_code==200
    assert item.json()["phaseAgreement"]=="MATCHED_SINGLE_PHASE"
    assert client.post("/api/internal/medical-registry-reconciliation/coverage").status_code==405
    assert client.get("/api/internal/medical-registry-reconciliation/NCT99999999/latest").status_code==422
