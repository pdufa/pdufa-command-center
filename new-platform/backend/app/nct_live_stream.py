"""Durable, authenticated live NCT evidence collection; no scientific scoring.

Original dossiers and archive records are read-only. Every normalized update is
committed to separate stream metadata before clients can receive it. Reconnects
replay persisted event IDs; they never pretend saved evidence is live retrieval.
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
from datetime import datetime, timezone
from urllib.request import Request as URLRequest, urlopen

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

LOG = logging.getLogger(__name__)
VERSION = "stage1-live-nct-v1"
NCT = re.compile(r"NCT[0-9]{8}\Z")
SAFE_ID = re.compile(r"[A-Za-z0-9_-]{8,100}\Z")
TERMINAL = {"VERIFIED", "FAILED", "INSUFFICIENT_EVIDENCE"}
LEAVES = {
    "trial_identity": ("nct_identifier", "sponsor", "products", "indication", "phase"),
    "trial_design": ("primary_endpoints", "study_completion_status"),
    "clinical_results": ("primary_endpoint_results", "statistical_significance", "clinical_effect_size", "safety_findings", "serious_adverse_events"),
    "regulatory": ("fda_regulatory_pathway", "special_designations", "regulatory_submission_evidence", "pdufa_date"),
}
_write_lock = threading.RLock()
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="nct-live")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def initialize(engine):
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS nct_stream_runs (
            run_id TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL,
            nct_id VARCHAR(11) NOT NULL, dossier_id TEXT NOT NULL,
            dossier_sha256 VARCHAR(64) NOT NULL, created_at TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('PENDING','LOADING','COMPLETE','FAILED')))"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS nct_stream_sources (
            run_id TEXT PRIMARY KEY REFERENCES nct_stream_runs(run_id),
            source_url TEXT NOT NULL, sha256 VARCHAR(64) NOT NULL,
            document TEXT NOT NULL, canonical_sha256 VARCHAR(64) NOT NULL, verified_at TEXT NOT NULL)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS nct_stream_events (
            run_id TEXT NOT NULL REFERENCES nct_stream_runs(run_id),
            sequence INTEGER NOT NULL, event_key VARCHAR(64) NOT NULL,
            document TEXT NOT NULL, PRIMARY KEY(run_id,sequence), UNIQUE(run_id,event_key))"""))
        if engine.dialect.name == "postgresql":
            c.execute(text("""CREATE OR REPLACE FUNCTION nct_stream_append_only() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
                RAISE EXCEPTION 'NCT stream source/events are append-only'; END; $$"""))
            for table in ("nct_stream_events", "nct_stream_sources"):
                exists = c.execute(text("SELECT 1 FROM pg_trigger WHERE tgname=:name AND tgrelid=CAST(:table AS regclass)"), {"name": table + "_immutable", "table": table}).scalar()
                if not exists:
                    c.execute(text(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION nct_stream_append_only()"))
            for table in ("nct_stream_runs", "nct_stream_events", "nct_stream_sources"):
                c.execute(text(f"REVOKE ALL ON {table} FROM PUBLIC"))
        else:
            for table in ("nct_stream_events", "nct_stream_sources"):
                for operation in ("UPDATE", "DELETE"):
                    c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'NCT stream source/events are append-only'); END"))


def saved_dossier(c, nct, dossier_id=None):
    if dossier_id and dossier_id.startswith("phase3-catalog:"):
        from .phase3_catalog import saved_catalog_dossier
        return saved_catalog_dossier(c, nct, dossier_id)
    revision = None
    if dossier_id:
        revision, separator, suffix = dossier_id.rpartition("/")
        if not separator or suffix != nct:
            raise ValueError("Saved dossier identity mismatch")
    revision_clause = " AND d.run_id=:revision" if revision else ""
    parameters = {"nct": nct, **({"revision": revision} if revision else {})}
    row = c.execute(text("""SELECT d.run_id,d.document,d.sha256
        FROM scientific_candidate_dossiers d JOIN scientific_review_runs r ON r.run_id=d.run_id
        WHERE d.nct_id=:nct""" + revision_clause + " ORDER BY r.verified_at DESC LIMIT 1"), parameters).first()
    if row is None:
        if dossier_id is None:
            from .phase3_catalog import saved_catalog_dossier
            return saved_catalog_dossier(c, nct)
        raise LookupError("No existing saved dossier for this NCT")
    doc = json.loads(row[1])
    if doc.get("nct_id") != nct or digest(doc) != row[2]:
        raise ValueError("Saved dossier identity/checksum mismatch")
    return {"id": row[0] + "/" + nct, "sha256": row[2], "document": doc}


def require_nct(nct):
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        raise ValueError("An exact NCT identifier is required")


def get_run(engine, nct, run_id):
    require_nct(nct)
    if not SAFE_ID.fullmatch(run_id):
        raise ValueError("Invalid stream run identifier")
    with engine.connect() as c:
        row = c.execute(text("SELECT * FROM nct_stream_runs WHERE run_id=:run"), {"run": run_id}).mappings().first()
    if row is None or row["nct_id"] != nct:
        raise LookupError("No stream run for this dossier")
    return dict(row)


def create_run(engine, nct, request_key, *, submit=True, reuse_existing=False):
    require_nct(nct)
    if not isinstance(request_key, str) or not SAFE_ID.fullmatch(request_key):
        raise ValueError("Invalid idempotency key")
    with _write_lock:
        with engine.begin() as c:
            existing = c.execute(text("SELECT * FROM nct_stream_runs WHERE request_key=:key"), {"key": request_key}).mappings().first()
            if existing:
                if existing["nct_id"] != nct:
                    raise ValueError("Idempotency key belongs to another dossier")
                return snapshot(engine, nct, existing["run_id"])
            if reuse_existing:
                previous = c.execute(text("SELECT run_id FROM nct_stream_runs WHERE nct_id=:nct ORDER BY created_at DESC,run_id DESC LIMIT 1"), {"nct": nct}).scalar()
                if previous:
                    return snapshot(engine, nct, previous)
            dossier = saved_dossier(c, nct)
            run_id = str(uuid.uuid4())
            try:
                c.execute(text("""INSERT INTO nct_stream_runs(run_id,request_key,nct_id,dossier_id,dossier_sha256,created_at,status)
                    VALUES(:run,:key,:nct,:dossier,:sha,:time,'PENDING')"""),
                          {"run": run_id, "key": request_key, "nct": nct, "dossier": dossier["id"], "sha": dossier["sha256"], "time": stamp()})
            except IntegrityError:
                raise ValueError("Concurrent duplicate request; reconnect using the same request key")
    if submit:
        _pool.submit(worker, engine, run_id)
    return snapshot(engine, nct, run_id)


def emit(engine, run, node_id, level, status, value=None, *, parent_id=None, source=None, kind="node", terminal=False):
    if status not in {"PENDING", "LOADING", *TERMINAL}:
        raise ValueError("Invalid evidence state")
    base = {"run_id": run["run_id"], "nct_id": run["nct_id"], "dossier_id": run["dossier_id"],
            "node_id": node_id, "level": level, "status": status, "value": value,
            "parent_id": parent_id, "source": source, "kind": kind, "terminal": terminal,
            "decision": "ABSTAIN", "scientific_assessments_completed": 0}
    key = digest(base)
    with _write_lock:
        with engine.begin() as c:
            if engine.dialect.name == "postgresql":
                c.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(hashlib.sha256(run["run_id"].encode()).hexdigest()[:14], 16)})
            prior = c.execute(text("SELECT document FROM nct_stream_events WHERE run_id=:run AND event_key=:key"), {"run": run["run_id"], "key": key}).scalar()
            if prior:
                return json.loads(prior)
            seq = c.execute(text("SELECT COALESCE(MAX(sequence),0)+1 FROM nct_stream_events WHERE run_id=:run"), {"run": run["run_id"]}).scalar_one()
            event = {**base, "sequence": seq, "verified_at": stamp()}
            c.execute(text("INSERT INTO nct_stream_events(run_id,sequence,event_key,document) VALUES(:run,:seq,:key,:doc)"),
                      {"run": run["run_id"], "seq": seq, "key": key, "doc": canonical(event)})
            c.execute(text("UPDATE nct_stream_runs SET status=:status WHERE run_id=:run"),
                      {"run": run["run_id"], "status": ("FAILED" if status == "FAILED" else "COMPLETE") if terminal else "LOADING"})
    return event


