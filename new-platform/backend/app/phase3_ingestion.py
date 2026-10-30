"""Resumable, provenance-backed ClinicalTrials.gov Phase 3 results discovery.

Only Phase 3 library tables are written. Archive payloads, scientific dossiers,
assessment scores and trading controls are never modified by this module.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

LOG = logging.getLogger(__name__)
SCOPE_ID = "ctgov-phase3-posted-results-v1"
SCOPE_QUERY = "AREA[Phase]PHASE3 AND AREA[HasResults]true"
API = "https://clinicaltrials.gov/api/v2/studies"
NCT = re.compile(r"NCT[0-9]{8}\Z")
PAGE_SIZE = 100
MAX_PAGE_BYTES = 32 * 1024 * 1024
SYNC_INTERVAL_SECONDS = 86400
LOCK_KEY = 72403507131
_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="phase3-ingest")
_active = set()
_started = set()
_thread_lock = threading.Lock()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def sha256(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def initialize(engine):
    """Add separate ingestion metadata; never change an existing archive table."""
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS phase3_ingestion_state (
            scope_id TEXT PRIMARY KEY, document TEXT NOT NULL)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS phase3_ingestion_history (
            event_id TEXT PRIMARY KEY, sync_id TEXT NOT NULL, occurred_at TEXT NOT NULL,
            kind TEXT NOT NULL, document TEXT NOT NULL)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS phase3_ingestion_seen (
            sync_id TEXT NOT NULL, nct_id TEXT NOT NULL, imported INTEGER NOT NULL,
            rejection_code TEXT, PRIMARY KEY(sync_id,nct_id))"""))
        c.execute(text("CREATE INDEX IF NOT EXISTS phase3_ingestion_history_sync ON phase3_ingestion_history(sync_id,occurred_at)"))
        c.execute(text("INSERT INTO phase3_ingestion_state(scope_id,document) VALUES(:scope,:doc) ON CONFLICT(scope_id) DO NOTHING"),
                  {"scope": SCOPE_ID, "doc": canonical(_initial())})


def _initial():
    return {"scope_id": SCOPE_ID, "source": "ClinicalTrials.gov API v2", "query": SCOPE_QUERY,
            "state": "PENDING", "sync_id": None, "next_page_token": None,
            "pages_completed": 0, "records_seen": 0, "records_imported": 0,
            "records_rejected": 0, "expected_total": None, "last_updated": None,
            "last_completed_at": None, "last_success_at": None, "next_sync_after": None,
            "next_retry_at": None, "error_code": None, "last_automatic_execution_at": None}


def _state(engine):
    with engine.connect() as c:
        raw = c.execute(text("SELECT document FROM phase3_ingestion_state WHERE scope_id=:scope"), {"scope": SCOPE_ID}).scalar()
    return json.loads(raw) if raw else _initial()


def _save(engine, state, kind=None, details=None):
    state["last_updated"] = stamp()
    with engine.begin() as c:
        c.execute(text("UPDATE phase3_ingestion_state SET document=:doc WHERE scope_id=:scope"),
                  {"doc": canonical(state), "scope": SCOPE_ID})
        if kind:
            c.execute(text("INSERT INTO phase3_ingestion_history(event_id,sync_id,occurred_at,kind,document) VALUES(:id,:sync,:at,:kind,:doc)"),
                      {"id": str(uuid.uuid4()), "sync": state["sync_id"] or "not-started", "at": stamp(),
                       "kind": kind, "doc": canonical(details or {})})


def status(engine):
    state = _state(engine)
    safe = {key: value for key, value in state.items() if key != "next_page_token"}
    safe["next_page_pending"] = bool(state.get("next_page_token"))
    safe["source_health"] = {"clinicaltrials": {
        "status": "REVIEW_REQUIRED" if state["state"] == "REVIEW_REQUIRED" else "ERROR" if state.get("error_code") else "VERIFIED" if state.get("last_success_at") else "PENDING",
        "last_success_at": state.get("last_success_at"), "last_error_code": state.get("error_code")}}
    safe["scheduling"] = {"mechanism": "in_process_daily_with_persisted_checkpoint",
                          "interval_seconds": SYNC_INTERVAL_SECONDS,
                          "last_automatic_execution_at": state.get("last_automatic_execution_at"),
                          "next_due_at": state.get("next_sync_after"),
                          "verified_execution": bool(state.get("last_automatic_execution_at"))}
    return safe


