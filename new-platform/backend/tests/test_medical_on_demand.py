"""Analyze Now is a reuse of the existing durable source worker, not another model."""
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
    # No pretend network; exactly one real source URL from the actual pilot trial.
    assert nct==PILOT
    source="https://clinicaltrials.gov/study/"+nct
    if index==0:
        return "SOURCE_RECORDED",{"source":source,"nct":nct,
                    "phases":["PHASE3"],"title":"Offline verified fixture NCT identity"}
    if index==1:
        return "SOURCE_RECORDED",{"source":source,"outcomesPosted":1,
                    "gap":"Sponsor-reported endpoint not independently reanalysed"}
    return "EVIDENCE_GAP",{"source":source,
             "gap":"Full regulatory/medical source package not available in fixture"}


def test_pilot_first_analysis_preserves_actual_45_research_score_and_abstains(engine):
    legacy=analyze.optional_legacy(PILOT)
    assert legacy["raasOverall"] is None
    assert legacy["clinicalFive"]==45
    assert legacy["clinicalScoredFactors"]==5
    assert legacy["status"]=="ARCHIVED_READ_ONLY"
    assert len(legacy["sources"])>=1

    key="00000000-0000-4000-8000-000000000201"
    job=analyze.start_now(engine,PILOT,key,submit=False)
    assert job["status"]=="PENDING"
    assert job["analysis"] is None
    core.worker(engine,job["runId"],step=fixture_stage)
    result=analyze.latest(engine,PILOT)
    assert result["status"]=="COMPLETE"
    assert result["completedStages"]==12
    assert result["revision"]==1
    a=result["analysis"]
    assert a["schema"]=="ANALYZE_NOW_V1"
    assert a["nct"]==PILOT
    assert a["trigger"]=="MANUAL"
    assert a["scores"]["scientificFiveFactorScore"]==45
    assert a["scores"]["raasOverallScore"] is None
    assert a["scores"]["sourceEventId"]
    assert len(a["scores"]["historicalFiveFactorEventIds"])>0
    assert a["scientificAssessment"]["sourceRecordedStages"]==2
    assert a["scientificAssessment"]["independentScientificSignoff"] is False
    assert a["scores"]["scientificFiveFactorsGraded"]==5
    assert len(a["fdaPredictions"])==3
    assert [p["outcome"] for p in a["fdaPredictions"]]==["APPROVAL","CRL","REVIEW_DELAY"]
    assert all(p["status"]=="ABSTAIN" and p["probability"] is None for p in a["fdaPredictions"])
    assert a["certainty"]["status"]=="NOT_VALIDATED"
    assert a["certainty"]["rating"] is None
    assert any(x["missing"].startswith("A validated full 30-metric RAAS score") for x in a["missingEvidence"])
    assert any("clinicaltrials.gov/study/"+PILOT in u for u in a["supportingSourceUrls"])
    assert any("nejm.org" in u for u in a["supportingSourceUrls"])
    saved=analyze.history(engine,PILOT)
    assert saved["historyKey"]=="EXACT_NCT"
    assert saved["locationIndependent"] is True
    assert saved["total"]==1
    assert saved["records"][0]["analysis"]["scores"]["scientificFiveFactorScore"]==45


def test_new_evidence_creates_second_immutable_report_not_an_overwrite(engine):
    first=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000202",submit=False)
    core.worker(engine,first["runId"],step=fixture_stage)
    second=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000203",submit=False,
                             trigger="REGISTRY_CHANGE")
    def new_evidence(i,nct):
        state,doc=fixture_stage(i,nct)
        if i==2:
            doc["observedUpdate"]="Updated source discussion, not an FDA decision"
        return state,doc
    core.worker(engine,second["runId"],step=new_evidence)
    reports=analyze.history(engine,PILOT)
    assert reports["total"]==2
    assert [x["revision"] for x in reports["records"]]==[2,1]
    assert reports["records"][0]["evidenceChanged"] is True
    assert reports["records"][0]["analysis"]["trigger"]=="REGISTRY_CHANGE"
    assert reports["records"][1]["analysis"]["trigger"]=="MANUAL"
    assert all(r["analysis"]["scores"]["scientificFiveFactorScore"]==45 for r in reports["records"])


