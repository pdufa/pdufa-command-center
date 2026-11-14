"""Precision monitor is read-only, fail-closed and independent of the prediction engine."""
import json
from sqlalchemy import create_engine,text
from fastapi.testclient import TestClient
from app import installation_monitor as mon
from app.main import app

def sqlite(tmp_path):
    engine=create_engine("sqlite:///"+str(tmp_path/"precision.sqlite3"))
    return engine

def test_unavailable_postgres_is_blocked_and_read_only(tmp_path):
    engine=sqlite(tmp_path)
    before=set(__import__("sqlalchemy").inspect(engine).get_table_names())
    a=mon.collect(engine,storage_ready=True,require_postgres=True)
    assert a["storage"]["state"]=="BLOCKED"
    assert a["research"]["state"]=="BLOCKED"
    assert a["analysisNow"]["pilotSaved"] is False
    assert a["sourceSnapshots"]["applications"]["state"]=="PARTIAL"
    assert a["sourceSnapshots"]["applications"]["focusNctCount"]==32
    assert a["sourceSnapshots"]["applications"]["coveredNctCount"]==29
    assert a["sourceSnapshots"]["applications"]["fdaApplicationStatusVerified"] is False
    assert set(__import__("sqlalchemy").inspect(engine).get_table_names())==before
    engine.dispose()

def test_monitor_api_requires_internal_key(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY","test-monitor-internal-key")
    client=TestClient(app)
    assert client.get("/api/internal/installation-monitor").status_code==401
    assert client.get("/api/internal/installation-monitor",headers={"X-Pdufa-Internal-Key":"invalid"}).status_code==401
    good=client.get("/api/internal/installation-monitor",headers={"X-Pdufa-Internal-Key":"test-monitor-internal-key"})
    assert good.status_code==200
    assert good.json()["storage"]["state"]=="BLOCKED"
    assert good.json()["alerts"]["lastDelivery"] is None

def test_exact_nct_revision_history_only_from_stored_rows(tmp_path):
    engine=sqlite(tmp_path)
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE medical_continuous_runs (
            run_id TEXT PRIMARY KEY,nct_id TEXT,status TEXT,updated_at TEXT)"""))
        c.execute(text("""CREATE TABLE medical_prediction_revisions (
            run_id TEXT PRIMARY KEY,nct_id TEXT,ordinal INTEGER,source_digest TEXT,
            evidence_changed BOOLEAN,report TEXT,recorded_at TEXT)"""))
        c.execute(text("""CREATE TABLE medical_continuous_stages (
            run_id TEXT,stage_index INTEGER,state TEXT)"""))
        c.execute(text("""INSERT INTO medical_continuous_runs VALUES(
            '00000000-0000-4000-8000-000000000001','NCT06081894','COMPLETE','2026-11-08T00:00:00Z')"""))
        c.execute(text("""INSERT INTO medical_prediction_revisions VALUES(
            '00000000-0000-4000-8000-000000000001','NCT06081894',1,'a',1,'{}','2026-11-08T00:00:00Z')"""))
        c.execute(text("""INSERT INTO medical_continuous_stages VALUES(
            '00000000-0000-4000-8000-000000000001',0,'SOURCE_RECORDED')"""))
    report=mon.collect(engine,storage_ready=True,require_postgres=False)
    trial=report["trialHistories"]["NCT06081894"]
    assert trial["state"]=="OBSERVED"
    assert trial["sourceStages"]==1
    assert trial["revisions"][0]["ordinal"]==1
    assert trial["latestStatus"]=="COMPLETE"
    assert report["research"]["probabilityForecastsValidated"] is False
    assert report["research"]["certaintyReliabilityValidated"] is False
    engine.dispose()

def test_telegram_alert_dedup_is_opt_in_and_no_secret_echo(tmp_path,monkeypatch):
    engine=sqlite(tmp_path)
    monkeypatch.delenv("PDUFA_TELEGRAM_BOT_TOKEN",raising=False)
    monkeypatch.delenv("PDUFA_TELEGRAM_CHAT_ID",raising=False)
    mon.initialize(engine)
    mon._queue_event(engine,"MILESTONE","precision-monitor-ready","Verified checkpoint")
    mon._queue_event(engine,"MILESTONE","precision-monitor-ready","Verified checkpoint")
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM installation_monitor_alerts")).scalar()==1
        row=c.execute(text("SELECT delivery_state,attempts FROM installation_monitor_alerts")).one()
    assert row[0]=="PENDING" and row[1]==0
    assert mon.configured() is False
    assert mon.start(engine,ready_provider=lambda:True) is False
    engine.dispose()
