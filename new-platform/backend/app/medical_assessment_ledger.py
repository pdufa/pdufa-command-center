"""Phase-first, source-linked scientific assessment ledger (Stage 2).

The 12-stage source research is a LEAD, not an adjudicated scientific test.
This module adds new tables only. It never changes existing research runs,
does not infer grades, and does not calculate FDA predictions or certainty.
Reviewer functions are intentionally not exposed as HTTP write routes.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

LOG = logging.getLogger(__name__)
PHASES = frozenset(("EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4"))
DISPOSITIONS = frozenset(("SCORED", "NOT_APPLICABLE", "RETRACTED"))
SOURCE_RUN_STAGES = 12
ASSESSMENTS = 40
METHODS = 20
HEX_SHA = re.compile(r"^[a-f0-9]{64}$")
REVIEWER = re.compile(r"^[A-Za-z0-9_.@-]{3,120}$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _url(value: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 2048:
        raise ValueError("An exact original HTTPS source URL is required")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Evidence must use an original HTTPS source")
    return value


def _reviewer(value: str) -> str:
    if not isinstance(value, str) or not REVIEWER.fullmatch(value):
        raise ValueError("A named reviewer identifier is required")
    return value


def _source_urls(value) -> set[str]:
    """Exact parsed source values, never substrings of a serialized document."""
    if isinstance(value, dict):
        return set().union(*(_source_urls(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(_source_urls(v) for v in value))
    if isinstance(value, str) and value.startswith("https://"):
        return {value}
    return set()


def _position(assessment: int, method: int | None = None) -> None:
    if type(assessment) is not int or not 1 <= assessment <= ASSESSMENTS:
        raise ValueError("Assessment index must be 1–40")
    if method is not None and (type(method) is not int or not 1 <= method <= METHODS):
        raise ValueError("Scientific method index must be 1–20")


def initialize(engine, *, test_only: bool = False) -> None:
    """Additive tables only. Production requires isolated durable PostgreSQL."""
    if engine.dialect.name != "postgresql" and not test_only:
        raise RuntimeError("Assessment ledger requires durable PostgreSQL")
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_assessment_trial_roster (
            nct_id TEXT PRIMARY KEY,
            source_run_id TEXT NOT NULL REFERENCES medical_continuous_runs(run_id),
            source_completed_at TEXT NOT NULL,
            seeded_at TEXT NOT NULL)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_assessment_phase_events (
            phase_event_id TEXT PRIMARY KEY,
            nct_id TEXT NOT NULL REFERENCES medical_assessment_trial_roster(nct_id),
            source_run_id TEXT NOT NULL REFERENCES medical_continuous_runs(run_id),
            verified_phase TEXT NOT NULL CHECK (verified_phase IN
                ('EARLY_PHASE1','PHASE1','PHASE2','PHASE3','PHASE4')),
            original_registry_url TEXT NOT NULL,
            source_stage_sha256 TEXT NOT NULL,
            reviewer_id TEXT NOT NULL,
            verified_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            supersedes_event_id TEXT REFERENCES medical_assessment_phase_events(phase_event_id))"""))
        c.execute(text("""CREATE INDEX IF NOT EXISTS medical_assessment_phases_nct
            ON medical_assessment_phase_events(nct_id,created_at)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_assessment_review_events (
            review_event_id TEXT PRIMARY KEY,
            nct_id TEXT NOT NULL REFERENCES medical_assessment_trial_roster(nct_id),
            source_run_id TEXT NOT NULL REFERENCES medical_continuous_runs(run_id),
            phase_event_id TEXT NOT NULL REFERENCES medical_assessment_phase_events(phase_event_id),
            verified_phase TEXT NOT NULL,
            assessment_index INTEGER NOT NULL CHECK (assessment_index BETWEEN 1 AND 40),
            method_index INTEGER NOT NULL CHECK (method_index BETWEEN 1 AND 20),
            revision INTEGER NOT NULL CHECK (revision >= 1),
            disposition TEXT NOT NULL CHECK (disposition IN ('SCORED','NOT_APPLICABLE','RETRACTED')),
            grade INTEGER,
            evidence_json TEXT NOT NULL,
            reviewer_id TEXT NOT NULL,
            rationale TEXT NOT NULL,
            evidence_reviewed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            supersedes_event_id TEXT REFERENCES medical_assessment_review_events(review_event_id),
            UNIQUE(nct_id,verified_phase,assessment_index,method_index,revision),
            CHECK ((disposition='SCORED' AND grade BETWEEN 0 AND 5)
                OR (disposition IN ('NOT_APPLICABLE','RETRACTED') AND grade IS NULL)))"""))
        c.execute(text("""CREATE INDEX IF NOT EXISTS medical_assessment_reviews_nct
            ON medical_assessment_review_events(nct_id,verified_phase,assessment_index,method_index)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_assessment_gap_events (
            gap_event_id TEXT PRIMARY KEY,
            nct_id TEXT NOT NULL REFERENCES medical_assessment_trial_roster(nct_id),
            source_run_id TEXT NOT NULL REFERENCES medical_continuous_runs(run_id),
            assessment_index INTEGER NOT NULL CHECK (assessment_index BETWEEN 1 AND 40),
            method_index INTEGER CHECK (method_index BETWEEN 1 AND 20),
            gap_code TEXT NOT NULL,
            evidence_note TEXT NOT NULL,
            recorded_at TEXT NOT NULL)"""))
        c.execute(text("""CREATE INDEX IF NOT EXISTS medical_assessment_gaps_nct
            ON medical_assessment_gap_events(nct_id,recorded_at)"""))
        # Guard accidental DML without rewriting any existing rows or changing
        # database privileges. Source runs/stages remain outside this ledger's
        # schema boundary. Owners can still alter schema; these are not a claim
        # of protection against a privileged database administrator.
        immutable = ("medical_assessment_trial_roster", "medical_assessment_phase_events",
                     "medical_assessment_review_events", "medical_assessment_gap_events")
        if engine.dialect.name == "postgresql":
            c.execute(text("""CREATE OR REPLACE FUNCTION medical_assessment_reject_mutation()
                RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
                RAISE EXCEPTION 'Medical assessment history and roster attachments are append-only';
                END; $$"""))
            for table in immutable:
                exists = c.execute(text("""SELECT 1 FROM pg_trigger
                    WHERE tgname=:name AND tgrelid=CAST(:table AS regclass)"""),
                    {"name": table + "_immutable", "table": table}).scalar()
                if not exists:
                    c.execute(text(f"CREATE TRIGGER {table}_immutable "
                                   f"BEFORE UPDATE OR DELETE OR TRUNCATE ON {table} "
                                   "FOR EACH STATEMENT EXECUTE FUNCTION medical_assessment_reject_mutation()"))
        else:
            # SQLite is permitted only by the explicit isolated-test flag.
            for table in immutable:
                for operation in ("UPDATE", "DELETE"):
                    c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_{operation.lower()} "
                                   f"BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, "
                                   "'Medical assessment history and roster attachments are append-only'); END"))