def snapshot(engine, nct, run_id):
    run = get_run(engine, nct, run_id)
    with engine.connect() as c:
        events = [json.loads(d) for d in c.execute(text("SELECT document FROM nct_stream_events WHERE run_id=:run ORDER BY sequence"), {"run": run_id}).scalars()]
    return {**run, "latest_sequence": events[-1]["sequence"] if events else 0,
            "events": events, "terminal": bool(events and events[-1]["terminal"])}


def fresh_source(nct):
    url = "https://clinicaltrials.gov/api/v2/studies/" + nct
    with urlopen(URLRequest(url, headers={"Accept": "application/json", "User-Agent": "PDUFA-Stage1-live-evidence/1.0"}), timeout=20) as response:
        raw = response.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError("Source response too large")
        if response.status != 200 or "json" not in response.headers.get("Content-Type", ""):
            raise ValueError("Source response is not authoritative JSON")
    study = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    if study.get("protocolSection", {}).get("identificationModule", {}).get("nctId") != nct:
        raise ValueError("Authoritative source NCT does not match saved dossier")
    return study, {"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "verified_at": stamp(), "http_status": 200}


def validate_source(study, source, nct):
    if study.get("protocolSection", {}).get("identificationModule", {}).get("nctId") != nct:
        raise ValueError("Source identity mismatch")
    if source.get("url") != "https://clinicaltrials.gov/api/v2/studies/" + nct or not re.fullmatch(r"[a-f0-9]{64}", str(source.get("sha256", ""))) or source.get("http_status") != 200:
        raise ValueError("Authoritative source provenance is invalid")
    if datetime.fromisoformat(source["verified_at"].replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("Source verification timestamp is not timezone-aware")
    return {k: source[k] for k in ("url", "sha256", "verified_at", "http_status")}


def normalize(study):
    p, r = study.get("protocolSection", {}), study.get("resultsSection", {})
    outcomes = [v for v in r.get("outcomeMeasuresModule", {}).get("outcomeMeasures", []) if isinstance(v, dict) and v.get("type") == "PRIMARY"]
    analyses = [a for v in outcomes for a in v.get("analyses", []) if isinstance(a, dict)]
    ae = r.get("adverseEventsModule", {})
    return {
        "nct_identifier": p.get("identificationModule", {}).get("nctId"),
        "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
        "products": [v.get("name") for v in p.get("armsInterventionsModule", {}).get("interventions", []) if v.get("type") in ("DRUG", "BIOLOGICAL") and v.get("name")],
        "indication": p.get("conditionsModule", {}).get("conditions", []),
        "phase": p.get("designModule", {}).get("phases", []),
        "primary_endpoints": p.get("outcomesModule", {}).get("primaryOutcomes", []),
        "study_completion_status": p.get("statusModule", {}),
        "primary_endpoint_results": outcomes,
        "statistical_significance": {"reported_primary_analyses": analyses, "interpretation": "NOT_ADJUDICATED"},
        "clinical_effect_size": {"reported_estimates": [a for a in analyses if a.get("paramValue") is not None], "interpretation": "NOT_ADJUDICATED"},
        "safety_findings": ae,
        "serious_adverse_events": {"event_groups": ae.get("eventGroups", []), "serious_events": ae.get("seriousEvents", []), "interpretation": "REPORTED_NOT_ADJUDICATED"} if ae else None,
        # ClinicalTrials.gov is not independent proof of these regulatory claims.
        **{k: None for k in LEAVES["regulatory"]},
    }


def aggregate(states):
    if not states or all(s == "PENDING" for s in states):
        return "PENDING"
    if any(s not in TERMINAL for s in states):
        return "LOADING"
    if "FAILED" in states:
        return "FAILED"
    return "VERIFIED" if all(s == "VERIFIED" for s in states) else "INSUFFICIENT_EVIDENCE"


def parents(engine, run, current, source):
    for group, children in LEAVES.items():
        if not any(k in current for k in children):
            continue
        statuses = [current.get(k, "PENDING") for k in children]
        state = aggregate(statuses)
        current[group] = state
        emit(engine, run, group, 3, state, {"verified": statuses.count("VERIFIED"), "total": len(children)}, parent_id="trial", source=source)
    groups = [current.get(k, "PENDING") for k in LEAVES]
    trial_state = aggregate(groups)
    current["trial"] = trial_state
    emit(engine, run, "trial", 2, trial_state, {"verified": groups.count("VERIFIED"), "total": len(groups)}, parent_id="main", source=source)
    emit(engine, run, "main", 1, "INSUFFICIENT_EVIDENCE", {"decision": "ABSTAIN", "reason": "Evidence collection does not execute or change SCIENCE, OUTCOME or MAIN scoring rules."}, source=source)


def worker(engine, run_id, fetcher=None):
    lock = None
    acquired = False
    run = None
    try:
        lock = engine.connect()
        if engine.dialect.name == "postgresql":
            key = int(hashlib.sha256(("worker:" + run_id).encode()).hexdigest()[:14], 16)
            acquired = bool(lock.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}).scalar_one())
            lock.commit()
            if not acquired:
                return
        with engine.connect() as c:
            run = dict(c.execute(text("SELECT * FROM nct_stream_runs WHERE run_id=:run"), {"run": run_id}).mappings().one())
            if run["status"] in ("COMPLETE", "FAILED"):
                return
            dossier = saved_dossier(c, run["nct_id"], run["dossier_id"])
            if dossier["id"] != run["dossier_id"] or dossier["sha256"] != run["dossier_sha256"]:
                raise ValueError("Saved dossier revision changed during stream")
            stored = c.execute(text("SELECT * FROM nct_stream_sources WHERE run_id=:run"), {"run": run_id}).mappings().first()
        prior = snapshot(engine, run["nct_id"], run_id)["events"]
        current = {e["node_id"]: e["status"] for e in prior if e["kind"] == "node"}
        for group, keys in LEAVES.items():
            for leaf in keys:
                if leaf not in current:
                    emit(engine, run, leaf, 4, "PENDING", parent_id=group)
                    current[leaf] = "PENDING"
        if current.get("nct_identifier") not in TERMINAL:
            emit(engine, run, "nct_identifier", 4, "LOADING", parent_id="trial_identity")
            current["nct_identifier"] = "LOADING"
        if stored:
            study = json.loads(stored["document"])
            if digest(study) != stored["canonical_sha256"]:
                raise ValueError("Persisted live source checksum mismatch")
            source = {"url": stored["source_url"], "sha256": stored["sha256"], "verified_at": stored["verified_at"], "http_status": 200}
        else:
            study, source = (fetcher or fresh_source)(run["nct_id"])
        source = validate_source(study, source, run["nct_id"])
        if not stored:
            with engine.begin() as c:
                c.execute(text("INSERT INTO nct_stream_sources(run_id,source_url,sha256,document,canonical_sha256,verified_at) VALUES(:run,:url,:sha,:doc,:canonical_sha,:time)"),
                          {"run": run_id, "url": source["url"], "sha": source["sha256"], "doc": canonical(study), "canonical_sha": digest(study), "time": source["verified_at"]})
        values = normalize(study)
        baseline = dossier["document"]
        saved_identity = {"sponsor": baseline.get("sponsor", {}).get("name"), "products": [p.get("name") for p in baseline.get("products", [])],
                          "indication": baseline.get("indication", []), "phase": baseline.get("phase", [])}
        for group, keys in LEAVES.items():
            for leaf in keys:
                if current.get(leaf) in TERMINAL:
                    continue
                emit(engine, run, leaf, 4, "LOADING", parent_id=group, source=source)
                current[leaf] = "LOADING"
                value = values[leaf]
                state = "VERIFIED" if value not in (None, "", [], {}) else "INSUFFICIENT_EVIDENCE"
                if leaf in ("statistical_significance", "clinical_effect_size"):
                    state = "INSUFFICIENT_EVIDENCE"  # report the raw observations, never adjudicate by field presence
                if leaf in saved_identity and canonical(value) != canonical(saved_identity[leaf]):
                    state = "FAILED"
                    value = {"source_reported": value, "saved_dossier": saved_identity[leaf], "reason": "Saved/live evidence conflict requires review"}
                emit(engine, run, leaf, 4, state, value, parent_id=group, source=source)
                current[leaf] = state
                parents(engine, run, current, source)
        emit(engine, run, "stream_complete", 1, "FAILED" if any(current.get(k) == "FAILED" for keys in LEAVES.values() for k in keys) else "VERIFIED",
             {"collection_complete": True, "decision": "ABSTAIN", "source_sha256": source["sha256"]}, source=source, kind="complete", terminal=True)
    except Exception as exc:
        if run:
            prior = snapshot(engine, run["nct_id"], run_id)["events"]
            states = {e["node_id"]: e["status"] for e in prior if e["kind"] == "node"}
            for group, keys in LEAVES.items():
                for leaf in keys:
                    if states.get(leaf) not in TERMINAL:
                        state = "FAILED" if states.get(leaf) == "LOADING" else "INSUFFICIENT_EVIDENCE"
                        emit(engine, run, leaf, 4, state, {"reason": "Live source processing failed; evidence was not verified"}, parent_id=group)
                        states[leaf] = state
            parents(engine, run, states, None)
            emit(engine, run, "stream_failed", 1, "FAILED", {"error_type": type(exc).__name__, "message": "Live evidence collection failed; saved dossier remains unchanged"}, kind="complete", terminal=True)
        LOG.error("PDUFA_NCT_STREAM_WORKER_FAILED error_type=%s", type(exc).__name__)
    finally:
        if lock is not None:
            try:
                if acquired:
                    lock.rollback()
                    lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                    lock.commit()
            finally:
                lock.close()


