"""Offline gates for one-time isolated, real-HTTP scientific smoke verification."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main, scientific_live_smoke as smoke

NCT = "NCT04280705"
KEY = "private-smoke-test-token"


@pytest.fixture
def review(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://review.invalid/db")
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", KEY)
    monkeypatch.setenv("RENDER_SERVICE_ID", smoke._ISOLATED_SERVICE_ID)
    monkeypatch.setenv("PDUFA_SCIENTIFIC_BATCH_WRITE_ENABLED", "1")
    with Session(engine) as session:
        session.add(main.FullTrialRecord(
            nct_id=NCT, payload_gzip=b"placeholder", sha256="x"*64,
            summary={"nctId": NCT}, statistics=[], fetched_at=datetime.now(timezone.utc),
        ))
        session.commit()
    yield
    engine.dispose()


def test_preflight_accepts_only_previously_archived_trial(review):
    assert smoke._preflight(NCT) == (True, "ready")
    assert smoke._preflight("NCT00000001") == (False, "source_not_archived")
    assert smoke._preflight("bad") == (False, "invalid_id")


@pytest.mark.parametrize("variable,value,reason", [
    ("RENDER_SERVICE_ID", "srv-production", "wrong_service"),
    ("PDUFA_SCIENTIFIC_BATCH_WRITE_ENABLED", "0", "write_disabled"),
    ("PDUFA_INTERNAL_API_KEY", "", "missing_internal_key"),
])
def test_preflight_fails_closed(review, monkeypatch, variable, value, reason):
    monkeypatch.setenv(variable, value)
    assert smoke._preflight(NCT) == (False, reason)


def test_preflight_blocks_active_job_and_repeat_single_id_smoke(review):
    now = datetime.now(timezone.utc)
    with Session(main.ENGINE) as session:
        job = main.ScientificBatchJob(
            id="a"*32, status="queued", nct_ids=[NCT], events=[], total=1,
            processed=0, imported=0, already_exists=0, failed=0,
            active_slot="scientific-import", created_at=now, updated_at=now,
            completed_at=None,
        )
        session.add(job)
        session.commit()
    assert smoke._preflight(NCT) == (False, "unfinished_batch_present")
    with Session(main.ENGINE) as session:
        job = session.get(main.ScientificBatchJob, "a"*32)
        job.active_slot = None
        job.status = "completed"
        job.completed_at = now
        session.commit()
    assert smoke._preflight(NCT) == (False, "single_id_batch_already_recorded")


def test_complete_authenticated_http_sequence_without_leaking_key(review, caplog):
    caplog.set_level("WARNING")
    seen = []
    result = [
        (401, {}), (200, {"jobs":[]}),
        (202, {"id":"b"*32}),
        (200, {"status":"running"}),
        (200, {"status":"completed","processed":1,"already_exists":1,
               "imported":0,"failed":0,
               "events":[{"status":"already_exists"}]}),
    ]
    def fake_http(method, path, key, payload=None):
        seen.append((method,path,key,payload))
        return result.pop(0)

    with patch.object(smoke, "_request", side_effect=fake_http), \
         patch.object(smoke, "time") as time_module:
        assert smoke.run_smoke(NCT, delay_before_start=0, poll_interval=0,
                               max_polls=3) is True
        assert time_module.sleep.call_count >= 2
    assert [item[0] for item in seen] == ["GET","GET","POST","GET","GET"]
    assert seen[0][2] is None
    assert seen[1][2] == KEY
    assert seen[2][3] == {"nct_ids":[NCT]}
    assert "SCIENTIFIC_E2E_SMOKE status=PASS" in caplog.text
    assert KEY not in caplog.text
    with Session(main.ENGINE) as session:
        claim = session.get(main.ScientificSmokeClaim, NCT)
        assert claim.status == "passed"
        assert claim.finished_at is not None


def test_atomic_claim_prevents_second_submission_even_if_preflight_was_stale(review, caplog):
    assert smoke._preflight(NCT) == (True, "ready")
    assert smoke._claim_once(NCT) is True
    # Simulate another live replica that passed preflight before the first claim.
    with patch.object(smoke, "_request") as request:
        assert smoke.run_smoke(NCT, delay_before_start=0, poll_interval=0) is False
        request.assert_not_called()
    assert "atomic_claim_already_exists" in caplog.text
    with Session(main.ENGINE) as session:
        claim = session.get(main.ScientificSmokeClaim, NCT)
        assert claim.status == "claimed"


def test_unexpected_unauthed_success_blocks_submission(review):
    seen=[]
    def fake_http(method,path,key,payload=None):
        seen.append(method)
        return (200,{})
    with patch.object(smoke,"_request",side_effect=fake_http), \
         patch.object(smoke,"time"):
        assert smoke.run_smoke(NCT,delay_before_start=0) is False
    assert seen==["GET"]
    with Session(main.ENGINE) as session:
        claim = session.get(main.ScientificSmokeClaim, NCT)
        assert claim.status == "failed"
        assert claim.finished_at is not None


def test_no_automatic_smoke_without_explicit_flag(review, monkeypatch):
    monkeypatch.delenv("PDUFA_SCIENTIFIC_SMOKE_NCT", raising=False)
    with patch.object(smoke.threading, "Thread") as thread:
        smoke.launch_once_if_requested()
        thread.assert_not_called()
