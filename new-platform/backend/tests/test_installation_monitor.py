"""Installation monitor contract: live DB evidence, fail-closed health and Telegram idempotence."""
import json
from sqlalchemy import create_engine,text
from app import installation_monitor as monitor
from app import medical_continuous


def db(tmp_path):
    engine=create_engine("sqlite:///"+str(tmp_path/"telemetry.sqlite3"))
    medical_continuous.initialize(engine)
    monitor.initialize(engine)
    return engine


def test_no_ephemeral_sqlite_can_masquerade_as_postgres(tmp_path):
    engine=db(tmp_path)
    r=monitor.collect(engine,storage_ready=True,require_postgres=True)
    assert r["storage"]["state"]=="BLOCKED"
    assert r["research"]["state"]=="BLOCKED"
    assert r["scans"]["phase3Ingestion"]["state"]=="BLOCKED"
    engine.dispose()


def test_read_only_telemetry_counts_real_runs_and_does_not_infer_predicted_outcomes(tmp_path):
    engine=db(tmp_path)
    with engine.begin() as c:
        c.execute(text("""INSERT INTO medical_continuous_runs
            (run_id,request_key,nct_id,status,stage_index,created_at,updated_at)
            VALUES(:run,:key,:nct,'COMPLETE',12,:now,:now)"""),
            {"run":"00000000-0000-4000-8000-000000000100","key":"k",
             "nct":"NCT00000001","now":"2026-11-08T00:00:00Z"})
        c.execute(text("""INSERT INTO medical_prediction_revisions
            (run_id,nct_id,ordinal,source_digest,evidence_changed,report,recorded_at)
            VALUES(:run,:nct,1,:digest,1,:report,:now)"""),
            {"run":"00000000-0000-4000-8000-000000000100","nct":"NCT00000001",
             "digest":"a"*64,"report":json.dumps({"outcomes":["ABSTAIN"]}),
             "now":"2026-11-08T00:00:00Z"})
    before=monitor.collect(engine,storage_ready=True,require_postgres=False)
    after=monitor.collect(engine,storage_ready=True,require_postgres=False)
    assert before["research"]["finishedSourceRuns"]==1
    assert before["research"]["immutableRevisions"]==1
    assert before["research"]["completedIndependentReviews"]==0
    assert before["research"]["probabilityForecastsValidated"] is False
    assert before["research"]["certaintyReliabilityValidated"] is False
    assert after["research"]["finishedSourceRuns"]==1
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM installation_monitor_alerts")).scalar()==0
    engine.dispose()


def test_duplicate_milestone_alerts_are_deduplicated_without_telegram(tmp_path,monkeypatch):
    engine=db(tmp_path)
    monkeypatch.delenv("PDUFA_TELEGRAM_BOT_TOKEN",raising=False)
    monkeypatch.delenv("PDUFA_TELEGRAM_CHAT_ID",raising=False)
    monitor._queue_event(engine,"MILESTONE","first-trial","First trial saved")
    monitor._queue_event(engine,"MILESTONE","first-trial","First trial saved")
    with engine.connect() as c:
        r=c.execute(text("SELECT kind,delivery_state,attempts FROM installation_monitor_alerts")).first()
        count=c.execute(text("SELECT COUNT(*) FROM installation_monitor_alerts")).scalar()
    assert count==1
    assert r[0]=="MILESTONE" and r[1]=="PENDING" and r[2]==0
    assert monitor.configured() is False
    engine.dispose()


def test_monitor_poll_records_real_failure_and_milestone_no_telegram_spam(tmp_path,monkeypatch):
    engine=db(tmp_path)
    monkeypatch.delenv("PDUFA_TELEGRAM_BOT_TOKEN",raising=False)
    monkeypatch.delenv("PDUFA_TELEGRAM_CHAT_ID",raising=False)
    with engine.begin() as c:
        c.execute(text("""INSERT INTO medical_continuous_runs
            (run_id,request_key,nct_id,status,stage_index,created_at,updated_at)
            VALUES('00000000-0000-4000-8000-000000000101','key1',
                   'NCT00000001','FAILED',0,'2026-11-08','2026-11-08')"""))
        c.execute(text("""INSERT INTO medical_continuous_runs
            (run_id,request_key,nct_id,status,stage_index,created_at,updated_at)
            VALUES('00000000-0000-4000-8000-000000000102','key2',
                   'NCT00000002','COMPLETE',12,'2026-11-08','2026-11-08')"""))
    for _ in range(2):
        monitor.monitor_once(engine,storage_ready=True,require_postgres=False)
    with engine.connect() as c:
        events=list(c.execute(text("SELECT kind,delivery_state,attempts FROM installation_monitor_alerts ORDER BY kind")))
    assert len(events)==3
    assert {k for k,_,_ in events}=={"MILESTONE","FAILURE"}
    assert all(status=="PENDING" and count==0 for _,status,count in events)
    engine.dispose()


