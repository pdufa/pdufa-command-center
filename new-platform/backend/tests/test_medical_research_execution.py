"""Research receipts never promote source work into clinical reviewer grades."""
import hashlib
import json
import os
import uuid

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DatabaseError

from app import medical_assessment_ledger as ledger
from app import medical_continuous as source
from app import medical_research_execution as research

WHEN = "2026-11-08T18:00:00+00:00"


@pytest.fixture
def db(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "research-execution.sqlite"))
    source.initialize(engine)
    ledger.initialize(engine, test_only=True)
    runs = {}
    with engine.begin() as c:
        for nct in source.roster():
            rid = runs[nct] = str(uuid.uuid4())
            c.execute(text("""INSERT INTO medical_continuous_runs
              (run_id,request_key,nct_id,status,stage_index,created_at,updated_at,stop_requested)
              VALUES(:id,:key,:nct,'COMPLETE',12,:at,:at,FALSE)"""),
              {"id": rid, "key": str(uuid.uuid4()), "nct": nct, "at": WHEN})
            for index in range(12):
                document = {"nct": nct, "source": "https://clinicaltrials.gov/study/" + nct,
                            "phases": ["PHASE3"], "fixture": "Not real scientific evidence"}
                c.execute(text("""INSERT INTO medical_continuous_stages
                  (run_id,stage_index,state,document,finished_at)
                  VALUES(:run,:idx,'SOURCE_RECORDED',:doc,:at)"""),
                  {"run": rid, "idx": index, "doc": json.dumps(document), "at": WHEN})
    ledger.seed_roster(engine)
    research.initialize(engine, test_only=True)
    yield engine, runs
    engine.dispose()


def examination(engine, run, *, request_key="source-examination-001", missing=False):
    next_task = run["nextTask"]
    with engine.connect() as c:
        doc = c.execute(text("SELECT document FROM medical_continuous_stages WHERE run_id=:id AND stage_index=0"),
                        {"id": run["sourceRunId"]}).scalar_one()
    return {
        "request_key": request_key, "assessment_index": next_task["assessmentIndex"],
        "method_index": next_task["methodIndex"],
        "sources": [] if missing else [{"stageIndex": 0,
            "sourceUrl": "https://clinicaltrials.gov/study/" + research.PILOT,
            "stageDocumentSha256": hashlib.sha256(doc.encode()).hexdigest(),
            "sourceVersion": "synthetic-fixture-v1", "publicationDate": "2026-11-01", "sourceLocation": "Fixture registry identity module"}],
        "findings": [{"classification": "MISSING" if missing else "CONTRADICTORY",
                      "finding": "Synthetic source examination used solely to verify research-state separation and restart integrity."}],
        "limitations": "This offline fixture has no clinical evidentiary meaning.",
        "rationale": "This is an isolated software test and never an actual clinical review or scientific recommendation.",
        "examined_at": WHEN, "producer_id": "isolated-test-driver",
    }


def assert_no_clinical_writes(engine):
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_assessment_review_events")).scalar_one() == 0
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_stages")).scalar_one() == 348


def test_all_29_readonly_plans_have_800_questions_without_starting_runs(db):
    engine, _ = db
    for nct in source.roster():
        planned = research.plan(engine, nct)
        assert len(planned["tasks"]) == 800
        assert len({(t["assessmentIndex"], t["methodIndex"]) for t in planned["tasks"]}) == 800
        assert sorted(t["priorityRank"] for t in planned["tasks"]) == list(range(1, 801))
        assert planned["tasks"][0]["priorityTier"] == "CRITICAL"
        assert planned["officialGradesWritten"] == 0
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_research_execution_runs")).scalar_one() == 0
    other = next(nct for nct in source.roster() if nct != research.PILOT)
    with pytest.raises(ValueError, match="restricted"):
        research.start(engine, other)


def test_idempotent_restart_keeps_receipts_and_separates_missing_from_zero(db):
    engine, _ = db
    run = research.start(engine)
    first = examination(engine, run)
    event = research.append_examination(engine, run["runId"], **first)
    gap = examination(engine, research.snapshot(engine, run["runId"]), request_key="source-gap-002", missing=True)
    gap_event = research.append_examination(engine, run["runId"], **gap)
    restart = research.start(engine)
    assert restart["runId"] == run["runId"]
    assert restart["examinedPositions"] == 1
    assert restart["recordedPositions"] == 2
    assert restart["gapPositions"] == 1
    assert restart["remainingExaminations"] == 799
    assert restart["recommendationPositions"] == 0
    assert research.append_examination(engine, run["runId"], **first) == event
    assert research.append_examination(engine, run["runId"], **gap) == gap_event
    with pytest.raises(ValueError, match="different examined"):
        research.append_examination(engine, run["runId"], **{**first, "limitations": "A different material uncertainty is introduced here."})
    with pytest.raises(ValueError, match="missing is never zero"):
        research.append_examination(engine, run["runId"], **{**gap, "request_key": "gap-score-003", "recommendation": 0})
    assert_no_clinical_writes(engine)