def stream(engine, nct, run_id, after=0, *, duration=25):
    run = get_run(engine, nct, run_id)
    snap = snapshot(engine, nct, run_id)
    if after < 0 or after > snap["latest_sequence"]:
        raise ValueError("Resume cursor is outside persisted stream")
    def generate():
        cursor = after
        deadline, heartbeat = time.monotonic() + duration, time.monotonic()
        while time.monotonic() < deadline:
            with engine.connect() as c:
                rows = c.execute(text("SELECT sequence,document FROM nct_stream_events WHERE run_id=:run AND sequence>:after ORDER BY sequence"), {"run": run_id, "after": cursor}).all()
                state = c.execute(text("SELECT status FROM nct_stream_runs WHERE run_id=:run"), {"run": run_id}).scalar_one()
            for seq, doc in rows:
                event = json.loads(doc)
                cursor = seq
                yield "id: " + run_id + ":" + str(seq) + "\nevent: " + event["kind"] + "\ndata: " + doc + "\n\n"
                if event["terminal"]:
                    return
            if state in ("COMPLETE", "FAILED"):
                return
            if time.monotonic() - heartbeat >= 5:
                yield ": heartbeat\n\n"
                heartbeat = time.monotonic()
            time.sleep(.15)
        yield ": reconnect with Last-Event-ID\n\n"
    return generate()