def seed_roster(engine) -> dict:
    """One-time, immutable attachment to every genuinely completed 12-stage run.

    All 29 exact NCTs must be present before a single roster row is inserted.
    Restart never rewrites an earlier source-run association or creates grades.
    """
    from . import medical_continuous as source
    canonical = set(source.roster())
    with engine.begin() as c:
        completed = c.execute(text("""SELECT r.nct_id,r.run_id,r.updated_at,COUNT(s.stage_index) AS stages
            FROM medical_continuous_runs r
            JOIN medical_continuous_stages s ON s.run_id=r.run_id
            WHERE r.status='COMPLETE'
            GROUP BY r.nct_id,r.run_id,r.updated_at
            HAVING COUNT(s.stage_index)=:required
            ORDER BY r.updated_at DESC,r.run_id DESC"""),
            {"required": SOURCE_RUN_STAGES}).mappings().all()
        by_nct = {}
        for item in completed:
            by_nct.setdefault(item["nct_id"], item)
        missing = canonical - set(by_nct)
        if missing:
            raise RuntimeError("Refusing partial assessment roster; missing completed source runs: "
                               + str(len(missing)))
        for nct in sorted(canonical):
            row = by_nct[nct]
            c.execute(text("""INSERT INTO medical_assessment_trial_roster
                (nct_id,source_run_id,source_completed_at,seeded_at)
                VALUES (:nct,:run,:done,:now)
                ON CONFLICT(nct_id) DO NOTHING"""),
                {"nct": nct,"run": row["run_id"],"done": row["updated_at"],"now":now()})
    return coverage(engine)