def test_history_survives_move_out_of_current_focus_list(engine,tmp_path,monkeypatch):
    job=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000204",submit=False)
    core.worker(engine,job["runId"],step=fixture_stage)
    new_focus=tmp_path/"focus_changed.json"
    new_focus.write_text(json.dumps({"records":[{"nct":OTHER,"ticker":"CAPR"}]}))
    monkeypatch.setattr(core,"FOCUS",new_focus)
    # The old trial is no longer eligible for new work, but saved history is
    # still readable through the exact NCT, without any Google Sheet lookup.
    assert analyze.history(engine,PILOT)["total"]==1
    assert analyze.latest(engine,PILOT)["status"]=="COMPLETE"
    with pytest.raises(ValueError):
        analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000205",submit=False)


def test_duplicate_clicks_reuse_existing_worker_and_idempotency_key(engine):
    first=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000206",submit=False)
    same=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000206",submit=False)
    new_key=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000207",submit=False)
    assert first["runId"]==same["runId"]==new_key["runId"]
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_runs")).scalar()==1
        assert c.execute(text("SELECT COUNT(*) FROM medical_analyze_requests")).scalar()==1


def test_manual_rollout_gated_beyond_pilot_unless_explicitly_enabled(engine,monkeypatch):
    with pytest.raises(ValueError,match="gated"):
        analyze.start_now(engine,OTHER,"00000000-0000-4000-8000-000000000208",submit=False)
    monkeypatch.setenv("PDUFA_ANALYZE_NOW_ALL_ENABLED","true")
    job=analyze.start_now(engine,OTHER,"00000000-0000-4000-8000-000000000208",submit=False)
    assert job["nct"]==OTHER and job["status"]=="PENDING"


def test_operational_component_change_is_auto_requeued_without_duplicate_active(engine,monkeypatch):
    submissions=[]
    monkeypatch.setattr(core._POOL,"submit",lambda fn,db,run_id:submissions.append(run_id))
    first=analyze.check_operational_component_changes(engine,generation="tested-v1")
    assert first["checked"]==29 and first["baselined"]==29 and first["queued"]==0
    again=analyze.check_operational_component_changes(engine,generation="tested-v1")
    assert again["queued"]==0
    # A manual pending pilot must not produce a duplicate active worker.
    pending=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000209",submit=False)
    changed=analyze.check_operational_component_changes(engine,generation="tested-v2")
    assert changed["queued"]==28
    assert changed["deferred"]==1
    assert len(submissions)==28
    assert pending["status"]=="PENDING"
    with engine.begin() as c:
        c.execute(text("""UPDATE medical_continuous_runs SET status='FAILED'
            WHERE run_id=:run"""),{"run":pending["runId"]})
    deferred=analyze.check_operational_component_changes(engine,generation="tested-v2")
    assert deferred["queued"]==1
    assert deferred["checked"]==29
    assert len(submissions)==29


def test_source_research_works_even_when_optional_raas_archive_missing(engine,monkeypatch,tmp_path):
    monkeypatch.setattr(analyze,"LEGACY",tmp_path/"unavailable-raas.json")
    job=analyze.start_now(engine,PILOT,"00000000-0000-4000-8000-000000000210",submit=False)
    core.worker(engine,job["runId"],step=fixture_stage)
    a=analyze.latest(engine,PILOT)["analysis"]
    assert a["scores"]["raasOverallScore"] is None
    assert a["scores"]["scientificFiveFactorScore"] is None
    assert a["scientificAssessment"]["sourceRecordedStages"]==2
    assert all(p["status"]=="ABSTAIN" for p in a["fdaPredictions"])
