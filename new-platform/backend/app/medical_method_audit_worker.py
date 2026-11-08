"""Durable, exact-trial execution receipts for existing 800-position SOURCE TRIAGE.

This is NOT a prediction, medical scoring, independent clinical review, or an
evidence retrieval worker. It audits each saved Stage-4 triage position in
order, persisting the observed classification/position and progress.
No reviewer phase, grade, source-run, or FOCUS roster writes are permitted.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

LOG = logging.getLogger(__name__)
NCT = "NCT06081894"
VERSION = "MAIN_PILOT_800_SOURCE_AUDIT_V1"
TOTAL = 800
STATES = {"PENDING", "RUNNING", "COMPLETE", "FAILED"}
CLASSES = {"SOURCE_RECORD_UNADJUDICATED", "RESEARCH_LEADS_ONLY",
           "IDENTITY_ONLY_NO_CLINICAL_DATA", "SOURCE_GAP",
           "NO_MATCHING_SAVED_SOURCE"}
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="medical-source-800")
_LOCK = threading.RLock()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def initialize(engine, *, test_only=False):
    """Additive only, isolated PostgreSQL required outside test fixtures."""
    if engine.dialect.name != "postgresql" and not test_only:
        raise RuntimeError("800-position pilot source audit requires isolated PostgreSQL")
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_pilot_method_audit_runs (
            run_id TEXT PRIMARY KEY,
            nct_id TEXT NOT NULL,
            source_snapshot_id TEXT NOT NULL,
            source_input_sha256 TEXT NOT NULL,
            catalog_sha256 TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('PENDING','RUNNING','COMPLETE','FAILED')),
            processed_methods INTEGER NOT NULL DEFAULT 0 CHECK (processed_methods BETWEEN 0 AND 800),
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            finished_at TEXT,
            failure_kind TEXT,
            UNIQUE(nct_id,source_snapshot_id))"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_pilot_method_audit_events (
            run_id TEXT NOT NULL REFERENCES medical_pilot_method_audit_runs(run_id),
            position_index INTEGER NOT NULL CHECK (position_index BETWEEN 1 AND 800),
            assessment_index INTEGER NOT NULL CHECK (assessment_index BETWEEN 1 AND 40),
            method_index INTEGER NOT NULL CHECK (method_index BETWEEN 1 AND 20),
            source_class TEXT NOT NULL,
            source_count INTEGER NOT NULL CHECK (source_count >= 0),
            observed_at TEXT NOT NULL,
            PRIMARY KEY(run_id,position_index),
            UNIQUE(run_id,assessment_index,method_index))"""))
        c.execute(text("""CREATE INDEX IF NOT EXISTS medical_pilot_audit_nct_latest
            ON medical_pilot_method_audit_runs(nct_id,started_at)"""))


def _exact(nct):
    if nct != NCT:
        raise ValueError("The 800-source-audit pilot is restricted to NCT06081894")


def _saved_source(engine, nct):
    from .medical_scientific_triage import latest
    record = latest(engine, nct)
    if (record.get("nct") != nct or record.get("methodPositions") != TOTAL or
            record.get("assessmentCount") != 40 or not record.get("snapshotId") or
            not re.fullmatch(r"[a-f0-9]{64}",str(record.get("sourceInputSha256",""))) or
            not re.fullmatch(r"[a-f0-9]{64}",str(record.get("catalogSha256",""))) or
            not isinstance(record.get("assessments"),list) or
            len(record["assessments"]) != 40 or record.get("scientificSignoff") is not False or
            record.get("fdaPredictions") != {"APPROVAL":"ABSTAIN","CRL":"ABSTAIN",
                                              "REVIEW_DELAY":"ABSTAIN"}):
        raise RuntimeError("Saved 800-position triage is incomplete, invalid or adjudicated")
    return record


def _get_saved_by_snapshot(engine, nct, snapshot_id):
    with engine.connect() as c:
        row = c.execute(text("""SELECT output_json FROM medical_scientific_triage_snapshots
            WHERE nct_id=:nct AND snapshot_id=:snapshot"""),
            {"nct":nct,"snapshot":snapshot_id}).first()
    if row is None:
        raise LookupError("Audit source snapshot no longer accessible")
    record = json.loads(row[0])
    if (record.get("nct")!=nct or record.get("methodPositions")!=TOTAL or
            record.get("scientificSignoff") is not False or
            record.get("fdaPredictions")!={"APPROVAL":"ABSTAIN","CRL":"ABSTAIN","REVIEW_DELAY":"ABSTAIN"}):
        raise ValueError("Source snapshot does not match exact unaudited trial")
    return record