def coverage(engine) -> dict:
    from . import medical_continuous as source
    canonical = set(source.roster())
    with engine.connect() as c:
        rows = list(c.execute(text("""SELECT r.nct_id,r.source_run_id,
            runs.status,
            (SELECT COUNT(*) FROM medical_continuous_stages s
             WHERE s.run_id=r.source_run_id) AS stage_count
            FROM medical_assessment_trial_roster r
            JOIN medical_continuous_runs runs ON runs.run_id=r.source_run_id""")).mappings())
        verified = c.execute(text("""SELECT COUNT(DISTINCT nct_id)
            FROM medical_assessment_phase_events""")).scalar_one()
        reviews = c.execute(text("""SELECT COUNT(*)
            FROM medical_assessment_review_events""")).scalar_one()
        gaps = c.execute(text("""SELECT COUNT(*)
            FROM medical_assessment_gap_events""")).scalar_one()
    seeded = {r["nct_id"] for r in rows}
    complete = sum(r["nct_id"] in canonical and r["status"] == "COMPLETE"
                   and int(r["stage_count"]) == SOURCE_RUN_STAGES for r in rows)
    ok = seeded == canonical and complete == len(canonical)
    return {"status": "READY_FOR_REVIEW" if ok else "INCOMPLETE",
            "sourceComplete": complete, "canonicalTrials": len(canonical),
            "missingNcts": sorted(canonical - seeded),
            "unexpectedNcts": sorted(seeded - canonical),
            "sourceStageCount": sum(int(r["stage_count"]) for r in rows if r["nct_id"] in canonical),
            "assessmentPositionsPerTrial": ASSESSMENTS * METHODS,
            "potentialMethodPositions": len(canonical) * ASSESSMENTS * METHODS,
            "phaseVerifiedNcts": int(verified),
            "reviewEvents": int(reviews), "explicitGapEvents": int(gaps),
            "scientificSignoff": False, "fdaPrediction": "ABSTAIN",
            "certainty": "NOT_VALIDATED",
            "note": "Recorded source stages are leads, not scored scientific tests."}


def trial_history(engine, nct: str) -> dict:
    from . import medical_continuous as source
    source.check_nct(nct)
    with engine.connect() as c:
        roster = c.execute(text("""SELECT nct_id,source_run_id,source_completed_at
            FROM medical_assessment_trial_roster WHERE nct_id=:nct"""),
            {"nct":nct}).mappings().first()
        if roster is None:
            raise LookupError("Trial is not in the scientific assessment ledger")
        phases = list(c.execute(text("""SELECT phase_event_id,verified_phase,original_registry_url,
            reviewer_id,verified_at,created_at,supersedes_event_id
            FROM medical_assessment_phase_events
            WHERE nct_id=:nct ORDER BY created_at,phase_event_id"""),
            {"nct":nct}).mappings())
        reviews = list(c.execute(text("""SELECT review_event_id,source_run_id,phase_event_id,verified_phase,
            assessment_index,method_index,revision,disposition,grade,evidence_json,
            reviewer_id,rationale,evidence_reviewed_at,created_at,supersedes_event_id
            FROM medical_assessment_review_events
            WHERE nct_id=:nct ORDER BY created_at,review_event_id"""),
            {"nct":nct}).mappings())
        gaps = list(c.execute(text("""SELECT gap_event_id,source_run_id,assessment_index,
            method_index,gap_code,evidence_note,recorded_at
            FROM medical_assessment_gap_events WHERE nct_id=:nct
            ORDER BY recorded_at,gap_event_id"""), {"nct":nct}).mappings())
    review_rows = [dict(r) for r in reviews]
    for r in review_rows:
        r["evidence"] = json.loads(r.pop("evidence_json"))
    return {"nct":nct,"sourceRunId":roster["source_run_id"],
            "sourceCompletedAt":roster["source_completed_at"],
            "phaseStatus":"REVIEWED" if phases else "NOT_VERIFIED",
            "phaseEvents":[dict(r) for r in phases],
            "scientificGradeStatus":"PROVISIONAL" if reviews else "NOT_REVIEWED",
            "reviewEvents":review_rows,
            "explicitGapEvents":[dict(r) for r in gaps],
            "potentialMethodPositions":ASSESSMENTS * METHODS,
            "scientificSignoff":False,"fdaPrediction":"ABSTAIN",
            "certainty":"NOT_VALIDATED"}


def _run(engine, nct: str, run_id: str) -> None:
    from . import medical_continuous as source
    source.check_nct(nct)
    with engine.connect() as c:
        row = c.execute(text("""SELECT r.status,COUNT(s.stage_index) AS total
            FROM medical_continuous_runs r
            LEFT JOIN medical_continuous_stages s ON s.run_id=r.run_id
            WHERE r.run_id=:run AND r.nct_id=:nct
            GROUP BY r.status"""), {"run":run_id,"nct":nct}).first()
    if row is None or row[0] != "COMPLETE" or int(row[1]) != SOURCE_RUN_STAGES:
        raise ValueError("A saved, complete 12-stage source run is required")