class StartRequest(BaseModel):
    request_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    reuse_existing: bool = False


def install_routes(app, engine_provider, require_internal_key, require_storage):
    router = APIRouter(prefix="/api/nct-stream", dependencies=[Depends(require_internal_key), Depends(require_storage)])
    def convert(exc):
        if isinstance(exc, LookupError):
            return HTTPException(404, "No matching saved dossier or stream run")
        if isinstance(exc, ValueError):
            return HTTPException(409, "Invalid identity, integrity check or resume cursor")
        return HTTPException(503, "Live stream storage unavailable")
    @router.get("/{nct_id}/runs/{run_id}/dossier-integrity")
    def dossier_integrity(nct_id: str, run_id: str):
        """Read-only independent DB recheck; never trusts a cached snapshot checksum."""
        try:
            run = get_run(engine_provider(), nct_id, run_id)
            with engine_provider().connect() as connection:
                original = saved_dossier(connection, nct_id, run["dossier_id"])
            unchanged = (original["id"] == run["dossier_id"]
                         and original["sha256"] == run["dossier_sha256"])
            return {"nct_id": nct_id, "run_id": run_id,
                    "dossier_id": original["id"],
                    "database_sha256": original["sha256"],
                    "run_original_sha256": run["dossier_sha256"],
                    "unchanged": unchanged}
        except Exception as exc:
            raise convert(exc)

    @router.post("/{nct_id}/runs")
    def create(nct_id: str, payload: StartRequest):
        if not NCT.fullmatch(nct_id):
            raise HTTPException(422, "Invalid NCT identifier")
        try:
            return create_run(engine_provider(), nct_id, payload.request_key, reuse_existing=payload.reuse_existing)
        except Exception as exc:
            raise convert(exc)
    @router.get("/{nct_id}/runs/latest")
    def latest(nct_id: str):
        try:
            require_nct(nct_id)
            with engine_provider().connect() as connection:
                run_id = connection.execute(text("SELECT run_id FROM nct_stream_runs WHERE nct_id=:nct ORDER BY created_at DESC,run_id DESC LIMIT 1"), {"nct": nct_id}).scalar()
            if run_id is None:
                raise LookupError("No saved processing run")
            return snapshot(engine_provider(), nct_id, run_id)
        except Exception as exc:
            raise convert(exc)
    @router.get("/{nct_id}/runs/{run_id}")
    def read(nct_id: str, run_id: str):
        try:
            return snapshot(engine_provider(), nct_id, run_id)
        except Exception as exc:
            raise convert(exc)
    @router.get("/{nct_id}/runs/{run_id}/events")
    def events(nct_id: str, run_id: str, after: int = Query(default=0, ge=0), last_event_id: str | None = Header(default=None)):
        if last_event_id:
            prefix, _, seq = last_event_id.rpartition(":")
            if prefix != run_id or not seq.isdecimal():
                raise HTTPException(409, "Resume cursor belongs to a different run")
            after = int(seq)
        try:
            body = stream(engine_provider(), nct_id, run_id, after)
        except Exception as exc:
            raise convert(exc)
        return StreamingResponse(body, media_type="text/event-stream", headers={"Cache-Control": "private, no-store, no-transform", "X-Accel-Buffering": "no"})
    app.include_router(router)