def _validated_positions(record):
    rows=[]
    assessments=record.get("assessments")
    if not isinstance(assessments,list) or len(assessments)!=40:
        raise ValueError("Expected 40 saved assessment groups")
    for ai,assessment in enumerate(assessments,start=1):
        methods=assessment.get("methods") if isinstance(assessment,dict) else None
        if not isinstance(methods,list) or len(methods)!=20:
            raise ValueError("Every assessment must have 20 method source positions")
        for mi,method in enumerate(methods,start=1):
            if not isinstance(method,dict) or method.get("methodIndex")!=mi:
                raise ValueError("Source positions not in catalog order")
            cls=method.get("sourceClassification")
            count=method.get("sourceCount")
            if (cls not in CLASSES or type(count) is not int or count<0 or
                    not isinstance(method.get("sourceLeads"),list) or
                    len(method["sourceLeads"])!=count):
                raise ValueError("Invalid method-level source classification")
            # This is source-capture verification, never a grade validation or grade write.
            rows.append((ai,mi,cls,count))
    if len(rows)!=TOTAL:
        raise ValueError("Not all 800 source positions were available")
    return rows


def run(engine, run_id):
    """Complete the actual audit once, recording one real position per event.

    Not paced for UI animation. A fast run can complete before the first poll.
    """
    try:
        with _LOCK:
            with engine.connect() as c:
                meta=c.execute(text("""SELECT nct_id,source_snapshot_id,
                    source_input_sha256,catalog_sha256,status FROM medical_pilot_method_audit_runs
                    WHERE run_id=:run"""),{"run":run_id}).mappings().first()
            if not meta or meta["status"]=="COMPLETE":
                return
            _exact(meta["nct_id"])
            record=_get_saved_by_snapshot(engine,meta["nct_id"],meta["source_snapshot_id"])
            if (record.get("sourceInputSha256")!=meta["source_input_sha256"] or
                    record.get("catalogSha256")!=meta["catalog_sha256"]):
                raise ValueError("Original source/catalog digest changed")
            positions=_validated_positions(record)
            with engine.begin() as c:
                done=c.execute(text("""SELECT processed_methods
                    FROM medical_pilot_method_audit_runs WHERE run_id=:run"""),
                    {"run":run_id}).scalar_one()
                checked=c.execute(text("""SELECT COUNT(*) FROM medical_pilot_method_audit_events
                    WHERE run_id=:run"""),{"run":run_id}).scalar_one()
                if done!=checked or done%20 or done<0 or done>TOTAL:
                    raise RuntimeError("Cannot resume a partial or inconsistent source-audit batch")
                c.execute(text("""UPDATE medical_pilot_method_audit_runs SET status='RUNNING',
                    updated_at=:now,failure_kind=NULL WHERE run_id=:run AND status IN ('PENDING','RUNNING','FAILED')"""),
                    {"now":stamp(),"run":run_id})
            # One committed assessment batch at a time. No fake delays or grades.
            for start in range(done,TOTAL,20):
                with engine.begin() as c:
                    for pos in range(start,start+20):
                        ai,mi,cls,count=positions[pos]
                        c.execute(text("""INSERT INTO medical_pilot_method_audit_events
                          (run_id,position_index,assessment_index,method_index,source_class,source_count,observed_at)
                          VALUES(:run,:pos,:a,:m,:cls,:count,:now)
                          ON CONFLICT(run_id,position_index) DO NOTHING"""),
                          {"run":run_id,"pos":pos+1,"a":ai,"m":mi,
                           "cls":cls,"count":count,"now":stamp()})
                    verified=c.execute(text("""SELECT COUNT(*) FROM medical_pilot_method_audit_events
                        WHERE run_id=:run"""),{"run":run_id}).scalar_one()
                    if verified!=start+20:
                        raise RuntimeError("Pilot audit event coverage is not contiguous")
                    c.execute(text("""UPDATE medical_pilot_method_audit_runs
                        SET processed_methods=:done,updated_at=:now
                        WHERE run_id=:run AND status='RUNNING'"""),
                        {"done":verified,"now":stamp(),"run":run_id})
            with engine.begin() as c:
                count=c.execute(text("SELECT COUNT(*) FROM medical_pilot_method_audit_events WHERE run_id=:run"),
                                {"run":run_id}).scalar_one()
                if count!=TOTAL:
                    raise RuntimeError("Incomplete pilot method audit")
                c.execute(text("""UPDATE medical_pilot_method_audit_runs
                    SET status='COMPLETE',processed_methods=800,updated_at=:now,
                        finished_at=:now WHERE run_id=:run"""),{"run":run_id,"now":stamp()})
    except Exception as exc:
        LOG.error("MAIN_800_SOURCE_AUDIT_FAILED error_type=%s",type(exc).__name__)
        try:
            with engine.begin() as c:
                c.execute(text("""UPDATE medical_pilot_method_audit_runs SET status='FAILED',
                    updated_at=:now,failure_kind=:kind WHERE run_id=:run AND status!='COMPLETE'"""),
                    {"now":stamp(),"kind":type(exc).__name__[:64],"run":run_id})
        except Exception:
            LOG.exception("Failed to persist source-audit failure class")


def _row(engine,nct):
    with engine.connect() as c:
        return c.execute(text("""SELECT run_id,nct_id,source_snapshot_id,status,
            processed_methods,started_at,updated_at,finished_at,failure_kind
            FROM medical_pilot_method_audit_runs WHERE nct_id=:nct
            ORDER BY started_at DESC,run_id DESC LIMIT 1"""),{"nct":nct}).mappings().first()


