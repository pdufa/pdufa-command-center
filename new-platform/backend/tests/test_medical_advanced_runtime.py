"""Research history and source-change watcher tests. No network or production calls."""
import json

import pytest
from sqlalchemy import create_engine, text
from app import medical_continuous as medical
from app import medical_advanced_runtime as advanced
from app import medical_on_demand as analyze

NCT="NCT00000001"


@pytest.fixture
def engine(tmp_path,monkeypatch):
    monkeypatch.setenv("PDUFA_ANALYZE_NOW_CANARY_NCT",NCT)
    f=tmp_path/"focus.json"
    f.write_text(json.dumps({"records":[{"nct":NCT,"ticker":"TEST","company":"Fixture"}]}))
    monkeypatch.setattr(medical,"FOCUS",f)
    d=tmp_path/"applications.json"
    d.write_text('{"schemaVersion":1,"asOf":"2026-11-07","records":[]}')
    monkeypatch.setattr(medical,"APPLICATIONS",d)
    db=create_engine("sqlite:///"+str(tmp_path/"medical.sqlite3"),
                     connect_args={"check_same_thread":False})
    medical.initialize(db)
    yield db
    db.dispose()


def run_full(engine,key,source_tag):
    job=medical.create(engine,NCT,key,submit=False)
    def record_stage(i,nct):
        return ("SOURCE_RECORDED" if i==0 else "LEADS_ONLY"), {
          "source":"https://clinicaltrials.gov/study/"+nct,"source_tag":source_tag,"stage_id":i}
    medical.worker(engine,job["runId"],step=record_stage)
    return medical.snapshot(engine,NCT,job["runId"])


def test_append_only_history_has_three_abstentions_and_independent_certainty(engine):
    final=run_full(engine,"00000000-0000-4000-8000-000000000001","v1")
    assert final["status"]=="COMPLETE"
    h=advanced.list_revisions(engine,NCT)
    assert h["totalShown"]==1
    item=h["revisions"][0]
    assert item["ordinal"]==1
    assert item["evidenceChanged"] is True
    r=item["report"]
    assert len(r["reviewLevels"])==12
    assert r["completedIndependentReviews"]==0
    assert r["calibrationReleasePermitted"] is False
    assert [o["outcome"] for o in r["outcomes"]]==["APPROVAL","CRL","REVIEW_DELAY"]
    assert all(o["status"]=="ABSTAIN" and o["probability"] is None for o in r["outcomes"])
    assert r["certainty"]["rating"] is None
    assert r["certainty"]["status"]=="NOT_VALIDATED"
    medical.worker(engine,final["runId"],step=lambda *_:pytest.fail("Should not repeat"))
    assert advanced.list_revisions(engine,NCT)["totalShown"]==1


def test_revision_history_detects_changed_sources_and_retains_prior(engine):
    first=run_full(engine,"00000000-0000-4000-8000-000000000002","a")
    second=run_full(engine,"00000000-0000-4000-8000-000000000003","b")
    third=run_full(engine,"00000000-0000-4000-8000-000000000004","b")
    h=advanced.list_revisions(engine,NCT)["revisions"]
    assert [r["runId"] for r in h]==[third["runId"],second["runId"],first["runId"]]
    assert [r["ordinal"] for r in h]==[3,2,1]
    assert [r["evidenceChanged"] for r in h]==[False,True,True]
    assert h[1]["sourceDigest"]==h[0]["sourceDigest"]
    assert h[2]["sourceDigest"]!=h[1]["sourceDigest"]


def study(label):
    return {"protocolSection":{
       "identificationModule":{"nctId":NCT},
       "statusModule":{"overallStatus":label},
       "designModule":{"phases":["PHASE3"]}},
       "resultsSection":{"outcomeMeasuresModule":{"outcomeMeasures":[]}}}


def test_exact_registry_monitor_baseline_change_defer_and_fail_closed(engine,monkeypatch):
    recorded=[]
    def fake_start(_db,nct,key,*,trigger):
        assert nct==NCT and trigger=="REGISTRY_CHANGE"
        recorded.append(key)
        return {"runId":"synthetic","status":"PENDING"}
    monkeypatch.setattr(analyze,"start_now",fake_start)
    baseline=advanced.check_registry_updates_once(engine,fetch=lambda n:study("RECRUITING"))
    assert baseline["baselined"]==1 and baseline["queued"]==0
    stable=advanced.check_registry_updates_once(engine,fetch=lambda n:study("RECRUITING"))
    assert stable["changed"]==0 and not recorded
    change=advanced.check_registry_updates_once(engine,fetch=lambda n:study("COMPLETED"))
    assert change["queued"]==1 and len(recorded)==1
    stable_again=advanced.check_registry_updates_once(engine,fetch=lambda n:study("COMPLETED"))
    assert stable_again["queued"]==0
    bad=advanced.check_registry_updates_once(engine,fetch=lambda n:{
       "protocolSection":{"identificationModule":{"nctId":"NCT99999999"}}})
    assert bad["unavailable"]==1
    assert len(recorded)==1


def test_active_trial_defers_change_until_current_run_completes(engine):
    baseline=advanced.check_registry_updates_once(engine,fetch=lambda n:study("RECRUITING"))
    assert baseline["baselined"]==1
    job=medical.create(engine,NCT,"00000000-0000-4000-8000-000000000010",submit=False)
    blocked=advanced.check_registry_updates_once(engine,fetch=lambda n:study("COMPLETED"))
    assert blocked["activeDeferred"]==1 and blocked["queued"]==0
    with engine.connect() as c:
        digest=c.execute(text("SELECT evidence_digest FROM medical_registry_watch WHERE nct_id=:n"),
             {"n":NCT}).scalar_one()
    assert digest==advanced.registry_digest(study("RECRUITING"),NCT)
    assert job["status"]=="PENDING"


def test_auto_watch_requires_explicit_postgres_setup(engine,monkeypatch):
    monkeypatch.setenv("PDUFA_MEDICAL_AUTO_WATCH","1")
    assert advanced.start_watch(engine) is False
    monkeypatch.delenv("PDUFA_MEDICAL_AUTO_WATCH")