@contextmanager
def _exclusive(engine):
    """Bound a page batch to one process/instance without database IP changes."""
    if not _lock.acquire(blocking=False):
        yield False
        return
    connection = None
    locked = False
    try:
        if engine.dialect.name == "postgresql":
            connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
            locked = bool(connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}).scalar())
            if not locked:
                yield False
                return
        yield True
    finally:
        if connection is not None:
            if locked:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
            connection.close()
        _lock.release()


def fetch_page(page_token=None):
    params = {"format": "json", "filter.advanced": SCOPE_QUERY, "pageSize": PAGE_SIZE, "countTotal": "true"}
    if page_token:
        params["pageToken"] = page_token
    url = API + "?" + urlencode(params)
    last_code = "SOURCE_UNAVAILABLE"
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"Accept": "application/json", "User-Agent": "PDUFA-Phase3-Library/1.0"}), timeout=30) as response:
                if response.status != 200 or "json" not in response.headers.get("Content-Type", "").lower():
                    raise ValueError("SOURCE_NOT_JSON")
                raw = response.read(MAX_PAGE_BYTES + 1)
            if len(raw) > MAX_PAGE_BYTES:
                raise ValueError("SOURCE_PAGE_TOO_LARGE")
            document = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("SOURCE_INVALID_JSON")))
            if not isinstance(document, dict) or not isinstance(document.get("studies"), list):
                raise ValueError("SOURCE_INVALID_PAGE")
            return document, {"url": url, "sha256": hashlib.sha256(raw).hexdigest(),
                              "retrieved_at": stamp(), "http_status": 200, "verification_status": "VERIFIED"}
        except HTTPError as exc:
            last_code = "SOURCE_HTTP_" + str(exc.code)
            if exc.code not in {408, 429, 500, 502, 503, 504}:
                break
        except (URLError, TimeoutError, OSError):
            last_code = "SOURCE_CONNECTION_FAILURE"
        if attempt < 2:
            time.sleep(1 + attempt)
    raise RuntimeError(last_code)


