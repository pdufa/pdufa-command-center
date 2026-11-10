"""Durable research examination receipts, separate from source audits and grades.

This callable-only pilot workflow never retrieves evidence, invents findings,
authenticates a clinical reviewer, or writes the scientific grading ledger.
Drivers must supply what they actually examined. A receipt records that research
claim and its captured-source provenance; it does not independently verify it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from . import medical_assessment_ledger as ledger
from . import medical_phase_matrix as phase_matrix

PILOT = "NCT06081894"
VERSION = "MEDICAL_RESEARCH_EXAMINATION_V1"
ISOLATED_SERVICE = "srv-dbntrkpsrm7s73aec3lg"
CLASSES = {"FAVORABLE", "UNFAVORABLE", "MISSING", "CONTRADICTORY"}
KEY = re.compile(r"^[A-Za-z0-9_.:-]{8,120}$")


def enabled_for_service():
    """This infrastructure may be activated only on the existing isolated service."""
    return os.getenv("RENDER_SERVICE_ID") == ISOLATED_SERVICE and all(
        os.getenv(name, "").lower() in ("1", "true", "yes") for name in (
            "PDUFA_MEDICAL_PREVIEW_ENABLED", "PDUFA_MEDICAL_ASSESSMENT_LEDGER_ENABLED",
            "PDUFA_MEDICAL_PHASE_MATRIX_ENABLED", "PDUFA_MEDICAL_RESEARCH_EXECUTION_ENABLED"))


def activate(engine, *, ledger_ready):
    """Create only additive schema, never a run or source examination on startup."""
    if not enabled_for_service() or not ledger_ready:
        return False
    initialize(engine)
    return True


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _time(value):
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if when.tzinfo is None or when.utcoffset() is None:
            raise ValueError()
        if when > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError()
        return when
    except (ValueError, TypeError, AttributeError):
        raise ValueError("A real timezone-aware examination timestamp is required")


def _narrative(value, minimum, maximum):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError("A substantive examined finding, limitation or research rationale is required")
    return value.strip()


def initialize(engine, *, test_only=False):
    if engine.dialect.name != "postgresql" and not test_only:
        raise RuntimeError("Research execution requires isolated durable PostgreSQL")
    tables = ("medical_research_execution_runs", "medical_research_examination_events")
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_research_execution_runs (
            run_id TEXT PRIMARY KEY,
            nct_id TEXT NOT NULL REFERENCES medical_assessment_trial_roster(nct_id),
            source_run_id TEXT NOT NULL REFERENCES medical_continuous_runs(run_id),
            phase_event_id TEXT REFERENCES medical_assessment_phase_events(phase_event_id),
            context_sha256 TEXT NOT NULL,
            plan_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(nct_id,context_sha256))"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_research_examination_events (
            examination_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES medical_research_execution_runs(run_id),
            request_key TEXT NOT NULL,
            assessment_index INTEGER NOT NULL CHECK (assessment_index BETWEEN 1 AND 40),
            method_index INTEGER NOT NULL CHECK (method_index BETWEEN 1 AND 20),
            revision INTEGER NOT NULL CHECK (revision>=1),
            source_examination_state TEXT NOT NULL CHECK (source_examination_state IN ('EXAMINED','GAP_RECORDED')),
            research_recommendation INTEGER CHECK (research_recommendation BETWEEN 0 AND 5),
            record_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            supersedes_event_id TEXT REFERENCES medical_research_examination_events(examination_id),
            UNIQUE(run_id,request_key),
            UNIQUE(run_id,assessment_index,method_index,revision))"""))
        if engine.dialect.name == "postgresql":
            c.execute(text("""CREATE OR REPLACE FUNCTION medical_research_reject_mutation()
                RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
                RAISE EXCEPTION 'Research execution history is append-only'; END; $$"""))
            for table in tables:
                exists = c.execute(text("SELECT 1 FROM pg_trigger WHERE tgname=:name AND tgrelid=CAST(:table AS regclass)"),
                                   {"name": table + "_immutable", "table": table}).scalar()
                if not exists:
                    c.execute(text(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} "
                                   "FOR EACH STATEMENT EXECUTE FUNCTION medical_research_reject_mutation()"))
        else:
            for table in tables:
                for operation in ("UPDATE", "DELETE"):
                    c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_{operation.lower()} BEFORE {operation} ON {table} "
                                   "BEGIN SELECT RAISE(ABORT,'Research execution history is append-only'); END"))


