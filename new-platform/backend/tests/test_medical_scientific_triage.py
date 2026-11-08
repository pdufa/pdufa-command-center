"""Stage-4 research triage is not a scientific verdict or FDA predictor."""
import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app import medical_continuous as core
from app import medical_assessment_ledger as ledger
from app import medical_scientific_triage as triage

CANARY = "NCT06081894"
WHEN = "2026-11-08T17:45:00+00:00"


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.delenv("PDUFA_MEDICAL_BATCH_AUTORUN",raising=False)
    monkeypatch.delenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_CANARY_AUTORUN",raising=False)
    monkeypatch.delenv("PDUFA_ANALYZE_NOW_CANARY_NCT",raising=False)
    db=create_engine("sqlite:///"+str(tmp_path/"triage.sqlite"),
                     connect_args={"check_same_thread":False})
    core.initialize(db)
    statuses = ["SOURCE_RECORDED","SOURCE_RECORDED","LEADS_ONLY",
                "LEADS_ONLY","EVIDENCE_GAP","LEADS_ONLY","LEADS_ONLY",
                "SOURCE_RECORDED","SOURCE_RECORDED","EVIDENCE_GAP",
                "LEADS_ONLY","EVIDENCE_GAP"]
    with db.begin() as c:
        for nct in sorted(core.roster()):
            run=str(uuid.uuid4())
            c.execute(text("""INSERT INTO medical_continuous_runs
                (run_id,request_key,nct_id,status,stage_index,created_at,updated_at,stop_requested)
                VALUES (:run,:key,:nct,'COMPLETE',12,:at,:at,FALSE)"""),
                {"run":run,"key":str(uuid.uuid4()),"nct":nct,"at":WHEN})
            for stage in range(12):
                doc={"nct":nct,"source":"https://clinicaltrials.gov/study/"+nct}
                if stage==0:
                    doc["phases"]=["PHASE3"]
                if stage==1:
                    doc.update(outcomesPosted=2,hasResults=True,
                               primaryEndpoints=["Reported measure not assessed"])
                if stage==3:
                    doc["publications"]=[{"pmid":"test-bibliographic-lead"}]
                if stage==7:
                    doc.update(reportedComparisons=2,
                               examples=[{"reportedP":"0.001","method":"POSTHOC_UNKNOWN"}],
                               gap="Multiplicity and SAP not independently assessed")
                if stage==8:
                    doc.update(reportedGroups=2,reportedSeriousEventTerms=4,
                               gap="Individual causality unadjudicated")
                if stage in (4,9,11):
                    doc["gap"]="Independent reviewer evidence not yet collected"
                c.execute(text("""INSERT INTO medical_continuous_stages
                    (run_id,stage_index,state,document,finished_at)
                    VALUES (:run,:idx,:state,:document,:at)"""),
                    {"run":run,"idx":stage,"state":statuses[stage],
                     "document":json.dumps(doc),"at":WHEN})
    ledger.initialize(db,test_only=True)
    ledger.seed_roster(db)
    triage.initialize(db,test_only=True)
    yield db
    db.dispose()


def test_all_40_assessments_20_scientific_methods_have_source_lead_mapping():
    c=triage._exact_catalog()
    assert len(c["assessments"])==40
    assert len(c["methods"])==20
    assert set(triage.ASSESSMENT_STAGE_LEADS)=={a["id"] for a in c["assessments"]}
    assert set(triage.METHOD_STAGE_HINTS)==set(range(1,21))


def test_real_12_stage_records_map_to_800_unadjudicated_method_questions(engine):
    row=triage.analyze(engine,CANARY)
    assert row["schema"]=="SOURCE_TRIAGE_V1"
    assert row["nct"]==CANARY
    assert row["assessmentCount"]==40
    assert row["methodPositions"]==800
    assert row["sourceStageCount"]==12
    assert sum(row["sourceClassCounts"].values())==800
    assert len(row["assessments"])==40
    assert all(len(a["methods"])==20 for a in row["assessments"])
    assert all(t["scientificGrade"] is None and t["scientificGradeStatus"]=="NOT_REVIEWED"
               and t["observedClinicalFinding"] is None
               for a in row["assessments"] for t in a["methods"])
    assert all(a["finalScientificScore"] is None for a in row["assessments"])
    assert row["methodsWithIndependentGrade"]==0
    assert row["scientificSignoff"] is False
    assert all(x=="ABSTAIN" for x in row["fdaPredictions"].values())
    assert row["certainty"]=="NOT_VALIDATED"
    assert row["observedClinicalRiskFindings"]==[]
    assert all(q["status"]=="PROMPT_NOT_OBSERVED_RISK" for q in row["phaseRiskQuestions"])