def snapshot(engine,nct):
    _exact(nct)
    row=_row(engine,nct)
    if row is None:raise LookupError("No 800-position audit run recorded")
    with engine.connect() as c:
        events=c.execute(text("""SELECT position_index,assessment_index,method_index,
            source_class,source_count,observed_at FROM medical_pilot_method_audit_events
            WHERE run_id=:run ORDER BY position_index DESC LIMIT 6"""),
            {"run":row["run_id"]}).mappings().all()
        count=c.execute(text("""SELECT COUNT(*) FROM medical_pilot_method_audit_events
            WHERE run_id=:run"""),{"run":row["run_id"]}).scalar_one()
    if count!=row["processed_methods"]:
        # Concurrent read between event commit and count-update (same transaction),
        # or corrupted records: never claim completion.
        raise RuntimeError("Audit progress ledger inconsistent")
    next_index=count+1 if count<TOTAL else None
    status=row["status"]
    if status=="COMPLETE" and count!=TOTAL:raise RuntimeError("Completed run lacks 800 evidence checks")
    return {
      "schema":VERSION,"nct":nct,"runId":row["run_id"],"sourceSnapshotId":row["source_snapshot_id"],
      "status":status,"completedPositions":count,"totalPositions":TOTAL,
      "completedAssessmentGroups":count//20,
      "currentAssessmentIndex":(next_index-1)//20+1 if next_index is not None else None,
      "currentMethodIndex":(next_index-1)%20+1 if next_index is not None else None,
      "createdAt":row["started_at"],"updatedAt":row["updated_at"],"finishedAt":row["finished_at"],
      "failureKind":row["failure_kind"],
      "recentEvents":[dict(v) for v in events],
      "auditKind":"SAVED_TRIAGE_SOURCE_CLASSIFICATION_VERIFICATION",
      "scientificReviewEventsWritten":0,"gradeEventsWritten":0,
      "prediction":{"APPROVAL":"ABSTAIN","CRL":"ABSTAIN","REVIEW_DELAY":"ABSTAIN"},
      "accuracy":"NOT_CALIBRATED",
      "note":"This run checks saved method-source classifications. It is not 800 clinical grades or an FDA probability."}


def start(engine,nct,*,submit=True):
    _exact(nct)
    record=_saved_source(engine,nct)
    _validated_positions(record) # refuse incomplete source packet before any write
    rid=str(uuid.uuid5(uuid.NAMESPACE_URL, VERSION+":"+nct+":"+record["snapshotId"]))
    with _LOCK:
        with engine.begin() as c:
            c.execute(text("""INSERT INTO medical_pilot_method_audit_runs
                (run_id,nct_id,source_snapshot_id,source_input_sha256,catalog_sha256,
                 status,processed_methods,started_at,updated_at)
                VALUES(:run,:nct,:source,:digest,:catalog,'PENDING',0,:now,:now)
                ON CONFLICT(nct_id,source_snapshot_id) DO NOTHING"""),
                {"run":rid,"nct":nct,"source":record["snapshotId"],
                 "digest":record["sourceInputSha256"],"catalog":record["catalogSha256"],
                 "now":stamp()})
        snap=snapshot(engine,nct)
        if submit and snap["runId"]==rid and snap["status"]!="COMPLETE":
            _EXECUTOR.submit(run,engine,rid)
    return snap


def resume_pending(engine):
    """Restart incomplete exact canary runs, but never create a run on startup."""
    with engine.connect() as c:
        ids=list(c.execute(text("""SELECT run_id FROM medical_pilot_method_audit_runs
            WHERE nct_id=:nct AND status IN ('PENDING','RUNNING')"""),{"nct":NCT}).scalars())
    for rid in ids:_EXECUTOR.submit(run,engine,rid)
    return len(ids)


def install_routes(app,engine_provider,require_read_key,require_write_key,require_storage):
    router=APIRouter(prefix="/api/internal/medical-method-audit")
    @router.get("/{nct}/latest",dependencies=[Depends(require_read_key),Depends(require_storage)])
    def read_latest(nct:str):
        try:return snapshot(engine_provider(),nct)
        except ValueError:raise HTTPException(422,"Exact canary trial required")
        except LookupError:raise HTTPException(404,"No recorded pilot audit")
        except Exception as exc:
            LOG.warning("Pilot method audit read failed error_type=%s",type(exc).__name__)
            raise HTTPException(503,"Pilot audit status unavailable")

    @router.post("/{nct}/runs",dependencies=[Depends(require_write_key),Depends(require_storage)])
    def create_run(nct:str):
        try:return start(engine_provider(),nct)
        except ValueError:raise HTTPException(422,"Exact canary or source packet invalid")
        except LookupError:raise HTTPException(409,"Original saved source triage required")
        except Exception as exc:
            LOG.warning("Pilot method audit launch failed error_type=%s",type(exc).__name__)
            raise HTTPException(503,"Pilot source audit unavailable")
    app.include_router(router)