def test_source_hash_identity_phase_freshness_and_priority_fail_closed(db):
    engine, runs = db
    run = research.start(engine)
    item = examination(engine, run)
    with pytest.raises(ValueError, match="next phase-prioritized"):
        research.append_examination(engine, run["runId"], **{**item, "method_index": 20 if item["method_index"] != 20 else 19})
    with pytest.raises(ValueError, match="captured digest"):
        research.append_examination(engine, run["runId"], **{**item, "sources": [{**item["sources"][0], "stageDocumentSha256": "f" * 64}]})
    with pytest.raises(ValueError, match="captured digest"):
        research.append_examination(engine, run["runId"], **{**item, "sources": [{**item["sources"][0], "sourceUrl": "https://clinicaltrials.gov/study/NCT99999999"}]})
    with pytest.raises(ValueError, match="independently verified phase"):
        research.append_examination(engine, run["runId"], **{**item, "recommendation": 3})
    ledger.record_verified_phase(engine, nct=research.PILOT, run_id=runs[research.PILOT],
                                 phase="PHASE3", reviewer_id="fixture-phase-verifier", verified_at=WHEN)
    with pytest.raises(ValueError, match="Latest phase"):
        research.append_examination(engine, run["runId"], **item)
    assert research.snapshot(engine, run["runId"])["status"] == "STALE_CONTEXT"
    assert research.snapshot(engine, run["runId"])["recordedPositions"] == 0
    assert research.start(engine)["runId"] != run["runId"]
    assert_no_clinical_writes(engine)


def test_revision_preserves_first_sources_and_is_not_an_official_grade(db):
    engine, runs = db
    ledger.record_verified_phase(engine, nct=research.PILOT, run_id=runs[research.PILOT],
                                 phase="PHASE3", reviewer_id="fixture-phase-verifier", verified_at=WHEN)
    run = research.start(engine)
    item = examination(engine, run)
    first = research.append_examination(engine, run["runId"], **item)
    second = research.append_examination(engine, run["runId"], **{
        **item, "request_key": "revised-examination-002", "recommendation": 0,
        "supersedes_event_id": first,
        "rationale": "Synthetic examined adverse finding supports a research-only zero recommendation, never a clinical grade."})
    latest = research.snapshot(engine, run["runId"])
    assert latest["historicalExaminationEvents"] == 2
    assert latest["examinedPositions"] == 1
    assert latest["recommendationPositions"] == 1
    assert latest["events"][0]["recommendation"] is None
    assert latest["events"][1]["examinationId"] == second
    assert latest["events"][1]["supersedesEventId"] == first
    assert latest["events"][1]["recommendationState"] == "RESEARCH_ONLY_PENDING_AUTHORIZED_REVIEW"
    assert latest["officialGradesWritten"] == 0
    assert latest["prediction"] == "ABSTAIN"
    assert_no_clinical_writes(engine)


def test_changed_captured_source_invalidates_frozen_run_without_rewriting_history(db):
    engine, runs = db
    run = research.start(engine)
    first = examination(engine, run)
    event = research.append_examination(engine, run["runId"], **first)
    # Corrupt only this isolated fixture to model a source version changing.
    # The production collector must preserve its older saved source records.
    with engine.begin() as c:
        c.execute(text("UPDATE medical_continuous_stages SET document=:doc WHERE run_id=:run AND stage_index=11"),
                  {"doc": json.dumps({"revisedSource": "offline fixture"}), "run": runs[research.PILOT]})
    stale = research.snapshot(engine, run["runId"])
    assert stale["status"] == "STALE_CONTEXT"
    assert stale["events"][0]["examinationId"] == event
    with pytest.raises(ValueError, match="captured source version changed"):
        research.append_examination(engine, run["runId"], **{**first, "request_key": "stale-source-revision-002", "supersedes_event_id": event})
    renewed = research.start(engine)
    assert renewed["runId"] != run["runId"]
    assert renewed["recordedPositions"] == 0
    assert research.snapshot(engine, run["runId"])["historicalExaminationEvents"] == 1
    assert_no_clinical_writes(engine)