def test_telegram_delivery_is_explicit_and_deduplicated(tmp_path,monkeypatch):
    engine=db(tmp_path)
    monkeypatch.setenv("PDUFA_TELEGRAM_BOT_TOKEN","fake-only")
    monkeypatch.setenv("PDUFA_TELEGRAM_CHAT_ID","fixture")
    sends=[]
    monkeypatch.setattr(monitor,"_telegram_send",lambda msg:sends.append(msg) or True)
    with engine.begin() as c:
        c.execute(text("""INSERT INTO medical_continuous_runs
            (run_id,request_key,nct_id,status,stage_index,created_at,updated_at)
            VALUES('00000000-0000-4000-8000-000000000103','key3',
                   'NCT00000003','COMPLETE',12,'2026-11-08','2026-11-08')"""))
    monitor.monitor_once(engine,storage_ready=True,require_postgres=False)
    monitor.monitor_once(engine,storage_ready=True,require_postgres=False)
    assert len(sends)==2
    with engine.connect() as c:
        events=list(c.execute(text("SELECT delivery_state,attempts,sent_at FROM installation_monitor_alerts")))
    assert all(item[0]=="SENT" and item[1]==1 and item[2] for item in events)
    engine.dispose()


def test_watchdog_disabled_unless_opted_in_to_persistent_postgres(tmp_path,monkeypatch):
    engine=db(tmp_path)
    monkeypatch.setenv("PDUFA_INSTALL_MONITOR_ENABLED","true")
    assert monitor.start(engine,ready_provider=lambda:True) is False
    monkeypatch.delenv("PDUFA_INSTALL_MONITOR_ENABLED")
    assert monitor.start(engine,ready_provider=lambda:True) is False
    engine.dispose()


def test_render_liveness_route_is_separate_from_storage_health():
    from fastapi.testclient import TestClient
    from app.main import app
    response=TestClient(app).head("/")
    assert response.status_code==204
    assert response.headers["cache-control"]=="no-store"


def test_completed_source_revision_queues_one_evidence_update_not_a_prediction(tmp_path,monkeypatch):
    engine=db(tmp_path)
    monkeypatch.delenv("PDUFA_TELEGRAM_BOT_TOKEN",raising=False)
    monkeypatch.delenv("PDUFA_TELEGRAM_CHAT_ID",raising=False)
    with engine.begin() as c:
        for ordinal in (1,2):
            run=f"00000000-0000-4000-8000-{ordinal:012d}"
            c.execute(text("""INSERT INTO medical_continuous_runs
                (run_id,request_key,nct_id,status,stage_index,created_at,updated_at)
                VALUES(:run,:key,'NCT00000001','COMPLETE',12,'2026-11-08','2026-11-08')"""),
                {"run":run,"key":"key"+str(ordinal)})
            c.execute(text("""INSERT INTO medical_prediction_revisions
                (run_id,nct_id,ordinal,source_digest,evidence_changed,report,recorded_at)
                VALUES(:run,'NCT00000001',:ordinal,:digest,1,:report,:at)"""),
                {"run":run,"ordinal":ordinal,"digest":str(ordinal)*64,
                 "report":json.dumps({"outcomes":[{"outcome":"APPROVAL","status":"ABSTAIN",
                     "probability":None}]}),"at":f"2026-11-0{ordinal}"})
    observed=monitor.monitor_once(engine,storage_ready=True,require_postgres=False)
    monitor.monitor_once(engine,storage_ready=True,require_postgres=False)
    assert observed["research"]["newSourceEvidenceRevisions"]==1
    with engine.connect() as c:
        changed=list(c.execute(text("""SELECT event_key,kind,message FROM installation_monitor_alerts
            WHERE kind='EVIDENCE_UPDATE'""")))
    assert len(changed)==1
    assert changed[0][0]=="medical-evidence:00000000-0000-4000-8000-000000000002"
    assert changed[0][1]=="EVIDENCE_UPDATE"
    assert "FDA predictions remain evidence-gated" in changed[0][2]
    assert "approval probability" not in changed[0][2].lower()
    engine.dispose()


def test_packaged_application_evidence_is_visible_without_postgres(tmp_path):
    engine=db(tmp_path)
    report=monitor.collect(engine,storage_ready=False,require_postgres=True)
    context=report["sourceSnapshots"]["applications"]
    assert context["state"]=="VALID"
    assert context["focusNctCount"]==29
    assert context["coveredNctCount"]==29
    assert context["applicationCycleCount"]==23
    assert context["fdaApplicationStatusVerified"] is False
    assert report["storage"]["state"]=="BLOCKED"
    engine.dispose()