def _context(c, nct, *, lock=False):
    from .medical_continuous import check_nct
    check_nct(nct)
    suffix = " FOR UPDATE" if lock and c.dialect.name == "postgresql" else ""
    run = c.execute(text("SELECT source_run_id FROM medical_assessment_trial_roster WHERE nct_id=:nct" + suffix),
                    {"nct": nct}).scalar()
    if not run:
        raise LookupError("Roster-attached source run is required")
    source = c.execute(text("SELECT nct_id,status FROM medical_continuous_runs WHERE run_id=:run"),
                       {"run": run}).first()
    stages = list(c.execute(text("SELECT stage_index,document,finished_at FROM medical_continuous_stages "
                                "WHERE run_id=:run ORDER BY stage_index"), {"run": run}).mappings())
    if not source or source.nct_id != nct or source.status != "COMPLETE" or [s["stage_index"] for s in stages] != list(range(12)):
        raise ValueError("A complete exact-NCT roster source run is required")
    identity = json.loads(stages[0]["document"])
    if identity.get("nct") != nct or identity.get("source") != f"https://clinicaltrials.gov/study/{nct}":
        raise ValueError("Original source identity does not match the exact NCT")
    phase = c.execute(text("SELECT phase_event_id FROM medical_assessment_phase_events WHERE nct_id=:nct "
                           "ORDER BY created_at DESC,phase_event_id DESC LIMIT 1"), {"nct": nct}).scalar()
    context = {"nct": nct, "sourceRunId": run, "phaseEventId": phase,
               "catalogSha256": _digest(phase_matrix.catalog()),
               "sourceStages": [{"stageIndex": s["stage_index"],
                                 "sha256": hashlib.sha256(s["document"].encode("utf-8")).hexdigest(),
                                 "capturedAt": s["finished_at"]} for s in stages]}
    return context, stages


def plan(engine, nct):
    """Read-only plans support every canonical FOCUS identity; no run is started."""
    matrix = phase_matrix.matrix(engine, nct)
    with engine.connect() as c:
        context, _ = _context(c, nct)
    latest = matrix["phaseEvents"][-1]["phase_event_id"] if matrix["phaseEvents"] else None
    if latest != context["phaseEventId"] or matrix["sourceRunId"] != context["sourceRunId"]:
        raise ValueError("Phase/source changed while planning; retry from a fresh snapshot")
    tasks = [{"assessmentIndex": a["assessmentIndex"], "assessmentId": a["assessmentId"],
              "methodIndex": m["methodIndex"], "question": m["question"],
              "method": m["method"], "requiredSources": m["requiredSources"],
              "priorityTier": m["priorityTier"], "priorityRank": m["priorityRank"],
              "phaseApplicability": m["phaseApplicability"]}
             for a in matrix["assessments"] for m in a["methods"]]
    tasks.sort(key=lambda m: (m["priorityRank"] if m["priorityRank"] is not None else 801,
                              m["assessmentIndex"], m["methodIndex"]))
    return {"schema": VERSION, **context, "contextSha256": _digest(context),
            "phaseBasis": matrix["phaseBasis"], "tasks": tasks, "totalPositions": 800,
            "researchStatus": "PLAN_ONLY_NOT_EXAMINED", "officialGradesWritten": 0,
            "clinicalSignoff": False, "prediction": "ABSTAIN", "certainty": "NOT_VALIDATED",
            "accuracy": "NOT_CALIBRATED"}