def test_unreviewed_positive_p_value_never_becomes_drug_benefit(engine):
    row=triage.analyze(engine,CANARY)
    trial_section=next(x for x in row["assessments"] if x["assessmentId"]=="4.3")
    all_source_leads=[lead for method in trial_section["methods"]
                      for lead in method["sourceLeads"]]
    assert any(x["sourceFacts"].get("reportedComparisons")==2 for x in all_source_leads)
    assert not any("reportedP" in str(x) for x in all_source_leads)
    assert all(m["scientificGrade"] is None for m in trial_section["methods"])
    assert trial_section["finalScientificScore"] is None
    assert all(lead["requiresIndependentReview"] is True for lead in all_source_leads)


def test_origin_source_digest_is_reproducible(engine):
    one=triage.analyze(engine,CANARY)
    two=triage.analyze(engine,CANARY)
    assert one["sourceInputSha256"]==two["sourceInputSha256"]
    assert one["catalogSha256"]==two["catalogSha256"]
    assert len(one["sourceInputSha256"])==64
    assert one["assessments"]==two["assessments"]


def test_append_only_canary_snapshot_is_idempotent_and_preserves_source_tables(engine):
    first=triage.persist(engine,CANARY,test_only=True)
    second=triage.persist(engine,CANARY,test_only=True)
    assert first["snapshotId"]==second["snapshotId"]
    assert triage.history(engine,CANARY)["total"]==1
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_scientific_triage_snapshots")).scalar_one()==1
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_stages")).scalar_one()==348
        assert c.execute(text("SELECT COUNT(*) FROM medical_assessment_review_events")).scalar_one()==0
        assert c.execute(text("SELECT COUNT(*) FROM medical_assessment_phase_events")).scalar_one()==0


def test_auto_run_is_canary_gated_and_never_runs_an_alternate_nct(engine,monkeypatch):
    # Exercise the actual canary gate while explicitly using isolated SQLite
    # test persistence. Production run_canary still requires PostgreSQL.
    original_persist = triage.persist
    monkeypatch.setattr(triage, "persist",
        lambda db,nct: original_persist(db,nct,test_only=True))
    assert triage.run_canary(engine) is None
    monkeypatch.setenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_CANARY_AUTORUN","true")
    monkeypatch.setenv("PDUFA_ANALYZE_NOW_CANARY_NCT","NCT05507203")
    with pytest.raises(RuntimeError,match="original NCT canary"):
        triage.run_canary(engine)
    monkeypatch.setenv("PDUFA_ANALYZE_NOW_CANARY_NCT",CANARY)
    first=triage.run_canary(engine)
    assert first["methodPositions"]==800
    assert triage.run_canary(engine)["snapshotId"]==first["snapshotId"]
    assert triage.history(engine,CANARY)["total"]==1
    monkeypatch.setenv("PDUFA_MEDICAL_BATCH_AUTORUN","true")
    with pytest.raises(RuntimeError,match="cannot overlap"):
        triage.run_canary(engine)


def test_gaps_and_source_records_are_not_called_observed_clinical_risk(engine):
    row=triage.analyze(engine,CANARY)
    all_methods=[m for a in row["assessments"] for m in a["methods"]]
    assert any(m["sourceClassification"]=="SOURCE_RECORD_UNADJUDICATED" for m in all_methods)
    assert any(m["sourceClassification"]=="RESEARCH_LEADS_ONLY" for m in all_methods)
    assert any(m["sourceClassification"] in (
        "SOURCE_GAP","IDENTITY_ONLY_NO_CLINICAL_DATA") for m in all_methods)
    assert not any(m["observedClinicalFinding"] is not None for m in all_methods)


def test_authenticated_read_routes_are_get_only_no_triage_write_route(engine):
    triage.persist(engine,CANARY,test_only=True)
    app=FastAPI()
    triage.install_routes(app,lambda:engine,lambda:None,lambda:None)
    client=TestClient(app)
    latest=client.get("/api/internal/medical-scientific-triage/"+CANARY+"/latest")
    assert latest.status_code==200 and latest.json()["methodPositions"]==800
    hist=client.get("/api/internal/medical-scientific-triage/"+CANARY+"/history")
    assert hist.status_code==200 and hist.json()["total"]==1
    assert client.post("/api/internal/medical-scientific-triage/"+CANARY+"/latest").status_code==405
    assert client.get("/api/internal/medical-scientific-triage/NCT99999999/latest").status_code==422


def configure_scientific_tail(monkeypatch, ncts="NCT05507203,NCT05507216,NCT04576949"):
    monkeypatch.setenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_BATCH_AUTORUN","true")
    monkeypatch.setenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_BATCH_CAMPAIGN","NOV08_TRIAGE_B")
    monkeypatch.setenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_BATCH_NCTS",ncts)
    monkeypatch.setenv("PDUFA_MEDICAL_BATCH_AUTORUN","false")
    monkeypatch.setenv("PDUFA_ANALYZE_NOW_ALL_ENABLED","false")


