"""The single Analyze Now worker uses independent sources, not retired scores."""
import json

import pytest
from sqlalchemy import create_engine,text
from app import medical_continuous as core
from app import medical_on_demand as analyze

PILOT="NCT06081894"
OTHER="NCT05126758"


@pytest.fixture
def engine(tmp_path,monkeypatch):
    monkeypatch.delenv("PDUFA_ANALYZE_NOW_ALL_ENABLED",raising=False)
    monkeypatch.delenv("PDUFA_ANALYZE_NOW_CANARY_NCT",raising=False)
    db=create_engine("sqlite:///"+str(tmp_path/"on_demand.sqlite3"),
                     connect_args={"check_same_thread":False})
    core.initialize(db)
    yield db
    db.dispose()


def fixture_stage(index,nct):
    assert nct==PILOT
    source="https://clinicaltrials.gov/study/"+nct
    if index==0:
        return "SOURCE_RECORDED",{"source":source,"nct":nct,
                    "phases":["PHASE3"],"title":"Offline identity fixture"}
    if index==1:
        return "SOURCE_RECORDED",{"source":source,"outcomesPosted":1,
                    "gap":"Outcome not independently reanalysed"}
    return "EVIDENCE_GAP",{"source":source,
             "gap":"Full statistical/regulatory/medical evidence unavailable in fixture"}


def test_initial_pilot_is_source_only_and_fda_abstains(engine):
    job=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000201",submit=False)
    assert job["status"]=="PENDING"
    report=job["analysis"]
    assert report["nct"]==PILOT
    assert report["scientificAssessment"]["stagesAttempted"]==0
    assert "scores" not in report
    assert "raas" not in json.dumps(report).lower()
    assert [p["outcome"] for p in report["fdaPredictions"]]==["APPROVAL","CRL","REVIEW_DELAY"]
    assert all(p["status"]=="ABSTAIN" and p["probability"] is None for p in report["fdaPredictions"])
    assert report["certainty"]["status"]=="NOT_VALIDATED"
    assert report["certainty"]["rating"] is None
    saved=analyze.history(engine,PILOT)
    assert saved["total"]==1
    assert saved["records"][0]["revision"] is None
    assert saved["records"][0]["analysis"]["savedAt"]


def test_one_real_worker_fixture_run_persists_source_outcomes(engine):
    job=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000202",submit=False)
    core.worker(engine,job["runId"],step=fixture_stage)
    result=analyze.latest(engine,PILOT)
    assert result["status"]=="COMPLETE"
    assert result["completedStages"]==12
    assert result["revision"]==1
    a=result["analysis"]
    assert a["schema"]=="ANALYZE_NOW_V1"
    assert a["nct"]==PILOT
    assert a["trigger"]=="MANUAL"
    assert a["scientificAssessment"]["stagesAttempted"]==12
    assert a["scientificAssessment"]["sourceRecordedStages"]==2
    assert a["scientificAssessment"]["independentScientificSignoff"] is False
    assert "scores" not in a and "legacyRaas" not in a["componentReadiness"]
    assert len(a["fdaPredictions"])==3
    assert all(p["status"]=="ABSTAIN" and p["probability"] is None for p in a["fdaPredictions"])
    assert a["certainty"]["rating"] is None
    assert any("clinicaltrials.gov/study/"+PILOT in u for u in a["supportingSourceUrls"])
    assert a["missingEvidence"]
    saved=analyze.history(engine,PILOT)
    assert saved["historyKey"]=="EXACT_NCT"
    assert saved["locationIndependent"] is True
    assert saved["total"]==1
    assert saved["records"][0]["revision"]==1


def test_evidence_rerun_appends_revision_not_overwrites(engine):
    first=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000203",submit=False)
    core.worker(engine,first["runId"],step=fixture_stage)
    second=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000204",
                              submit=False,trigger="REGISTRY_CHANGE")
    def next_source(i,nct):
        state,doc=fixture_stage(i,nct)
        if i==2:
            doc["evidenceRevision"]="New source comment; NOT a prediction"
        return state,doc
    core.worker(engine,second["runId"],step=next_source)
    reports=analyze.history(engine,PILOT)
    assert [x["revision"] for x in reports["records"]]==[2,1]
    assert reports["records"][0]["evidenceChanged"] is True
    assert reports["records"][0]["analysis"]["trigger"]=="REGISTRY_CHANGE"
    assert reports["records"][1]["analysis"]["trigger"]=="MANUAL"
    assert "scores" not in reports["records"][0]["analysis"]