def record_verified_phase(engine, *, nct: str, run_id: str, phase: str,
                          reviewer_id: str, verified_at: str,
                          supersedes_event_id: str | None = None) -> str:
    """Named human adjudication only; never called by source batch startup."""
    _reviewer(reviewer_id)
    if phase not in PHASES:
        raise ValueError("An exact phase is required")
    datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
    _run(engine,nct,run_id)
    with engine.begin() as c:
        stage = c.execute(text("""SELECT document FROM medical_continuous_stages
            WHERE run_id=:run AND stage_index=0"""), {"run":run_id}).scalar()
        if stage is None:
            raise ValueError("Original registry identity stage is missing")
        details = json.loads(stage)
        if (details.get("nct") != nct or
                details.get("source") != f"https://clinicaltrials.gov/study/{nct}"):
            raise ValueError("Phase confirmation requires the exact NCT registry identity")
        if phase not in details.get("phases", []):
            raise ValueError("Verified phase must match the saved original registry phase")
        source_url = _url(details.get("source", ""))
        if (urlparse(source_url).hostname or "").lower() not in ("clinicaltrials.gov", "www.clinicaltrials.gov"):
            raise ValueError("Phase confirmation requires the original registry source")
        previous = c.execute(text("""SELECT phase_event_id FROM medical_assessment_phase_events
            WHERE nct_id=:nct ORDER BY created_at DESC,phase_event_id DESC LIMIT 1"""),
            {"nct":nct}).scalar()
        if previous != supersedes_event_id:
            raise ValueError("Phase revision must explicitly supersede the latest event")
        event_id = str(uuid.uuid4())
        c.execute(text("""INSERT INTO medical_assessment_phase_events
            (phase_event_id,nct_id,source_run_id,verified_phase,original_registry_url,
             source_stage_sha256,reviewer_id,verified_at,created_at,supersedes_event_id)
            VALUES(:id,:nct,:run,:phase,:url,:digest,:reviewer,:verified,:created,:previous)"""),
            {"id":event_id,"nct":nct,"run":run_id,"phase":phase,"url":source_url,
             "digest":hashlib.sha256(stage.encode("utf-8")).hexdigest(),
             "reviewer":reviewer_id,"verified":verified_at,"created":now(),
             "previous":supersedes_event_id})
    return event_id


