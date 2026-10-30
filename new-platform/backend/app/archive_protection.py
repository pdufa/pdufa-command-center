"""Versioned archive evidence. Payload reads never share a writable transaction.

Only two new metadata tables are written. Existing manifests/runs reject UPDATE,
DELETE and TRUNCATE in PostgreSQL. A database owner can deliberately change DDL;
this is append-only application protection, not administrator-proof WORM storage.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import text

from .archive_readiness import INVENTORY_FLAGS, READINESS_DEFINITIONS, study_readiness

LOG = logging.getLogger(__name__)
VERSION = "pdufa-archive-audit-v2"
ARCHIVE_ID = "pdufa-ctgov-saved-scope-11622-v1"
EXPECTED = 11622
BATCH_SIZE = 100
LOCK_ID = 116220820
PACIFIC = ZoneInfo("America/Los_Angeles")
_local_lock = threading.Lock()
_scheduler_lock = threading.Lock()
_stop = threading.Event()
_thread = None


def canonical(document):
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(document):
    return hashlib.sha256(canonical(document).encode("utf-8")).hexdigest()


def schedule_times(now=None):
    """Latest due local date and next 20:00; zoneinfo handles both DST changes."""
    now = (now or datetime.now(timezone.utc)).astimezone(PACIFIC)
    target = datetime.combine(now.date(), datetime.min.time(), PACIFIC).replace(hour=20)
    due = target if now >= target else target - timedelta(days=1)
    upcoming = target + timedelta(days=1) if now >= target else target
    return due.date().isoformat(), upcoming.isoformat()


def initialize(engine):
    """Idempotent additive migration, isolated to archive metadata."""
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS archive_manifests (
            archive_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
            document TEXT NOT NULL, sha256 VARCHAR(64) UNIQUE NOT NULL,
            CHECK (length(sha256) = 64))"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS archive_verification_runs (
            run_id TEXT PRIMARY KEY, schedule_key TEXT UNIQUE NOT NULL,
            finished_at TEXT NOT NULL, summary TEXT NOT NULL)"""))
        if engine.dialect.name == "postgresql":
            c.execute(text("""CREATE OR REPLACE FUNCTION archive_metadata_append_only()
                RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
                RAISE EXCEPTION 'archive metadata is append-only'; END; $$"""))
            for table in ("archive_manifests", "archive_verification_runs"):
                exists = c.execute(text("SELECT 1 FROM pg_trigger WHERE tgname=:name AND tgrelid=CAST(:table AS regclass)"),
                                   {"name": table + "_immutable", "table": table}).scalar()
                if not exists:
                    c.execute(text(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION archive_metadata_append_only()"))
                c.execute(text(f"REVOKE ALL ON {table} FROM PUBLIC"))
        else:
            for table in ("archive_manifests", "archive_verification_runs"):
                for operation in ("UPDATE", "DELETE"):
                    c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'archive metadata is append-only'); END"))


def read_connection(engine):
    c = engine.connect()
    try:
        if engine.dialect.name == "postgresql":
            c.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            c.execute(text("SET LOCAL statement_timeout = '30s'"))
        else:
            c.execute(text("PRAGMA query_only = ON"))
        return c
    except BaseException:
        c.close()
        raise


def close_read(c):
    c.rollback()
    if c.dialect.name == "sqlite":
        c.execute(text("PRAGMA query_only = OFF"))
        c.rollback()
    c.close()


def inspect_payload(nct, packed, expected_hash):
    errors = {"invalid_ids": int(not isinstance(nct, str) or not re.fullmatch(r"NCT[0-9]{8}", nct)),
              "bad_gzip": 0, "invalid_json": 0, "bad_sha256": 0, "payload_id_mismatch": 0}
    try:
        raw = gzip.decompress(packed)
    except Exception:
        errors["bad_gzip"] = 1
        return errors, None
    errors["bad_sha256"] = int(hashlib.sha256(raw).hexdigest() != expected_hash)
    try:
        study = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (ValueError, UnicodeError):
        errors["invalid_json"] = 1
        return errors, None
    try:
        internal = study["protocolSection"]["identificationModule"]["nctId"]
    except (KeyError, TypeError):
        internal = None
    errors["payload_id_mismatch"] = int(internal != nct)
    return errors, study if isinstance(study, dict) else None


def collect(c, expected_count=EXPECTED):
    database = c.execute(text("SELECT current_database()")).scalar_one() if c.dialect.name == "postgresql" else "sqlite_test"
    jobs = [dict(r) for r in c.execute(text("SELECT id, status, scope_ids, completed_ids, completed_at FROM full_trial_download ORDER BY id")).mappings()]
    for job in jobs:
        for field in ("scope_ids", "completed_ids"):
            if isinstance(job[field], str):
                job[field] = json.loads(job[field])
    scope = {n for job in jobs for n in job["scope_ids"]}
    totals = {k: 0 for k in ("rows", "valid_ids", "invalid_ids", "duplicate_ids", "bad_gzip", "invalid_json", "bad_sha256", "payload_id_mismatch")}
    inventory = {k: {"present": 0, "missing": 0} for k in INVENTORY_FLAGS}
    entries, seen = [], set()
    ready = outcomes = 0
    physical = c.execute(text("SELECT count(*) FROM full_trial_records")).scalar_one()
    duplicate = c.execute(text("SELECT count(*) - count(DISTINCT nct_id) FROM full_trial_records")).scalar_one()
    offset = 0
    while True:
        rows = c.execute(text("SELECT nct_id, payload_gzip, sha256 FROM full_trial_records ORDER BY nct_id LIMIT :limit OFFSET :offset"),
                         {"limit": BATCH_SIZE, "offset": offset}).all()
        if not rows:
            break
        for nct, packed, checksum in rows:
            errors, study = inspect_payload(nct, packed, checksum)
            for key, count in errors.items():
                totals[key] += count
            totals["rows"] += 1
            totals["valid_ids"] += int(not errors["invalid_ids"])
            totals["duplicate_ids"] += int(nct in seen)
            seen.add(nct)
            entries.append({"nct_id": nct, "sha256": checksum})
            flags = study_readiness(study) if study is not None and not any(errors.values()) else {}
            for key in inventory:
                inventory[key]["present" if flags.get(key, False) else "missing"] += 1
            ready += int(flags.get("scientific_ready", False))
            outcomes += int(flags.get("regulatory_outcome_evidence", False))
            if totals["rows"] % 1000 == 0:
                LOG.warning("PDUFA_ARCHIVE_INTEGRITY_PROGRESS rows=%d audit_version=%s", totals["rows"], VERSION)
        offset += len(rows)
    completed = {n for job in jobs for n in job["completed_ids"]}
    totals.update(physical_records=physical, expected_scope_records=len(scope),
                  missing_expected_records=len(scope - seen), unexpected_records=len(seen - scope),
                  tracking_missing_records=len(completed - seen))
    passed = (physical == expected_count == totals["rows"] == len(scope)
              and bool(jobs) and all(j["status"] == "COMPLETE" for j in jobs)
              and completed == scope
              and duplicate == totals["duplicate_ids"] == 0
              and all(totals[k] == 0 for k in ("invalid_ids", "bad_gzip", "invalid_json", "bad_sha256", "payload_id_mismatch", "missing_expected_records", "unexpected_records", "tracking_missing_records")))
    return {"database": database, "totals": totals, "integrity_passed": passed,
            "entries": entries, "expected_nct_ids": sorted(scope), "jobs": jobs,
            "inventory": inventory, "scientific_ready_trials": ready,
            "trials_needing_additional_evidence": totals["rows"] - ready,
            "trials_with_regulatory_outcome_evidence": outcomes}


def make_manifest(data, timestamp):
    return {"archive_id": ARCHIVE_ID, "created_at": timestamp,
            "source": "ClinicalTrials.gov API v2 full study JSON",
            "download_scope": "Saved full_trial_download.scope_ids (not all ClinicalTrials.gov)",
            "expected_nct_ids": data["expected_nct_ids"], "records": data["entries"],
            "total_expected_trials": len(data["expected_nct_ids"]),
            "total_downloaded_trials": data["totals"]["rows"],
            "download_completion_status": [j["status"] for j in data["jobs"]],
            "download_completed_at": [str(j["completed_at"]) for j in data["jobs"]],
            "database_identifier": data["database"], "verification_timestamp": timestamp,
            "audit_version": VERSION}


def check_manifest(document, checksum, data):
    return (digest(document) == checksum and document["archive_id"] == ARCHIVE_ID
            and document["database_identifier"] == data["database"]
            and document["records"] == data["entries"]
            and document["expected_nct_ids"] == data["expected_nct_ids"]
            and document["total_downloaded_trials"] == data["totals"]["rows"])


def saved_manifest(engine):
    with engine.connect() as c:
        row = c.execute(text("SELECT document, sha256 FROM archive_manifests WHERE archive_id=:id"), {"id": ARCHIVE_ID}).first()
    if row is None:
        return None
    doc = json.loads(row[0])
    return {"manifest": doc, "manifest_sha256": row[1],
            "canonical_format": "UTF-8 JSON, sorted keys, compact separators, ASCII escaped, no NaN; checksum excludes envelope",
            "checksum_valid": digest(doc) == row[1]}


def execute_run(engine, schedule_key, expected_count=EXPECTED):
    """Advisory lock prevents overlap across workers and rolling deployments."""
    if not _local_lock.acquire(blocking=False):
        return {"status": "SKIPPED_OVERLAP"}
    lock = None
    acquired = False
    try:
        lock = engine.connect()
        if engine.dialect.name == "postgresql":
            acquired = bool(lock.execute(text("SELECT pg_try_advisory_lock(:id)"), {"id": LOCK_ID}).scalar_one())
            lock.commit()
            if not acquired:
                return {"status": "SKIPPED_OVERLAP"}
        if lock.execute(text("SELECT 1 FROM archive_verification_runs WHERE schedule_key=:key"), {"key": schedule_key}).scalar():
            lock.rollback()
            return {"status": "ALREADY_VERIFIED_SLOT"}
        lock.rollback()
        started = datetime.now(timezone.utc).isoformat()
        try:
            c = read_connection(engine)
            try:
                data = collect(c, expected_count)
                baseline = c.execute(text("SELECT document, sha256 FROM archive_manifests WHERE archive_id=:id"), {"id": ARCHIVE_ID}).first()
            finally:
                close_read(c)
            timestamp = datetime.now(timezone.utc).isoformat()
            if baseline is None and data["integrity_passed"]:
                document = make_manifest(data, timestamp)
                checksum = digest(document)
                lock.execute(text("INSERT INTO archive_manifests (archive_id, created_at, document, sha256) VALUES (:id,:time,:doc,:hash)"),
                             {"id": ARCHIVE_ID, "time": timestamp, "doc": canonical(document), "hash": checksum})
                lock.commit()
                baseline = lock.execute(text("SELECT document, sha256 FROM archive_manifests WHERE archive_id=:id"), {"id": ARCHIVE_ID}).one()
                lock.rollback()
                LOG.warning("PDUFA_ARCHIVE_MANIFEST archive_id=%s sha256=%s records=%d status=CREATED", ARCHIVE_ID, checksum, data["totals"]["rows"])
            manifest_ok = baseline is not None and check_manifest(json.loads(baseline[0]), baseline[1], data)
            summary = {k: v for k, v in data.items() if k not in ("entries", "expected_nct_ids", "jobs", "integrity_passed")}
            summary.update(status="PASS" if data["integrity_passed"] and manifest_ok else "REVIEW_REQUIRED",
                           archive_integrity="PASS" if data["integrity_passed"] else "REVIEW_REQUIRED",
                           manifest_verification="PASS" if manifest_ok else "REVIEW_REQUIRED",
                           manifest_sha256=baseline[1] if baseline else None,
                           started_at=started, last_verified=timestamp, audit_version=VERSION,
                           schedule_key=schedule_key, archive_id=ARCHIVE_ID,
                           archive_records_read_only=True, trade_authorized=False)
        except Exception as exc:
            lock.rollback()
            LOG.error("PDUFA_ARCHIVE_PROTECTION_FAILED error_type=%s schedule_key=%s", type(exc).__name__, schedule_key)
            summary = {"status": "REVIEW_REQUIRED", "archive_integrity": "REVIEW_REQUIRED", "manifest_verification": "REVIEW_REQUIRED",
                       "error_type": type(exc).__name__, "started_at": started,
                       "last_verified": datetime.now(timezone.utc).isoformat(), "schedule_key": schedule_key}
        lock.execute(text("INSERT INTO archive_verification_runs (run_id,schedule_key,finished_at,summary) VALUES (:id,:key,:time,:summary)"),
                     {"id": str(uuid.uuid4()), "key": schedule_key, "time": summary["last_verified"], "summary": canonical(summary)})
        lock.commit()
        LOG.warning("PDUFA_ARCHIVE_PROTECTION_RESULT %s", canonical(summary))
        return summary
    finally:
        try:
            if lock is not None:
                try:
                    if acquired:
                        lock.rollback()
                        lock.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": LOCK_ID})
                        lock.commit()
                finally:
                    lock.close()
        finally:
            _local_lock.release()


def dashboard(engine):
    with engine.connect() as c:
        row = c.execute(text("SELECT summary FROM archive_verification_runs ORDER BY finished_at DESC LIMIT 1")).scalar()
    summary = json.loads(row) if row else {}
    due, upcoming = schedule_times()
    # A previous success is not a current success once a scheduled check is overdue.
    stale = summary.get("last_verified", "") < datetime.combine(datetime.fromisoformat(due).date(), datetime.min.time(), PACIFIC).replace(hour=20).astimezone(timezone.utc).isoformat()
    passed = summary.get("status") == "PASS" and not stale
    return {**summary, "archived_trials": summary.get("totals", {}).get("physical_records"),
            "archive_integrity": summary.get("archive_integrity", "REVIEW_REQUIRED") if not stale else "REVIEW_REQUIRED",
            "manifest_verification": summary.get("manifest_verification", "REVIEW_REQUIRED") if not stale else "REVIEW_REQUIRED",
            "status": "PASS" if passed else "REVIEW_REQUIRED", "verification_overdue": stale,
            "last_verified": summary.get("last_verified"), "next_scheduled_verification": upcoming,
            "scientific_ready_trials": summary.get("scientific_ready_trials"),
            "trials_needing_additional_evidence": summary.get("trials_needing_additional_evidence"),
            "trials_with_regulatory_outcome_evidence": summary.get("trials_with_regulatory_outcome_evidence"),
            "inventory": summary.get("inventory", {}), "definitions": READINESS_DEFINITIONS,
            "checks": summary.get("totals", {}),
            "scheduler": {"timezone": "America/Los_Angeles", "local_time": "20:00",
                          "mode": "due-date catch-up; external wake required when service sleeps",
                          "latest_due_date": due, "overlap_prevention": "PostgreSQL advisory lock + unique schedule key",
                          "running_in_this_process": _local_lock.locked()},
            "scientific_readiness_scope": "Evidence screening only; no SCIENCE/OUTCOME/MAIN validation or trading eligibility",
            "trade_authorized": False}


def public_status(engine):
    d = dashboard(engine)
    return {k: d[k] for k in ("status", "archive_integrity", "manifest_verification", "last_verified", "next_scheduled_verification", "verification_overdue", "scheduler")}


def start(engine):
    global _thread
    if engine.dialect.name != "postgresql":
        return
    with _scheduler_lock:
        if _thread is not None and _thread.is_alive():
            return
        _stop.clear()
        def loop():
            try:
                initialize(engine)
                verify_metadata_guards(engine)
                LOG.warning("PDUFA_ARCHIVE_SCHEDULER timezone=America/Los_Angeles local_time=20:00 mode=catch_up next=%s", schedule_times()[1])
                # Verify actual PostgreSQL read-only enforcement without changing a record.
                c = read_connection(engine)
                try:
                    try:
                        c.execute(text("DELETE FROM full_trial_records WHERE false"))
                        raise RuntimeError("Read-only enforcement failed")
                    except Exception as exc:
                        if getattr(getattr(exc, "orig", None), "sqlstate", None) != "25006":
                            raise
                        LOG.warning("PDUFA_ARCHIVE_READ_ONLY_SELFTEST status=PASS sqlstate=25006")
                finally:
                    close_read(c)
                while not _stop.is_set():
                    try:
                        due, _ = schedule_times()
                        summary = execute_run(engine, "daily:" + due)
                        if summary.get("status") in ("PASS", "REVIEW_REQUIRED"):
                            verify_http()
                    except Exception as exc:
                        LOG.error("PDUFA_ARCHIVE_SCHEDULE_ATTEMPT_FAILED error_type=%s", type(exc).__name__)
                    _stop.wait(30)
            except Exception as exc:
                LOG.error("PDUFA_ARCHIVE_SCHEDULER_FAILED error_type=%s", type(exc).__name__)
        _thread = threading.Thread(target=loop, name="archive-protection", daemon=True)
        _thread.start()


def stop():
    _stop.set()


def verify_metadata_guards(engine):
    for table in ("archive_manifests", "archive_verification_runs"):
        with engine.connect() as c:
            try:
                c.execute(text(f"UPDATE {table} SET {('archive_id' if table == 'archive_manifests' else 'run_id')} = 'guard-test' WHERE false"))
                raise RuntimeError("Append-only enforcement failed")
            except Exception as exc:
                if getattr(getattr(exc, "orig", None), "sqlstate", None) != "P0001":
                    raise
                c.rollback()
    LOG.warning("PDUFA_ARCHIVE_APPEND_ONLY_SELFTEST status=PASS tables=2")


def verify_http():
    """Exercise the running authenticated route; log no keys or connection strings."""
    from urllib.request import Request, urlopen
    try:
        req = Request("http://127.0.0.1:8000/api/archive-health", headers={"X-Pdufa-Internal-Key": os.environ["PDUFA_INTERNAL_API_KEY"]})
        with urlopen(req, timeout=15) as response:
            d = json.load(response)
        manifest_req = Request("http://127.0.0.1:8000/api/archive-manifest", headers={"X-Pdufa-Internal-Key": os.environ["PDUFA_INTERNAL_API_KEY"]})
        with urlopen(manifest_req, timeout=15) as response:
            m = json.load(response)
        manifest_valid = (digest(m["manifest"]) == m["manifest_sha256"]
                          and len(m["manifest"]["records"]) == EXPECTED
                          and [r["nct_id"] for r in m["manifest"]["records"]] == m["manifest"]["expected_nct_ids"])
        ok = d["archived_trials"] == EXPECTED and all(v["present"] + v["missing"] == EXPECTED for v in d["inventory"].values())
        LOG.warning("PDUFA_ARCHIVE_HEALTH_HTTP status=%s http=200 archived_trials=%s manifest=%s canonical_checksum=%s", "PASS" if ok and manifest_valid else "FAIL", d["archived_trials"], d["manifest_verification"], "PASS" if manifest_valid else "FAIL")
    except Exception as exc:
        LOG.error("PDUFA_ARCHIVE_HEALTH_HTTP status=FAIL error_type=%s", type(exc).__name__)