def normalize_study(study, page_proof):
    """Keep posted values distinct from statistical/clinical interpretation."""
    if not isinstance(study, dict):
        raise ValueError("INVALID_STUDY")
    protocol = study.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    nct = identification.get("nctId")
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        raise ValueError("INVALID_NCT")
    design = protocol.get("designModule") or {}
    phases = design.get("phases") or []
    if "PHASE3" not in phases:
        raise ValueError("NOT_PHASE3")
    results = study.get("resultsSection")
    if study.get("hasResults") is not True or not isinstance(results, dict) or not results:
        raise ValueError("NO_POSTED_RESULTS")
    sponsor = (protocol.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}
    company = sponsor.get("name")
    title = identification.get("officialTitle") or identification.get("briefTitle")
    if not isinstance(company, str) or not company.strip() or not isinstance(title, str) or not title.strip():
        raise ValueError("MISSING_TRIAL_IDENTITY")
    status_module = protocol.get("statusModule") or {}
    interventions = (protocol.get("armsInterventionsModule") or {}).get("interventions") or []
    products = sorted({item["name"].strip() for item in interventions if isinstance(item, dict)
                       and item.get("type") in {"DRUG", "BIOLOGICAL", "COMBINATION_PRODUCT"}
                       and isinstance(item.get("name"), str) and item["name"].strip()})
    conditions = (protocol.get("conditionsModule") or {}).get("conditions") or []
    outcomes = (results.get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []
    primary = []
    for item in outcomes:
        if not isinstance(item, dict) or item.get("type") != "PRIMARY":
            continue
        primary.append({key: item[key] for key in ("type", "title", "description", "timeFrame", "paramType", "dispersionType",
                                                   "unitOfMeasure", "groups", "classes", "analyses", "denoms", "typeUnitsAnalyzed") if key in item})
    completion = (status_module.get("completionDateStruct") or {}).get("date")
    proof = {"url": API + "/" + nct, "sha256": sha256(study), "retrieved_at": page_proof["retrieved_at"],
             "verification_status": "VERIFIED", "hash_scope": "canonical-study-json", "discovery_url": page_proof["url"],
             "discovery_page_sha256": page_proof["sha256"]}
    return {"nct_id": nct, "company": company.strip(), "ticker": None, "drug": products,
            "indication": conditions, "trial_title": title.strip(), "status": status_module.get("overallStatus", "UNKNOWN"),
            "phases": phases, "has_results": True, "results_available": True, "completion_date": completion,
            "primary_endpoint_result": {"status": "POSTED" if primary else "NOT_REPORTED", "outcomes": primary,
                                        "interpretation": "Posted trial values; endpoint success and clinical meaning have not been independently adjudicated."},
            "source": proof, "source_url": proof["url"], "sha256": proof["sha256"],
            "verified_at": proof["retrieved_at"], "document": study}


def _upsert_trial(engine, record):
    from . import phase3_catalog
    return phase3_catalog.upsert_trial(engine, record)


def _counts(engine, sync_id):
    with engine.connect() as c:
        row = c.execute(text("SELECT COUNT(*),COALESCE(SUM(imported),0) FROM phase3_ingestion_seen WHERE sync_id=:sync"), {"sync": sync_id}).first()
    return int(row[0]), int(row[1])


def _mark_seen(engine, sync_id, nct, imported, code=None):
    with engine.begin() as c:
        previous = c.execute(text("SELECT imported FROM phase3_ingestion_seen WHERE sync_id=:sync AND nct_id=:nct"),
                             {"sync": sync_id, "nct": nct}).scalar()
        c.execute(text("""INSERT INTO phase3_ingestion_seen(sync_id,nct_id,imported,rejection_code)
            VALUES(:sync,:nct,:imported,:code) ON CONFLICT(sync_id,nct_id) DO UPDATE
            SET imported=excluded.imported,rejection_code=excluded.rejection_code"""),
                  {"sync": sync_id, "nct": nct, "imported": int(imported), "code": code})
    return previous


def sync(engine, max_pages=3, *, automatic=False, fetcher=None):
    """Process bounded pages; checkpoint only after every page record is handled."""
    if not isinstance(max_pages, int) or not 1 <= max_pages <= 20:
        raise ValueError("max_pages must be between 1 and 20")
    initialize(engine)
    fetcher = fetcher or fetch_page
    with _exclusive(engine) as acquired:
        if not acquired:
            return {**status(engine), "worker_busy": True}
        state = _state(engine)
        now = datetime.now(timezone.utc)
        if state["state"] in {"COMPLETE", "REVIEW_REQUIRED"}:
            due = state.get("next_sync_after")
            if due and datetime.fromisoformat(due) > now:
                return status(engine)
            previous_complete = state.get("last_completed_at")
            previous_automatic = state.get("last_automatic_execution_at")
            state = _initial()
            state["last_completed_at"] = previous_complete
            state["last_automatic_execution_at"] = previous_automatic
        if not state.get("sync_id"):
            state["sync_id"] = str(uuid.uuid4())
        seen, imported = _counts(engine, state["sync_id"])
        state.update(records_seen=seen, records_imported=imported, records_rejected=seen-imported)
        state["state"] = "LOADING"
        state["error_code"] = None
        state["next_retry_at"] = None
        _save(engine, state, "SYNC_STARTED", {"automatic": automatic, "query": SCOPE_QUERY})
        try:
            for _ in range(max_pages):
                page, proof = fetcher(state.get("next_page_token"))
                if automatic:
                    state["last_automatic_execution_at"] = proof["retrieved_at"]
                expected = page.get("totalCount")
                if state["expected_total"] is None and isinstance(expected, int) and expected >= 0:
                    state["expected_total"] = expected
                studies = page["studies"]
                for index, study in enumerate(studies):
                    raw_nct = ((study.get("protocolSection") or {}).get("identificationModule") or {}).get("nctId") if isinstance(study, dict) else None
                    identifier = raw_nct if isinstance(raw_nct, str) and NCT.fullmatch(raw_nct) else "INVALID:" + sha256(study)[:24]
                    try:
                        record = normalize_study(study, proof)
                        _upsert_trial(engine, record)
                    except ValueError as exc:
                        code = str(exc) if re.fullmatch(r"[A-Z0-9_]{1,80}", str(exc)) else "TRIAL_VALIDATION_FAILED"
                        previous = _mark_seen(engine, state["sync_id"], identifier, False, code)
                        imported_record = 0
                    else:
                        previous = _mark_seen(engine, state["sync_id"], identifier, True)
                        imported_record = 1
                    if previous is None:
                        state["records_seen"] += 1
                        state["records_imported"] += imported_record
                    else:
                        state["records_imported"] += imported_record - int(previous)
                    state["records_rejected"] = state["records_seen"] - state["records_imported"]
                    if (index + 1) % 10 == 0:
                        _save(engine, state)
                next_token = page.get("nextPageToken")
                if next_token is not None and (not isinstance(next_token, str) or not next_token or next_token == state.get("next_page_token")):
                    raise ValueError("INVALID_SOURCE_CHECKPOINT")
                if not studies and next_token:
                    raise ValueError("EMPTY_SOURCE_PAGE_WITH_CHECKPOINT")
                state["pages_completed"] += 1
                seen, imported = _counts(engine, state["sync_id"])
                state.update(records_seen=seen, records_imported=imported, records_rejected=seen-imported)
                state["last_success_at"] = proof["retrieved_at"]
                state["next_page_token"] = next_token
                if not next_token:
                    reconciled = state["expected_total"] is not None and state["records_seen"] == state["expected_total"] and state["records_rejected"] == 0
                    state["state"] = "COMPLETE" if reconciled else "REVIEW_REQUIRED"
                    state["last_completed_at"] = stamp()
                    state["next_sync_after"] = (datetime.now(timezone.utc) + timedelta(seconds=SYNC_INTERVAL_SECONDS)).isoformat()
                    state["error_code"] = None if reconciled else "SCOPE_RECONCILIATION_REQUIRED"
                _save(engine, state, "PAGE_COMPLETED", {"source": proof, "records_on_page": len(studies),
                                                       "pages_completed": state["pages_completed"], "state": state["state"]})
                LOG.info("PDUFA_PHASE3_INGESTION_PROGRESS %s", canonical({key: state[key] for key in ("sync_id", "state", "pages_completed", "records_seen", "records_imported", "records_rejected", "expected_total")}))
                if not next_token:
                    LOG.info("PDUFA_PHASE3_INGESTION_RESULT %s", canonical(status(engine)))
                    break
            if state["state"] == "LOADING":
                state["state"] = "PAUSED"
                _save(engine, state)
        except Exception as exc:
            code = str(exc) if re.fullmatch(r"[A-Z0-9_]{1,80}", str(exc)) else "INGESTION_EXECUTION_FAILED"
            state.update(state="FAILED", error_code=code,
                         next_retry_at=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat())
            _save(engine, state, "SYNC_FAILED", {"error_code": code, "exception_type": type(exc).__name__})
            LOG.error("PDUFA_PHASE3_INGESTION_FAILED %s", canonical({"sync_id": state["sync_id"], "error_code": code, "exception_type": type(exc).__name__}))
        return status(engine)


def _run(engine, automatic):
    try:
        while True:
            report = sync(engine, max_pages=3, automatic=automatic)
            if report.get("worker_busy"):
                break
            if report["state"] not in {"PENDING", "PAUSED", "LOADING"}:
                break
            time.sleep(0.25)
    finally:
        with _thread_lock:
            _active.discard(id(engine))


def trigger(engine, *, automatic=False):
    initialize(engine)
    with _thread_lock:
        if id(engine) not in _active:
            _active.add(id(engine))
            _pool.submit(_run, engine, automatic)
    return status(engine)


def start(engine):
    """Install a new library-only daily/resume schedule; do not change old scans."""
    initialize(engine)
    if engine.dialect.name != "postgresql":
        return
    with _thread_lock:
        if id(engine) in _started:
            return
        _started.add(id(engine))

    def scheduled():
        while True:
            try:
                state = _state(engine)
                now = datetime.now(timezone.utc)
                wait_until = state.get("next_retry_at") if state["state"] == "FAILED" else state.get("next_sync_after")
                if not wait_until or datetime.fromisoformat(wait_until) <= now:
                    trigger(engine, automatic=True)
            except Exception as exc:
                LOG.error("PDUFA_PHASE3_SCHEDULER_ERROR %s", type(exc).__name__)
            time.sleep(60)

    threading.Thread(target=scheduled, name="phase3-daily-sync", daemon=True).start()


def install_routes(app, engine_provider, require_internal_key, require_storage):
    router = APIRouter(prefix="/api/phase3-trials", dependencies=[Depends(require_internal_key), Depends(require_storage)])

    @router.post("/sync", status_code=202)
    def sync_phase3_catalog():
        engine = engine_provider()
        if engine is None:
            raise HTTPException(503, "Phase 3 catalog storage unavailable")
        return trigger(engine)

    @router.get("/ingestion")
    def get_ingestion_status():
        return status(engine_provider())

    app.include_router(router)