def start(engine, nct=PILOT):
    if nct != PILOT:
        raise ValueError("Research execution writes remain restricted to the validated pilot")
    packet = plan(engine, nct)
    run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, VERSION + ":" + nct + ":" + packet["contextSha256"]))
    with engine.begin() as c:
        current, _ = _context(c, nct, lock=True)
        if _digest(current) != packet["contextSha256"]:
            raise ValueError("Source or phase changed before research execution started")
        c.execute(text("""INSERT INTO medical_research_execution_runs
            (run_id,nct_id,source_run_id,phase_event_id,context_sha256,plan_json,created_at)
            VALUES(:id,:nct,:source,:phase,:digest,:plan,:at) ON CONFLICT(nct_id,context_sha256) DO NOTHING"""),
            {"id": run_id, "nct": nct, "source": packet["sourceRunId"], "phase": packet["phaseEventId"],
             "digest": packet["contextSha256"], "plan": _json(packet), "at": ledger.now()})
    return snapshot(engine, run_id)


def _latest(events):
    out = {}
    for event in events:
        key = (event["assessment_index"], event["method_index"])
        if key not in out or event["revision"] > out[key]["revision"]:
            out[key] = event
    return out


def snapshot(engine, run_id):
    with engine.connect() as c:
        run = c.execute(text("SELECT * FROM medical_research_execution_runs WHERE run_id=:id"), {"id": run_id}).mappings().first()
        if not run:
            raise LookupError("Research execution run not found")
        events = list(c.execute(text("SELECT * FROM medical_research_examination_events WHERE run_id=:id "
                                    "ORDER BY recorded_at,examination_id"), {"id": run_id}).mappings())
        context, _ = _context(c, run["nct_id"])
    packet = json.loads(run["plan_json"])
    latest = _latest(events)
    examined = sum(e["source_examination_state"] == "EXAMINED" for e in latest.values())
    gaps = len(latest) - examined
    next_task = next((t for t in packet["tasks"] if (t["assessmentIndex"], t["methodIndex"]) not in latest), None)
    fresh = _digest(context) == run["context_sha256"]
    return {"schema": VERSION, "runId": run_id, "nct": run["nct_id"], "createdAt": run["created_at"],
            "sourceRunId": run["source_run_id"], "phaseEventId": run["phase_event_id"],
            "status": "STALE_CONTEXT" if not fresh else "RESEARCH_EXAMINATIONS_RECORDED" if len(latest) == 800 else "AWAITING_SOURCE_EXAMINATIONS",
            "totalPositions": 800, "recordedPositions": len(latest), "examinedPositions": examined,
            "gapPositions": gaps, "remainingExaminations": 800 - examined,
            "recommendationPositions": sum(e["research_recommendation"] is not None for e in latest.values()),
            "historicalExaminationEvents": len(events), "nextTask": next_task,
            "events": [{**json.loads(e["record_json"]), "examinationId": e["examination_id"],
                        "revision": e["revision"], "recordedAt": e["recorded_at"],
                        "supersedesEventId": e["supersedes_event_id"]} for e in events],
            "officialGradesWritten": 0, "clinicalSignoff": False,
            "prediction": "ABSTAIN", "certainty": "NOT_VALIDATED", "accuracy": "NOT_CALIBRATED",
            "note": "Research receipts and recommendations are not independently verified scientific grades."}