def test_history_survives_move_out_of_focus(engine,tmp_path,monkeypatch):
    job=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000205",submit=False)
    core.worker(engine,job["runId"],step=fixture_stage)
    changed=tmp_path/"focus_changed.json"
    changed.write_text(json.dumps({"records":[{"nct":OTHER,"ticker":"CAPR"}]}))
    monkeypatch.setattr(core,"FOCUS",changed)
    assert analyze.history(engine,PILOT)["total"]==1
    assert analyze.latest(engine,PILOT)["status"]=="COMPLETE"
    with pytest.raises(ValueError):
        analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000206",submit=False)


def test_duplicate_clicks_are_idempotent(engine):
    first=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000207",submit=False)
    same=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000207",submit=False)
    another=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000208",submit=False)
    assert first["runId"]==same["runId"]==another["runId"]
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_runs")).scalar()==1
        assert c.execute(text("SELECT COUNT(*) FROM medical_analyze_requests")).scalar()==1


def test_gated_rollout_only_enabled_by_flag(engine,monkeypatch):
    with pytest.raises(ValueError,match="gated"):
        analyze.start_now(engine,OTHER,"00000000-0000-4000-8000-000000000209",submit=False)
    monkeypatch.setenv("PDUFA_ANALYZE_NOW_ALL_ENABLED","true")
    job=analyze.start_now(engine,OTHER,"00000000-0000-4000-8000-000000000209",submit=False)
    assert job["nct"]==OTHER
    assert job["status"]=="PENDING"
    assert "scores" not in job["analysis"]


def test_component_change_watch_only_operates_within_canary(engine,monkeypatch):
    submissions=[]
    monkeypatch.setattr(core._POOL,"submit",lambda fn,db,run_id:submissions.append(run_id))
    baseline=analyze.check_operational_component_changes(engine,generation="source-v2")
    assert baseline["checked"]==1 and baseline["baselined"]==1
    repeat=analyze.check_operational_component_changes(engine,generation="source-v2")
    assert repeat["queued"]==0
    pending=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000210",submit=False)
    changed=analyze.check_operational_component_changes(engine,generation="source-v3")
    assert changed["queued"]==0 and changed["deferred"]==1
    assert submissions==[]
    with engine.begin() as c:
        c.execute(text("""UPDATE medical_continuous_runs SET status='FAILED'
           WHERE run_id=:run"""),{"run":pending["runId"]})
    after=analyze.check_operational_component_changes(engine,generation="source-v3")
    assert after["queued"]==1
    assert len(submissions)==1


def test_failed_source_stage_retains_initial_report(engine):
    job=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000211",submit=False)
    def failed(i,nct):
        raise TimeoutError("Offline fixture source failure")
    core.worker(engine,job["runId"],step=failed)
    report=analyze.latest(engine,PILOT)
    assert report["status"]=="FAILED"
    assert report["analysis"]["scientificAssessment"]["stagesAttempted"]==0
    assert "scores" not in report["analysis"]
    saved=analyze.history(engine,PILOT)
    assert saved["total"]==1 and saved["records"][0]["revision"] is None
    assert saved["records"][0]["analysis"]["savedAt"]


def test_one_engine_supports_all_32_after_rollout_flag(engine,monkeypatch):
    monkeypatch.setenv("PDUFA_ANALYZE_NOW_ALL_ENABLED","true")
    ncts=sorted(core.roster())
    assert len(ncts)==32
    for i,nct in enumerate(ncts):
        job=analyze.start_now(engine,nct,f"00000000-0000-4000-8000-{i+900:012d}",submit=False)
        assert job["nct"]==nct and job["status"]=="PENDING"
        assert "scores" not in job["analysis"]
        assert job["analysis"]["certainty"]["rating"] is None
        assert analyze.history(engine,nct)["total"]==1
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_runs")).scalar()==32