def test_controlled_tail_rejects_duplicate_unrostered_and_original_canary(monkeypatch):
    assert triage.requested_batch() is None
    configure_scientific_tail(monkeypatch)
    campaign,ncts=triage.requested_batch()
    assert campaign=="NOV08_TRIAGE_B"
    assert ncts==("NCT05507203","NCT05507216","NCT04576949")
    for batch in ("NCT05507203", "NCT05507203,NCT05507216"):
        monkeypatch.setenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_BATCH_NCTS",batch)
        assert len(triage.requested_batch()[1])==len(batch.split(","))
    invalid = [
        "NCT05507203,NCT05507203",
        "NCT06081894",
        "NCT99999999",
        "NCT05507203,NCT05507216,NCT04576949,NCT05126758",
        "NCT05507203,INVALID",
        "",
    ]
    for batch in invalid:
        monkeypatch.setenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_BATCH_NCTS",batch)
        with pytest.raises((ValueError,RuntimeError)):
            triage.requested_batch()
    monkeypatch.setenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_BATCH_NCTS","NCT05507203")
    monkeypatch.setenv("PDUFA_ANALYZE_NOW_ALL_ENABLED","true")
    with pytest.raises(RuntimeError,match="Global all-trial"):
        triage.requested_batch()
    monkeypatch.setenv("PDUFA_ANALYZE_NOW_ALL_ENABLED","false")
    monkeypatch.setenv("PDUFA_MEDICAL_BATCH_AUTORUN","true")
    with pytest.raises(RuntimeError,match="cannot overlap"):
        triage.requested_batch()


def test_tail_requires_durable_postgresql_unless_explicit_test_only(engine,monkeypatch):
    configure_scientific_tail(monkeypatch)
    with pytest.raises(RuntimeError,match="PostgreSQL"):
        triage.run_batch(engine)
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_scientific_triage_snapshots")).scalar_one()==0


def test_three_trial_batch_preflights_before_any_scientific_snapshot_writes(engine,monkeypatch):
    configure_scientific_tail(monkeypatch)
    victim="NCT04576949"
    run=ledger.trial_history(engine,victim)["sourceRunId"]
    with engine.begin() as c:
        c.execute(text("""DELETE FROM medical_continuous_stages
            WHERE run_id=:run AND stage_index=11"""),{"run":run})
    with pytest.raises(RuntimeError,match="Exactly 12"):
        triage.run_batch(engine,test_only=True)
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_scientific_triage_snapshots")).scalar_one()==0


def test_three_trial_tail_is_idempotent_and_preserves_29_original_research_runs(engine,monkeypatch):
    configure_scientific_tail(monkeypatch)
    first=triage.run_batch(engine,test_only=True)
    second=triage.run_batch(engine,test_only=True)
    assert len(first)==len(second)==3
    assert [x["snapshotId"] for x in first]==[x["snapshotId"] for x in second]
    assert all(x["methodPositions"]==800 and x["methodsWithIndependentGrade"]==0
               for x in first)
    assert all(x["scientificSignoff"] is False and x["certainty"]=="NOT_VALIDATED"
               for x in first)
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_scientific_triage_snapshots")).scalar_one()==3
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_stages")).scalar_one()==348
        assert c.execute(text("SELECT COUNT(*) FROM medical_assessment_review_events")).scalar_one()==0
        assert c.execute(text("SELECT COUNT(*) FROM medical_assessment_phase_events")).scalar_one()==0


def test_persisted_exact_trial_source_triage_coverage_is_distinct_from_scientific_grading(engine,monkeypatch):
    before=triage.coverage(engine)
    assert before["canonicalTrials"]==29
    assert before["sourceResearchCompleteNcts"]==29
    assert before["originalSourceStages"]==348
    assert before["savedNcts"]==0
    assert before["methodPositionsScreened"]==0
    assert before["status"]=="IN_PROGRESS"
    triage.persist(engine,CANARY,test_only=True)
    configure_scientific_tail(monkeypatch)
    triage.run_batch(engine,test_only=True)
    triage.run_batch(engine,test_only=True)
    after=triage.coverage(engine)
    assert after["savedNcts"]==4
    assert after["methodPositionsScreened"]==3200
    assert after["savedSnapshotCount"]==4
    assert len(after["missingNcts"])==25
    assert after["unexpectedNcts"]==[]
    assert after["independentScientificReviewEvents"]==0
    assert after["reviewerVerifiedPhaseNcts"]==0
    assert after["scientificSignoff"] is False
    assert after["fdaPrediction"]=="ABSTAIN"
    assert after["certainty"]=="NOT_VALIDATED"
    app=FastAPI()
    triage.install_routes(app,lambda:engine,lambda:None,lambda:None)
    client=TestClient(app)
    result=client.get("/api/internal/medical-scientific-triage/coverage")
    assert result.status_code==200
    assert result.json()["savedNcts"]==4
    assert client.post("/api/internal/medical-scientific-triage/coverage").status_code==405