def start(engine):
    if engine.dialect.name != "postgresql":
        return
    def bootstrap():
        try:
            initialize(engine)
            with engine.connect() as c:
                pending = list(c.execute(text("SELECT run_id FROM nct_stream_runs WHERE status IN ('PENDING','LOADING') ORDER BY created_at LIMIT 8")).scalars())
            for run_id in pending:
                _pool.submit(worker, engine, run_id)
            deployed_selftest(engine)
        except Exception as exc:
            LOG.error("PDUFA_NCT_STREAM_STARTUP_FAILED error_type=%s", type(exc).__name__)
    threading.Thread(target=bootstrap, name="nct-stream-bootstrap", daemon=True).start()


def deployed_selftest(engine):
    """Use the existing credential through real localhost HTTP; log no field data."""
    import os
    from urllib.error import HTTPError
    try:
        for attempt in range(20):
            try:
                with urlopen("http://127.0.0.1:8000/health", timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Application HTTP server did not become ready")
        with engine.connect() as c:
            selected = c.execute(text("SELECT nct_id FROM scientific_candidate_dossiers ORDER BY nct_id LIMIT 1")).scalar_one()
        base = "http://127.0.0.1:8000/api/nct-stream/" + selected + "/runs"
        unauthenticated_denied = False
        try:
            urlopen(URLRequest(base, data=b'{"request_key":"stage1-auth-denied"}', headers={"Content-Type": "application/json"}), timeout=5)
        except HTTPError as exc:
            unauthenticated_denied = exc.code in (401, 403)
        headers = {"X-Pdufa-Internal-Key": os.environ["PDUFA_INTERNAL_API_KEY"], "Content-Type": "application/json"}
        key = "stage1-selftest-" + os.getenv("RENDER_GIT_COMMIT", VERSION)[:40]
        with urlopen(URLRequest(base, data=canonical({"request_key": key}).encode(), headers=headers), timeout=10) as response:
            created = json.load(response)
        events, first_at, final_at = [], None, None
        incremental_received_while_processing = False
        connections = 0
        for attempt in range(4):
            resume_headers = dict(headers)
            if events:
                resume_headers["Last-Event-ID"] = created["run_id"] + ":" + str(events[-1]["sequence"])
            req = URLRequest(base + "/" + created["run_id"] + "/events", headers=resume_headers)
            with urlopen(req, timeout=35) as response:
                connections += 1
                if "text/event-stream" not in response.headers.get("Content-Type", ""):
                    raise ValueError("Deployed route is not an event stream")
                for raw in response:
                    if raw.startswith(b"data: "):
                        event = json.loads(raw[6:])
                        events.append(event)
                        if first_at is None:
                            observed = snapshot(engine, selected, created["run_id"])
                            incremental_received_while_processing = not observed["terminal"]
                        first_at = first_at or stamp()
                        if event["terminal"]:
                            final_at = stamp()
                            break
                        if attempt == 0 and len(events) == 3:
                            break  # Deliberate disconnect: prove live cursor resume.
            if final_at:
                break
        with urlopen(URLRequest(base + "/" + created["run_id"], headers=headers), timeout=10) as response:
            saved = json.load(response)
        with urlopen(URLRequest(base + "/" + created["run_id"], headers=headers), timeout=10) as response:
            reload = json.load(response)
        with engine.connect() as c:
            source = c.execute(text("SELECT source_url,sha256,document FROM nct_stream_sources WHERE run_id=:run"), {"run": created["run_id"]}).one()
            original = saved_dossier(c, selected)
        live = json.loads(source[2])
        passed = (unauthenticated_denied and bool(events) and events[-1]["terminal"] and events[-1]["status"] == "VERIFIED"
                  and live["protocolSection"]["identificationModule"]["nctId"] == selected
                  and source[0] == "https://clinicaltrials.gov/api/v2/studies/" + selected
                  and [e["sequence"] for e in events] == list(range(1, len(events) + 1))
                  and saved["events"] == reload["events"] == events
                  and original["sha256"] == created["dossier_sha256"] and connections >= 2
                  and incremental_received_while_processing)
        proof = {"status": "PASS" if passed else "FAIL", "version": VERSION,
                 "nct_id": selected, "run_id": created["run_id"], "dossier_id": created["dossier_id"],
                 "dossier_sha256": created["dossier_sha256"], "live_source_sha256": source[1],
                 "authentication_denied_without_key": unauthenticated_denied, "http_stream_events": len(events),
                 "persisted_events": len(saved["events"]), "reload_matches": saved["events"] == reload["events"],
                 "incremental_received_while_processing": incremental_received_while_processing,
                 "http_connections": connections, "cursor_resume_without_duplicates": len({e["sequence"] for e in events}) == len(events),
                 "saved_dossier_unchanged": original["sha256"] == created["dossier_sha256"],
                 "first_event_received_at": first_at, "terminal_event_received_at": final_at,
                 "verified_at": stamp(), "frontend_browser_verified": False, "decision": "ABSTAIN"}
        LOG.warning("PDUFA_STAGE1_BACKEND_VERIFICATION %s", canonical(proof))
    except Exception as exc:
        LOG.error("PDUFA_STAGE1_BACKEND_VERIFICATION status=FAIL error_type=%s", type(exc).__name__)