def test_future_phase_recommendations_refused_even_with_current_phase_and_sources(db):
    engine, runs = db
    with engine.begin() as c:
        document = c.execute(text("SELECT document FROM medical_continuous_stages WHERE run_id=:run AND stage_index=0"),
                             {"run": runs[research.PILOT]}).scalar_one()
        identity = json.loads(document)
        identity["phases"] = ["PHASE1"]
        c.execute(text("UPDATE medical_continuous_stages SET document=:doc WHERE run_id=:run AND stage_index=0"),
                  {"doc": json.dumps(identity), "run": runs[research.PILOT]})
    ledger.record_verified_phase(engine, nct=research.PILOT, run_id=runs[research.PILOT],
                                 phase="PHASE1", reviewer_id="fixture-phase-verifier", verified_at=WHEN)
    run = research.start(engine)
    forward = next(t for t in research.plan(engine, research.PILOT)["tasks"] if t["phaseApplicability"] == "FORWARD_LOOKING")
    item = examination(engine, run)
    with pytest.raises(ValueError, match="Forward-looking"):
        research.append_examination(engine, run["runId"], **{**item,
            "assessment_index": forward["assessmentIndex"], "method_index": forward["methodIndex"], "recommendation": 0})
    assert research.snapshot(engine, run["runId"])["recordedPositions"] == 0
    assert_no_clinical_writes(engine)


def test_fixed_service_activation_is_opt_in_and_creates_no_run(db, monkeypatch):
    engine, _ = db
    for flag in ("PDUFA_MEDICAL_PREVIEW_ENABLED", "PDUFA_MEDICAL_ASSESSMENT_LEDGER_ENABLED",
                 "PDUFA_MEDICAL_PHASE_MATRIX_ENABLED", "PDUFA_MEDICAL_RESEARCH_EXECUTION_ENABLED"):
        monkeypatch.setenv(flag, "true")
    monkeypatch.setenv("RENDER_SERVICE_ID", "a-production-or-unrelated-service")
    calls = []
    monkeypatch.setattr(research, "initialize", lambda db: calls.append(db))
    assert research.activate(engine, ledger_ready=True) is False
    monkeypatch.setenv("RENDER_SERVICE_ID", research.ISOLATED_SERVICE)
    assert research.activate(engine, ledger_ready=False) is False
    assert research.activate(engine, ledger_ready=True) is True
    assert calls == [engine]
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_research_execution_runs")).scalar_one() == 0
        assert c.execute(text("SELECT COUNT(*) FROM medical_research_examination_events")).scalar_one() == 0


def test_read_routes_auth_identity_storage_and_absence_of_http_writes(db):
    engine, _ = db
    app = FastAPI()
    def denied():
        raise HTTPException(401, "Read authorization required")
    research.install_routes(app, lambda: engine, denied, lambda: None)
    path = "/api/internal/medical-research-execution/" + research.PILOT
    with TestClient(app) as client:
        assert client.get(path + "/plan").status_code == 401
        assert client.get(path + "/latest").status_code == 401
    public = FastAPI()
    research.install_routes(public, lambda: engine, lambda: None, lambda: None)
    with TestClient(public) as client:
        packet = client.get(path + "/plan")
        assert packet.status_code == 200
        assert len(packet.json()["tasks"]) == 800
        assert client.get(path + "/latest").status_code == 404
        assert client.get("/api/internal/medical-research-execution/NCT99999999/plan").status_code == 422
        assert client.post(path + "/plan", json={}).status_code == 405
        assert client.post(path + "/latest", json={}).status_code == 405
        run = research.start(engine)
        research.append_examination(engine, run["runId"], **examination(engine, run))
        observed = client.get(path + "/latest").json()
        assert observed["examinedPositions"] == 1
        assert observed["officialGradesWritten"] == 0
    blocked = FastAPI()
    def storage_unavailable():
        raise HTTPException(503, "Durable storage required")
    research.install_routes(blocked, lambda: engine, lambda: None, storage_unavailable)
    with TestClient(blocked) as client:
        assert client.get(path + "/plan").status_code == 503
    assert_no_clinical_writes(engine)


def _isolated_postgres_url():
    """Same dedicated loopback contract as the existing clinical ledger test."""
    configured = os.getenv("PDUFA_TEST_POSTGRES_URL")
    if not configured:
        pytest.skip("Dedicated loopback PostgreSQL research test database is not configured")
    url = make_url(configured)
    if (url.drivername != "postgresql+psycopg" or url.host not in ("127.0.0.1", "localhost")
            or url.port != 55432 or url.database != "pdufa_ledger_test" or url.query):
        pytest.fail("Research PostgreSQL test requires the dedicated loopback test database")
    return url