def append_review(engine, *, nct: str, run_id: str, phase_event_id: str,
                  assessment_index: int, method_index: int, disposition: str,
                  grade: int | None, evidence: list[dict], rationale: str,
                  reviewer_id: str, evidence_reviewed_at: str,
                  supersedes_event_id: str | None = None) -> str:
    """Append-only, evidence-provenanced review; no inferred or bulk grades."""
    _run(engine,nct,run_id)
    _position(assessment_index,method_index)
    _reviewer(reviewer_id)
    datetime.fromisoformat(evidence_reviewed_at.replace("Z", "+00:00"))
    if disposition not in DISPOSITIONS:
        raise ValueError("Invalid evidence disposition")
    if disposition == "SCORED":
        if type(grade) is not int or not 0 <= grade <= 5 or not evidence:
            raise ValueError("Scored tests require grade 0–5 and captured original source evidence")
    elif grade is not None:
        raise ValueError("Non-scored tests cannot carry a numerical grade")
    if not isinstance(rationale,str) or not 20 <= len(rationale.strip()) <= 6000:
        raise ValueError("Independent method-level scientific rationale is required")
    if not isinstance(evidence,list) or len(evidence)>12:
        raise ValueError("At most twelve original source evidence links per method")
    with engine.begin() as c:
        phase = c.execute(text("""SELECT verified_phase,nct_id FROM medical_assessment_phase_events
            WHERE phase_event_id=:id"""), {"id":phase_event_id}).first()
        if not phase or phase[1]!=nct:
            raise ValueError("A matching reviewer-verified phase is required")
        captures = []
        for item in evidence:
            if not isinstance(item,dict):
                raise ValueError("Evidence must identify an original source stage")
            index = item.get("stageIndex")
            if type(index) is not int or not 0 <= index < SOURCE_RUN_STAGES:
                raise ValueError("Source evidence must reference a recorded stage 0–11")
            url = _url(item.get("sourceUrl"))
            document = c.execute(text("""SELECT document FROM medical_continuous_stages
                WHERE run_id=:run AND stage_index=:idx"""),
                {"run":run_id,"idx":index}).scalar()
            if document is None or url not in _source_urls(json.loads(document)):
                raise ValueError("Source URL is not present in the immutable saved source stage")
            captures.append({"stageIndex":index,"sourceUrl":url,
                             "stageDocumentSha256":hashlib.sha256(
                                 document.encode("utf-8")).hexdigest()})
        previous = c.execute(text("""SELECT review_event_id,revision FROM medical_assessment_review_events
            WHERE nct_id=:nct AND verified_phase=:phase AND
            assessment_index=:assessment AND method_index=:method
            ORDER BY revision DESC LIMIT 1"""),
            {"nct":nct,"phase":phase[0],"assessment":assessment_index,
             "method":method_index}).first()
        if (previous[0] if previous else None) != supersedes_event_id:
            raise ValueError("Method revision must explicitly supersede latest recorded grade")
        if disposition == "RETRACTED" and not previous:
            raise ValueError("A retraction requires an existing recorded review")
        event_id = str(uuid.uuid4())
        c.execute(text("""INSERT INTO medical_assessment_review_events
            (review_event_id,nct_id,source_run_id,phase_event_id,verified_phase,
             assessment_index,method_index,revision,disposition,grade,evidence_json,
             reviewer_id,rationale,evidence_reviewed_at,created_at,supersedes_event_id)
            VALUES(:id,:nct,:run,:phase_id,:phase,:assessment,:method,:revision,:disposition,
                   :grade,:evidence,:reviewer,:rationale,:reviewed,:created,:previous)"""),
            {"id":event_id,"nct":nct,"run":run_id,"phase_id":phase_event_id,
             "phase":phase[0],"assessment":assessment_index,"method":method_index,
             "revision":int(previous[1])+1 if previous else 1,"disposition":disposition,
             "grade":grade,"evidence":json.dumps(captures,sort_keys=True),
             "reviewer":reviewer_id,"rationale":rationale.strip(),
             "reviewed":evidence_reviewed_at,"created":now(),
             "previous":supersedes_event_id})
    return event_id


def append_evidence_gap(engine, *, nct: str, run_id: str, assessment_index: int,
                        method_index: int | None, gap_code: str, evidence_note: str) -> str:
    _run(engine,nct,run_id)
    _position(assessment_index,method_index)
    if not isinstance(gap_code,str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,79}",gap_code):
        raise ValueError("A bounded missing-evidence classification is required")
    if not isinstance(evidence_note,str) or not 15 <= len(evidence_note.strip()) <= 4000:
        raise ValueError("A precise evidence gap explanation is required")
    event_id = str(uuid.uuid4())
    with engine.begin() as c:
        c.execute(text("""INSERT INTO medical_assessment_gap_events
            (gap_event_id,nct_id,source_run_id,assessment_index,method_index,
             gap_code,evidence_note,recorded_at)
            VALUES(:id,:nct,:run,:assessment,:method,:code,:note,:recorded)"""),
            {"id":event_id,"nct":nct,"run":run_id,"assessment":assessment_index,
             "method":method_index,"code":gap_code,"note":evidence_note.strip(),
             "recorded":now()})
    return event_id


def install_routes(app, engine_provider, require_key, require_storage) -> None:
    """Authenticated read only; an independent reviewer workflow is not installed."""
    router = APIRouter(prefix="/api/internal/medical-assessments",
                       dependencies=[Depends(require_key),Depends(require_storage)])

    @router.get("/coverage")
    def get_coverage():
        return coverage(engine_provider())

    @router.get("/{nct}/history")
    def get_history(nct: str):
        try:
            return trial_history(engine_provider(),nct)
        except ValueError:
            raise HTTPException(422, "Invalid exact trial identity")
        except LookupError:
            raise HTTPException(404, "Trial assessment roster not found")

    @router.get("/{nct}/matrix")
    def get_matrix(nct: str, assessmentIndex: int | None = None):
        """Read-only current-phase projection; optional 20-method drill-down."""
        from .medical_method_projection import project_trial_history
        try:
            return project_trial_history(trial_history(engine_provider(), nct),
                                         assessment_index=assessmentIndex)
        except ValueError:
            raise HTTPException(422, "Exact trial and assessment 1–40 are required")
        except LookupError:
            raise HTTPException(404, "Trial assessment roster not found")

    app.include_router(router)
