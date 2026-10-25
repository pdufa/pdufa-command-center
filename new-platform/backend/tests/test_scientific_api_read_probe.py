"""Exercise the actual read routes against disposable storage; no live writes."""
import copy
import gzip
import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func, event
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.pool import StaticPool

from app import main
from app import scientific_api_read_probe as probe

KEY = "probe-test-private-key"


@pytest.fixture
def archived_api(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://isolated.invalid/test")
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", KEY)
    raw = json.dumps({"protocolSection": {
        "identificationModule": {"nctId": probe.NCT_ID},
        "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE3"],
                         "enrollmentInfo": {"count": 305},
                         "designInfo": {"allocation": "RANDOMIZED",
                                        "maskingInfo": {"masking": "NONE"}}},
    }}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    with Session(engine) as session:
        session.add(main.FullTrialRecord(
            nct_id=probe.NCT_ID, payload_gzip=gzip.compress(raw),
            sha256=hashlib.sha256(raw).hexdigest(), summary={}, statistics=[],
            fetched_at=datetime(2026, 10, 24, tzinfo=timezone.utc),
        ))
        session.commit()
    # SQLite drops timezone metadata; PostgreSQL preserves it. Restore this
    # fixture's known UTC timestamp on load, without marking the row dirty.
    def preserve_fixture_utc(record, context):
        if record.fetched_at.tzinfo is None:
            set_committed_value(record, "fetched_at", record.fetched_at.replace(tzinfo=timezone.utc))

    event.listen(main.FullTrialRecord, "load", preserve_fixture_utc)
    try:
        with TestClient(main.app) as client:
            calls = []

            def read(path, key):
                calls.append(path)
                response = client.get(path, headers={"x-pdufa-internal-key": key} if key else {})
                return response.status_code, response.json()

            yield read, calls, engine
    finally:
        event.remove(main.FullTrialRecord, "load", preserve_fixture_utc)
        engine.dispose()


def test_actual_routes_pass_without_mutating_any_application_table(archived_api):
    read, calls, engine = archived_api
    with engine.connect() as connection:
        before = {table.name: connection.scalar(select(func.count()).select_from(table))
                  for table in main.Base.metadata.sorted_tables}
        original_sha256 = connection.execute(select(main.FullTrialRecord.sha256)).scalar_one()
    assert probe.check_api(KEY, read) == {
        "checks": 7, "stored_trials": 1, "batch_jobs": 0, "domains": 8,
    }
    assert len(calls) == 7
    with engine.connect() as connection:
        after = {table.name: connection.scalar(select(func.count()).select_from(table))
                 for table in main.Base.metadata.sorted_tables}
        assert after == before
        assert connection.execute(select(main.FullTrialRecord.sha256)).scalar_one() == original_sha256


@pytest.mark.parametrize("corruption", ["unauthenticated", "identity", "score", "packet"])
def test_probe_rejects_auth_bypass_wrong_trial_scores_and_packet_tampering(archived_api, corruption):
    read, _, _ = archived_api

    def corrupt(path, key):
        status, body = read(path, key)
        body = copy.deepcopy(body)
        if corruption == "unauthenticated" and key is None:
            return 200, {}
        if corruption == "identity" and "pilot/keynote024" in path:
            body["dossier"]["nct_id"] = "NCT00000001"
        if corruption == "score" and path == probe.TRIAL_PATH and status == 200:
            body["readinessGrades"]["scientificScore"] = 99
        if corruption == "packet" and "/review-packet/" in path:
            body["archive"]["sourceSha256"] = "tampered"
        return status, body

    with pytest.raises(ValueError):
        probe.check_api(KEY, corrupt)


def test_loopback_transport_uses_get_header_and_blocks_redirects():
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return b'{"ok":true}'

    with patch.object(probe, "build_opener") as opener:
        opener.return_value.open.return_value = Response()
        assert probe._request_json(probe.TRIAL_PATH, KEY) == (200, {"ok": True})
        request = opener.return_value.open.call_args.args[0]
        assert request.get_method() == "GET"
        assert request.full_url.startswith("http://127.0.0.1:8000/")
        assert KEY not in request.full_url
        assert dict((k.lower(), v) for k, v in request.header_items())["x-pdufa-internal-key"] == KEY
        assert any(isinstance(handler, probe._NoRedirect) for handler in opener.call_args.args)
    assert probe._NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid") is None


def test_failures_never_log_credentials_response_bodies_or_connection_urls(monkeypatch, caplog):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", KEY)
    private_text = "private-body postgresql://private-credential@private-host/db " + KEY
    with patch.object(probe, "_request_json", side_effect=ValueError(private_text)):
        assert probe.run_probe(startup_attempts=1) is False
    assert "status=FAIL" in caplog.text
    assert KEY not in caplog.text
    assert private_text not in caplog.text


def test_wrong_service_never_launches_probe(monkeypatch):
    monkeypatch.setenv("RENDER_SERVICE_ID", "production-or-other-service")
    with patch.object(probe.threading, "Thread") as thread:
        probe.launch_if_isolated_review()
        thread.assert_not_called()