def append_examination(engine, run_id, *, request_key, assessment_index, method_index,
                       sources, findings, limitations, rationale, examined_at, producer_id,
                       recommendation=None, supersedes_event_id=None):
    """Append a research driver's explicit examination, never an official grade.

    `sources` cite exact saved stage URLs plus the caller-checked capture digest,
    source version, publication date and precise document location. Empty sources
    are allowed only for an explicit missing-evidence record, without a score.
    """
    ledger._position(assessment_index, method_index)
    if not isinstance(request_key, str) or not KEY.fullmatch(request_key):
        raise ValueError("A bounded idempotent research request key is required")
    producer_id = _narrative(producer_id, 3, 120)
    examined_time = _time(examined_at)
    limitations = _narrative(limitations, 20, 4000)
    rationale = _narrative(rationale, 40, 6000)
    if not isinstance(findings, list) or not 1 <= len(findings) <= 20:
        raise ValueError("Explicit examined or missing-evidence findings are required")
    for finding in findings:
        if (not isinstance(finding, dict) or set(finding) != {"classification", "finding"}
                or finding["classification"] not in CLASSES):
            raise ValueError("Findings must distinguish favorable, unfavorable, missing and contradictory evidence")
        _narrative(finding["finding"], 40, 3000)
    if not isinstance(sources, list) or len(sources) > 12:
        raise ValueError("At most twelve examined source references are allowed")
    nonmissing = any(f["classification"] != "MISSING" for f in findings)
    if nonmissing and not sources:
        raise ValueError("Non-missing research findings require examined original sources")
    if recommendation is not None and (type(recommendation) is not int or not 0 <= recommendation <= 5 or not nonmissing):
        raise ValueError("A research recommendation requires examined non-missing evidence; missing is never zero")
    with engine.begin() as c:
        run = c.execute(text("SELECT * FROM medical_research_execution_runs WHERE run_id=:id"), {"id": run_id}).mappings().first()
        if not run or run["nct_id"] != PILOT:
            raise ValueError("An existing exact pilot research run is required")
        context, stages = _context(c, run["nct_id"], lock=True)
        if _digest(context) != run["context_sha256"]:
            raise ValueError("Latest phase, roster source or captured source version changed; start a fresh research run")
        if recommendation is not None and not run["phase_event_id"]:
            raise ValueError("Research recommendations require the current independently verified phase")
        packet = json.loads(run["plan_json"])
        task = next(t for t in packet["tasks"] if (t["assessmentIndex"], t["methodIndex"]) == (assessment_index, method_index))
        if recommendation is not None and task["phaseApplicability"] != "CURRENT_PHASE":
            raise ValueError("Forward-looking or unverified phase methods cannot receive a numerical research recommendation")
        captures = []
        for source in sources:
            if not isinstance(source, dict) or set(source) != {"stageIndex", "sourceUrl", "stageDocumentSha256", "sourceVersion", "publicationDate", "sourceLocation"}:
                raise ValueError("Each examined source requires its original version, date, location and captured digest")
            index = source["stageIndex"]
            if type(index) is not int or not 0 <= index < 12:
                raise ValueError("Source stage must be 0–11")
            url = ledger._url(source["sourceUrl"])
            stage = stages[index]
            digest = context["sourceStages"][index]["sha256"]
            if source["stageDocumentSha256"] != digest or url not in ledger._source_urls(json.loads(stage["document"])):
                raise ValueError("Source URL or captured digest does not match the attached source run")
            _narrative(source["sourceVersion"], 3, 300)
            _narrative(source["sourceLocation"], 5, 500)
            if source["publicationDate"] is not None:
                try:
                    published = date.fromisoformat(source["publicationDate"])
                except (TypeError, ValueError):
                    raise ValueError("Publication date must be an original ISO date or explicitly unknown")
                if published > examined_time.date():
                    raise ValueError("An examination cannot precede its source publication")
            captures.append({**source, "sourceCapturedAt": stage["finished_at"]})
        record = {"assessmentIndex": assessment_index, "methodIndex": method_index,
                  "scientificQuestion": task["question"], "phaseApplicability": task["phaseApplicability"],
                  "priorityTier": task["priorityTier"], "priorityRank": task["priorityRank"],
                  "sources": captures, "findings": findings, "limitations": limitations,
                  "rationale": rationale, "examinedAt": examined_at, "producerId": producer_id,
                  "recommendation": recommendation, "recommendationState": "RESEARCH_ONLY_PENDING_AUTHORIZED_REVIEW" if recommendation is not None else "NO_NUMERICAL_RECOMMENDATION",
                  "sourceExaminationState": "EXAMINED" if nonmissing else "GAP_RECORDED"}
        payload_digest = _digest({**record, "supersedesEventId": supersedes_event_id})
        existing = c.execute(text("SELECT examination_id,payload_sha256 FROM medical_research_examination_events "
                                  "WHERE run_id=:id AND request_key=:key"), {"id": run_id, "key": request_key}).first()
        if existing:
            if existing.payload_sha256 != payload_digest:
                raise ValueError("Idempotency key already records different examined evidence")
            return existing.examination_id
        events = list(c.execute(text("SELECT * FROM medical_research_examination_events WHERE run_id=:id"), {"id": run_id}).mappings())
        latest = _latest(events)
        key = (assessment_index, method_index)
        previous = latest.get(key)
        if (previous["examination_id"] if previous else None) != supersedes_event_id:
            raise ValueError("Research revisions must explicitly supersede the latest examination event")
        if not previous:
            next_task = next((t for t in packet["tasks"] if (t["assessmentIndex"], t["methodIndex"]) not in latest), None)
            if next_task is None or (next_task["assessmentIndex"], next_task["methodIndex"]) != key:
                raise ValueError("Research must examine the next phase-prioritized method first")
        event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, run_id + ":" + request_key))
        c.execute(text("""INSERT INTO medical_research_examination_events
            (examination_id,run_id,request_key,assessment_index,method_index,revision,
             source_examination_state,research_recommendation,record_json,payload_sha256,recorded_at,supersedes_event_id)
            VALUES(:event,:run,:key,:a,:m,:revision,:state,:recommendation,:record,:digest,:at,:previous)"""),
            {"event": event_id, "run": run_id, "key": request_key, "a": assessment_index, "m": method_index,
             "revision": previous["revision"] + 1 if previous else 1, "state": record["sourceExaminationState"],
             "recommendation": recommendation, "record": _json(record), "digest": payload_digest,
             "at": ledger.now(), "previous": supersedes_event_id})
    return event_id


