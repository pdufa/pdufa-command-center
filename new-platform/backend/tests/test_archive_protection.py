"""Archive protection integration tests use disposable SQLite records only."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DatabaseError

from app import archive_protection as protection


def record(nct="NCT00000001", *, title="Example", raw=None):
    raw = raw if raw is not None else json.dumps({"protocolSection": {"identificationModule": {"nctId": nct, "briefTitle": title}}}, sort_keys=True).encode()
    return {"nct": nct, "packed": gzip.compress(raw), "checksum": hashlib.sha256(raw).hexdigest()}


@pytest.fixture
def engine(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "archive.sqlite3"), connect_args={"check_same_thread": False})
    with engine.begin() as c:
        # No primary key here: the audit must detect unexpected physical duplicates.
        c.execute(text("CREATE TABLE full_trial_records (nct_id TEXT, payload_gzip BLOB, sha256 TEXT)"))
        c.execute(text("CREATE TABLE full_trial_download (id INTEGER PRIMARY KEY, status TEXT, scope_ids JSON, completed_ids JSON, completed_at TEXT)"))
        c.execute(text("INSERT INTO full_trial_records VALUES (:nct, :packed, :checksum)"), [record("NCT00000001"), record("NCT00000002")])
        c.execute(text("INSERT INTO full_trial_download VALUES (1, 'COMPLETE', :scope, :scope, '2026-10-01T00:00:00+00:00')"), {"scope": json.dumps(["NCT00000001", "NCT00000002"])})
    protection.initialize(engine)
    yield engine
    engine.dispose()


def collect(engine, expected=2):
    c = protection.read_connection(engine)
    try:
        return protection.collect(c, expected_count=expected)
    finally:
        protection.close_read(c)


def test_manifest_canonicalization_and_checksum_detection(engine):
    data = collect(engine)
    assert data["integrity_passed"]
    manifest = protection.make_manifest(data, "2026-10-30T13:00:00+00:00")
    checksum = protection.digest(manifest)
    assert protection.canonical({"z": 1, "a": {"b": 2, "a": "é"}}) == protection.canonical({"a": {"a": "é", "b": 2}, "z": 1})
    assert protection.check_manifest(manifest, checksum, data)
    assert [r["nct_id"] for r in manifest["records"]] == manifest["expected_nct_ids"]
    tampered = deepcopy(manifest)
    tampered["records"][0]["sha256"] = "0" * 64
    assert not protection.check_manifest(tampered, checksum, data)
    assert not protection.check_manifest(manifest, "0" * 64, data)
    with pytest.raises(ValueError):
        protection.canonical({"invalid": float("nan")})


@pytest.mark.parametrize("kind,category", [("gzip", "bad_gzip"), ("json", "invalid_json"), ("hash", "bad_sha256"), ("internal_id", "payload_id_mismatch"), ("nct_id", "invalid_ids"), ("nonstandard_json", "invalid_json")])
def test_payload_error_categories(kind, category):
    item = record()
    if kind == "gzip":
        item["packed"] = b"not gzip"
    elif kind == "json":
        item = record(raw=b"not JSON")
    elif kind == "nonstandard_json":
        item = record(raw=b'{"nonstandard": NaN}')
    elif kind == "hash":
        item["checksum"] = "0" * 64
    elif kind == "internal_id":
        item["nct"] = "NCT00000002"
    elif kind == "nct_id":
        item = record("NCT１２３４５６７８")
    errors, _ = protection.inspect_payload(item["nct"], item["packed"], item["checksum"])
    assert errors[category] == 1


def test_missing_expected_and_tracking_records(engine):
    with engine.begin() as c:
        c.execute(text("DELETE FROM full_trial_records WHERE nct_id='NCT00000002'"))
    data = collect(engine)
    assert not data["integrity_passed"]
    assert data["totals"]["physical_records"] == 1
    assert data["totals"]["missing_expected_records"] == 1
    assert data["totals"]["tracking_missing_records"] == 1


def test_duplicate_identifier_is_not_hidden_by_distinct_or_manifest(engine):
    with engine.begin() as c:
        c.execute(text("INSERT INTO full_trial_records VALUES (:nct, :packed, :checksum)"), record())
    data = collect(engine)
    assert not data["integrity_passed"]
    assert data["totals"]["rows"] == 3
    assert data["totals"]["duplicate_ids"] == 1


def test_additional_record_and_incomplete_tracking_require_review(engine):
    with engine.begin() as c:
        c.execute(text("INSERT INTO full_trial_records VALUES (:nct, :packed, :checksum)"), record("NCT00000003"))
        c.execute(text("UPDATE full_trial_download SET status='PARTIAL'"))
    data = collect(engine)
    assert not data["integrity_passed"]
    assert data["totals"]["unexpected_records"] == 1


def test_payload_reads_are_bounded_and_progress_is_logged(engine, caplog, monkeypatch):
    ids = ["NCT" + str(n).zfill(8) for n in range(1, 1003)]
    with engine.begin() as c:
        c.execute(text("DELETE FROM full_trial_records"))
        c.execute(text("INSERT INTO full_trial_records VALUES (:nct, :packed, :checksum)"), [record(nct) for nct in ids])
        c.execute(text("UPDATE full_trial_download SET scope_ids=:scope, completed_ids=:scope"), {"scope": json.dumps(ids)})
    batches = []
    def observe(conn, cursor, statement, parameters, context, executemany):
        if "SELECT nct_id, payload_gzip" in statement:
            assert "LIMIT" in statement and "OFFSET" in statement
            batches.append(parameters[0])
    event.listen(engine, "before_cursor_execute", observe)
    try:
        data = collect(engine, expected=len(ids))
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert data["integrity_passed"]
    assert len(batches) >= 11
    assert all(limit <= protection.BATCH_SIZE for limit in batches)
    assert "PDUFA_ARCHIVE_INTEGRITY_PROGRESS rows=1000" in caplog.text


def test_sqlite_reads_reject_writes_and_return_clean_connection(engine):
    c = protection.read_connection(engine)
    try:
        assert c.execute(text("PRAGMA query_only")).scalar_one() == 1
        with pytest.raises(DatabaseError, match="readonly"):
            c.execute(text("DELETE FROM full_trial_records"))
    finally:
        protection.close_read(c)
    with engine.begin() as writable:
        assert writable.execute(text("PRAGMA query_only")).scalar_one() == 0
        writable.execute(text("INSERT INTO full_trial_records VALUES (:nct, :packed, :checksum)"), record("NCT00000003"))


def test_existing_manifest_cannot_be_replaced_after_record_change(engine):
    first = protection.execute_run(engine, "manual:baseline", expected_count=2)
    assert first["status"] == "PASS"
    with engine.connect() as c:
        baseline = c.execute(text("SELECT document, sha256 FROM archive_manifests")).one()
    with engine.begin() as c:
        changed = record("NCT00000001", title="Updated source payload")
        c.execute(text("UPDATE full_trial_records SET payload_gzip=:packed, sha256=:checksum WHERE nct_id=:nct"), changed)
    second = protection.execute_run(engine, "manual:changed", expected_count=2)
    assert second["archive_integrity"] == "PASS"
    assert second["manifest_verification"] == "REVIEW_REQUIRED"
    assert second["status"] == "REVIEW_REQUIRED"
    with engine.connect() as c:
        assert c.execute(text("SELECT document, sha256 FROM archive_manifests")).one() == baseline
        assert c.execute(text("SELECT count(*) FROM archive_verification_runs")).scalar_one() == 2
    for sql in ("UPDATE archive_manifests SET document='{}'", "DELETE FROM archive_manifests", "UPDATE archive_verification_runs SET summary='{}'", "DELETE FROM archive_verification_runs"):
        with pytest.raises(DatabaseError, match="append-only"):
            with engine.begin() as c:
                c.execute(text(sql))


def test_failed_first_run_never_creates_a_baseline(engine):
    with engine.begin() as c:
        c.execute(text("UPDATE full_trial_records SET sha256=:bad WHERE nct_id='NCT00000001'"), {"bad": "0" * 64})
    result = protection.execute_run(engine, "manual:invalid", expected_count=2)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["totals"]["bad_sha256"] == 1
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM archive_manifests")).scalar_one() == 0
        assert c.execute(text("SELECT count(*) FROM full_trial_records")).scalar_one() == 2


@pytest.mark.parametrize("utc,due,next_at", [
    ("2026-10-31T02:59:59+00:00", "2026-10-29", "2026-10-30T20:00:00-07:00"),
    ("2026-10-31T03:00:00+00:00", "2026-10-30", "2026-10-31T20:00:00-07:00"),
    ("2026-11-02T04:00:00+00:00", "2026-11-01", "2026-11-02T20:00:00-08:00"),
    ("2026-03-09T03:00:00+00:00", "2026-03-08", "2026-03-09T20:00:00-07:00"),
])
def test_daily_20_pacific_schedule_with_dst(utc, due, next_at):
    assert protection.schedule_times(datetime.fromisoformat(utc)) == (due, next_at)


def test_unique_schedule_slot_and_local_overlap_guard(engine):
    assert protection.execute_run(engine, "daily:2026-10-30", expected_count=2)["status"] == "PASS"
    assert protection.execute_run(engine, "daily:2026-10-30", expected_count=2)["status"] == "ALREADY_VERIFIED_SLOT"
    protection._local_lock.acquire()
    try:
        assert protection.execute_run(engine, "daily:2026-10-31", expected_count=2)["status"] == "SKIPPED_OVERLAP"
    finally:
        protection._local_lock.release()
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM archive_verification_runs")).scalar_one() == 1


def test_dashboard_and_actual_route_auth_contract(engine, monkeypatch):
    summary = protection.execute_run(engine, "manual:dashboard", expected_count=2)
    monkeypatch.setattr(protection, "schedule_times", lambda: ("2020-01-01", "2030-01-01T20:00:00-08:00"))
    # Compile the actual endpoint and authentication dependency from main.py,
    # avoiding unrelated application startup, scanners and external I/O.
    source = Path(protection.__file__).with_name("main.py")
    syntax = ast.parse(source.read_text())
    wanted = {"require_internal_key", "archive_health"}
    extracted = ast.Module(body=[node for node in syntax.body if isinstance(node, ast.FunctionDef) and node.name in wanted], type_ignores=[])
    app = FastAPI()
    context = {"__name__": "app.archive_route_test", "__package__": "app", "app": app, "ENGINE": engine,
               "Depends": Depends, "Header": Header, "Annotated": Annotated, "HTTPException": HTTPException,
               "os": os, "secrets": secrets, "require_storage": lambda: None}
    exec(compile(extracted, str(source), "exec"), context)
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-archive-health-only")
    with pytest.raises(HTTPException) as unauthorized:
        context["require_internal_key"]()
    assert unauthorized.value.status_code == 401
    context["require_internal_key"]("test-archive-health-only")
    response = JSONResponse(jsonable_encoder(context["archive_health"]()))
    assert response.status_code == 200
    dashboard = json.loads(response.body)
    route = next(route for route in app.routes if route.path == "/api/archive-health")
    assert route.methods == {"GET"}
    assert len(route.dependencies) == 2
    assert dashboard["status"] == "PASS"
    assert dashboard["archive_integrity"] == "PASS"
    assert dashboard["manifest_verification"] == "PASS"
    assert dashboard["archived_trials"] == 2
    assert dashboard["scientific_ready_trials"] == 0
    assert dashboard["trials_needing_additional_evidence"] == 2
    assert dashboard["trials_with_regulatory_outcome_evidence"] == 0
    assert dashboard["trade_authorized"] is False
    assert all(value["present"] + value["missing"] == 2 for value in dashboard["inventory"].values())
    assert dashboard["scheduler"]["local_time"] == "20:00"
    assert dashboard["last_verified"] == summary["last_verified"]


def test_dashboard_marks_overdue_success_for_review(engine, monkeypatch):
    protection.execute_run(engine, "manual:old", expected_count=2)
    monkeypatch.setattr(protection, "schedule_times", lambda: ("2099-01-01", "2099-01-02T20:00:00-08:00"))
    result = protection.dashboard(engine)
    assert result["verification_overdue"] is True
    assert result["archive_integrity"] == "REVIEW_REQUIRED"
    assert result["manifest_verification"] == "REVIEW_REQUIRED"