def test_real_isolated_postgres_research_guards_restarts_and_no_clinical_writes(db):
    url = _isolated_postgres_url()
    schema = "research_execution_test_" + uuid.uuid4().hex
    admin = create_engine(url)
    pg = create_engine(url, connect_args={"options": "-csearch_path=" + schema})
    local, _ = db
    created = False
    try:
        with admin.begin() as c:
            c.execute(text(f"CREATE SCHEMA {schema}"))
        created = True
        source.initialize(pg)
        ledger.initialize(pg)
        research.initialize(pg)
        with local.connect() as c:
            runs = [dict(row) for row in c.execute(text("SELECT * FROM medical_continuous_runs")).mappings()]
            stages = [dict(row) for row in c.execute(text("SELECT * FROM medical_continuous_stages")).mappings()]
        for row in runs:
            row["stop_requested"] = bool(row["stop_requested"])
        with pg.begin() as c:
            c.execute(text("""INSERT INTO medical_continuous_runs
                (run_id,request_key,nct_id,status,stage_index,created_at,updated_at,stop_requested)
                VALUES(:run_id,:request_key,:nct_id,:status,:stage_index,:created_at,:updated_at,:stop_requested)"""), runs)
            c.execute(text("""INSERT INTO medical_continuous_stages
                (run_id,stage_index,state,document,finished_at)
                VALUES(:run_id,:stage_index,:state,:document,:finished_at)"""), stages)
        ledger.seed_roster(pg)
        run = research.start(pg)
        first = examination(pg, run)
        event = research.append_examination(pg, run["runId"], **first)
        before = research.snapshot(pg, run["runId"])
        for table in ("medical_research_execution_runs", "medical_research_examination_events"):
            for sql in (f"UPDATE {table} SET run_id=run_id", f"DELETE FROM {table}", f"TRUNCATE {table} CASCADE"):
                with pytest.raises(DatabaseError, match="append-only"):
                    with pg.begin() as c:
                        c.execute(text(sql))
                assert research.snapshot(pg, run["runId"]) == before
        research.initialize(pg)
        assert research.start(pg)["runId"] == run["runId"]
        assert research.append_examination(pg, run["runId"], **first) == event
        revised = research.append_examination(pg, run["runId"], **{**first,
            "request_key": "postgres-research-revision-002", "supersedes_event_id": event,
            "limitations": "Additional offline uncertainty is documented without rewriting the first source examination."})
        after = research.snapshot(pg, run["runId"])
        assert after["historicalExaminationEvents"] == 2
        assert after["recordedPositions"] == 1
        assert after["events"][1]["examinationId"] == revised
        assert after["events"][0] == before["events"][0]
        assert_no_clinical_writes(pg)
    finally:
        pg.dispose()
        if created:
            with admin.begin() as c:
                c.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()


def test_bounded_batch_replays_completed_receipt_after_interruption(db):
    engine, _ = db
    run = research.start(engine)
    first = examination(engine, run)
    # Second item deliberately repeats the first position with a different
    # request key and no supersession. Only the completed first item persists.
    wrong_second = {**first, "request_key": "interrupted-second-002"}
    with pytest.raises(ValueError, match="supersede"):
        research.process_batch(engine, run["runId"], [first, wrong_second])
    current = research.snapshot(engine, run["runId"])
    assert current["recordedPositions"] == 1
    second = examination(engine, current, request_key="corrected-second-003")
    ids = research.process_batch(engine, run["runId"], [first, second])
    assert len(ids) == 2
    assert research.snapshot(engine, run["runId"])["recordedPositions"] == 2
    with pytest.raises(ValueError, match="1–20"):
        research.process_batch(engine, run["runId"], [first] * 21)
    assert_no_clinical_writes(engine)


@pytest.mark.parametrize("table", ["medical_research_execution_runs", "medical_research_examination_events"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_research_history_rejects_mutation(db, table, operation):
    engine, _ = db
    run = research.start(engine)
    research.append_examination(engine, run["runId"], **examination(engine, run))
    sql = f"DELETE FROM {table}" if operation == "DELETE" else f"UPDATE {table} SET run_id=run_id"
    with pytest.raises(DatabaseError, match="append-only"):
        with engine.begin() as c:
            c.execute(text(sql))
    research.initialize(engine, test_only=True)
    assert research.snapshot(engine, run["runId"])["recordedPositions"] == 1
    assert_no_clinical_writes(engine)