def process_batch(engine, run_id, examinations):
    """Bounded supplied-evidence processing; replay a stopped batch safely.

    Receipts commit per position. A later invalid item leaves earlier completed
    examinations available for identical-key replay after interruption.
    """
    if not isinstance(examinations, list) or not 1 <= len(examinations) <= 20:
        raise ValueError("Research examination batches must contain 1–20 explicit records")
    return [append_examination(engine, run_id, **item) for item in examinations]


def latest(engine, nct):
    from .medical_continuous import check_nct
    check_nct(nct)
    with engine.connect() as c:
        run_id = c.execute(text("SELECT run_id FROM medical_research_execution_runs WHERE nct_id=:nct "
                                "ORDER BY created_at DESC,run_id DESC LIMIT 1"), {"nct": nct}).scalar()
    if not run_id:
        raise LookupError("No research examinations have been started for this exact trial")
    return snapshot(engine, run_id)


def install_routes(app, engine_provider, require_read_key, require_storage):
    """Authenticated reads only. No HTTP path starts research or accepts findings."""
    router = APIRouter(prefix="/api/internal/medical-research-execution",
                       dependencies=[Depends(require_read_key), Depends(require_storage)])

    @router.get("/{nct}/plan")
    def read_plan(nct: str):
        try:
            return plan(engine_provider(), nct)
        except ValueError:
            raise HTTPException(422, "An exact FOCUS trial and fresh source/phase context are required")
        except LookupError:
            raise HTTPException(404, "Roster-attached source evidence is not available")
        except Exception:
            raise HTTPException(503, "Research planning evidence cannot be verified")

    @router.get("/{nct}/latest")
    def read_latest(nct: str):
        try:
            return latest(engine_provider(), nct)
        except ValueError:
            raise HTTPException(422, "An exact FOCUS trial is required")
        except LookupError:
            raise HTTPException(404, "No saved research examination run is available")
        except Exception:
            raise HTTPException(503, "Research execution history cannot be verified")

    app.include_router(router)
