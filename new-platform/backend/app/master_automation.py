"""Checkpointed, fail-closed PDUFA controller state machine.

No orders, background execution, workflow dispatch, or automatic production edits
occur in this module. GitHub run conclusions and source evidence are supplied by
a separately authenticated runner. State transitions are deterministic and testable.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
RUN_KEY = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{3,79}$")
WORKER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{5,95}$")

# First integrated lane: the source collection and FOCUS publication already
# provide strict final artifacts. Later lanes remain visible but NOT_WIRED
# until their evidence/adapters are independently reviewed. Never equate a
# scheduled workflow with a verified finished scientific assessment.
STAGES = (
    {"id": "POOL", "label": "Overnight POOL / clinical sources",
     "needs": (), "workflow": "pdufa-overnight-sequential.yml", "kind": "MANAGED"},
    {"id": "FOCUS", "label": "Full-POOL qualification and FOCUS sync",
     "needs": ("POOL",), "workflow": "p3-post-data-google-sheet-sync.yml", "kind": "MANAGED"},
    {"id": "ASSESSMENTS", "label": "Scientific assessments",
     "needs": ("FOCUS",), "workflow": None, "kind": "NOT_WIRED"},
    {"id": "PREDICTIONS", "label": "Predictions and calibration",
     "needs": ("ASSESSMENTS",), "workflow": None, "kind": "NOT_WIRED"},
    {"id": "CAL_NEWS", "label": "Calendar, company, and news",
     "needs": ("PREDICTIONS",), "workflow": None, "kind": "NOT_WIRED"},
    {"id": "ATSMS", "label": "Alpaca market-monitoring (separate schedule)",
     "needs": ("FOCUS",), "workflow": "atsms-focus-market-monitor.yml", "kind": "OBSERVE_ONLY"},
    {"id": "ALERTS", "label": "Message and signal delivery",
     "needs": ("CAL_NEWS",), "workflow": None, "kind": "NOT_WIRED"},
    {"id": "BACKUPS", "label": "Backup and recovery (independent)",
     "needs": (), "workflow": "pdufa-phase3-google-drive-backup.yml", "kind": "INDEPENDENT"},
)
INDEX = {s["id"]: s for s in STAGES}
MANAGED = tuple(s["id"] for s in STAGES if s["kind"] == "MANAGED")
STAGE_IDS = tuple(INDEX)
assert set(MANAGED) == {"POOL", "FOCUS"}


class ControllerBase(DeclarativeBase):
    pass


class ControllerRun(ControllerBase):
    __tablename__ = "master_automation_runs"
    __table_args__ = (UniqueConstraint("run_key", name="uq_master_automation_run_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_key: Mapped[str] = mapped_column(String(80), nullable=False)
    source_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def utcnow():
    return datetime.now(timezone.utc)


def new_state(run_key: str, source_sha: str, now=None):
    if not RUN_KEY.fullmatch(run_key) or not SHA.fullmatch(source_sha):
        raise ValueError("A unique run key and exact commit SHA are required")
    stamp = (now or utcnow()).isoformat()
    return {
        "runId": str(uuid4()), "runKey": run_key, "sourceSha": source_sha,
        "createdAt": stamp, "updatedAt": stamp, "generation": 1,
        "stages": {
            s["id"]: {"status": "PENDING" if s["kind"] == "MANAGED"
                      else "NOT_WIRED" if s["kind"] == "NOT_WIRED"
                      else "OBSERVE_ONLY", "attempts": 0,
                      "inputDigest": None, "outputDigest": None,
                      "workflowRunId": None, "worker": None,
                      "leaseUntil": None, "errorCode": None,
                      "updatedAt": stamp}
            for s in STAGES
        },
        "events": [{"event": "RUN_CREATED", "at": stamp}],
    }


def _append_event(state, event, now, **data):
    state["updatedAt"] = now.isoformat()
    state["events"] = (state["events"] + [{"event": event, "at": now.isoformat(), **data}])[-120:]


def _needs_complete(state, stage):
    return all(state["stages"][required]["status"] == "SUCCEEDED"
               for required in INDEX[stage]["needs"])


def _input_digest(state, stage):
    # Exact source revision and upstream validated outputs bind the checkpoint.
    source = [state["sourceSha"], stage]
    for required in INDEX[stage]["needs"]:
        source.append(required + ":" + str(state["stages"][required]["outputDigest"]))
    return hashlib.sha256("|".join(source).encode()).hexdigest()


def descendants(stage):
    if stage not in INDEX:
        raise ValueError("Unknown stage")
    found = set()
    frontier = [stage]
    while frontier:
        item = frontier.pop()
        for s in STAGES:
            if item in s["needs"] and s["id"] not in found:
                found.add(s["id"])
                frontier.append(s["id"])
    return found


def _blocked_dependents(state, failed_stage, now):
    for key in descendants(failed_stage):
        row = state["stages"][key]
        if INDEX[key]["kind"] == "MANAGED" and row["status"] == "PENDING":
            row["status"] = "BLOCKED"
            row["updatedAt"] = now.isoformat()


def claim(state, stage, worker, now=None):
    """Claim ONLY a ready, managed stage. Expired leases require explicit recovery."""
    now = now or utcnow()
    if stage not in MANAGED or not WORKER.fullmatch(worker):
        raise ValueError("Unmanaged stage or invalid worker")
    row = state["stages"][stage]
    if row["status"] != "PENDING" or not _needs_complete(state, stage):
        raise ValueError("Stage is not ready; use explicit resume on failures")
    row.update(status="RUNNING", attempts=row["attempts"] + 1,
               inputDigest=_input_digest(state, stage), outputDigest=None,
               workflowRunId=None, worker=worker,
               leaseUntil=(now + timedelta(hours=4)).isoformat(),
               errorCode=None, updatedAt=now.isoformat())
    _append_event(state, "CLAIMED", now, stage=stage, attempt=row["attempts"])
    return state


def finish(state, stage, worker, conclusion, workflow_run_id, evidence_digest=None,
           error_code=None, now=None):
    now = now or utcnow()
    if stage not in MANAGED or not WORKER.fullmatch(worker):
        raise ValueError("Unknown managed stage or worker")
    row = state["stages"][stage]
    if row["status"] != "RUNNING" or row["worker"] != worker:
        raise ValueError("Stage lease is not held by this worker")
    if datetime.fromisoformat(row["leaseUntil"]) < now:
        raise ValueError("Lease expired; a manual recovery is required")
    # A failed dispatch may have no correlated run ID; success never may.
    if (not isinstance(workflow_run_id, int) or workflow_run_id < 0 or
            (conclusion == "SUCCEEDED" and workflow_run_id < 1)):
        raise ValueError("A correlated GitHub run ID is required for success")
    if row["inputDigest"] != _input_digest(state, stage):
        raise ValueError("An upstream checkpoint changed while executing")
    if conclusion == "SUCCEEDED":
        if not isinstance(evidence_digest, str) or not DIGEST.fullmatch(evidence_digest):
            raise ValueError("A verified output artifact digest is required")
        row.update(status="SUCCEEDED", outputDigest=evidence_digest,
                   errorCode=None)
    elif conclusion == "FAILED":
        if not isinstance(error_code, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", error_code):
            raise ValueError("A safe, explicit failure code is required")
        row.update(status="FAILED", outputDigest=None, errorCode=error_code)
        _blocked_dependents(state, stage, now)
    else:
        raise ValueError("Only SUCCEEDED/FAILED are valid final states")
    row.update(workflowRunId=workflow_run_id, worker=None, leaseUntil=None,
               updatedAt=now.isoformat())
    _append_event(state, conclusion, now, stage=stage, workflowRunId=workflow_run_id)
    return state


def fail_expired_lease(state, stage, now=None):
    """Manual recovery gate: never steal or replay an active worker's stage."""
    now = now or utcnow()
    if stage not in MANAGED:
        raise ValueError("Unknown managed stage")
    row = state["stages"][stage]
    if row["status"] != "RUNNING" or not row["leaseUntil"]:
        raise ValueError("No running lease to recover")
    if datetime.fromisoformat(row["leaseUntil"]) >= now:
        raise ValueError("The current worker lease has not expired")
    row.update(status="FAILED", outputDigest=None, errorCode="LEASE_EXPIRED",
               worker=None, leaseUntil=None, updatedAt=now.isoformat())
    _blocked_dependents(state, stage, now)
    _append_event(state, "LEASE_EXPIRED", now, stage=stage)
    return state


def resume(state, failed_stage, now=None):
    """Reset precisely the failed stage and managed descendants; keep valid parents."""
    now = now or utcnow()
    if failed_stage not in MANAGED:
        raise ValueError("Only an integrated managed stage can be resumed")
    if state["stages"][failed_stage]["status"] != "FAILED":
        raise ValueError("The requested resume point must be FAILED")
    if not _needs_complete(state, failed_stage):
        raise ValueError("Prior checkpoints are not valid")
    for key in {failed_stage} | descendants(failed_stage):
        if INDEX[key]["kind"] != "MANAGED":
            continue
        row = state["stages"][key]
        if row["status"] == "RUNNING":
            raise ValueError("Refuse resume while a dependent lease is active")
        row.update(status="PENDING", inputDigest=None, outputDigest=None,
                   workflowRunId=None, worker=None, leaseUntil=None,
                   errorCode=None, updatedAt=now.isoformat())
    state["generation"] += 1
    _append_event(state, "RESUMED_FROM_FAILURE", now, stage=failed_stage,
                  generation=state["generation"])
    return state


def status(state):
    rows = state["stages"]
    if any(rows[k]["status"] == "FAILED" for k in MANAGED):
        return "FAILED"
    if any(rows[k]["status"] == "RUNNING" for k in MANAGED):
        return "RUNNING"
    if all(rows[k]["status"] == "SUCCEEDED" for k in MANAGED):
        return "MANAGED_STAGES_COMPLETE"
    if any(rows[k]["status"] == "BLOCKED" for k in MANAGED):
        return "BLOCKED"
    return "READY"


def public(state, version):
    return {
        "id": state["runId"], "runKey": state["runKey"],
        "sourceSha": state["sourceSha"], "version": version,
        "status": status(state), "generation": state["generation"],
        "createdAt": state["createdAt"], "updatedAt": state["updatedAt"],
        "stages": [
            {"id": item["id"], "label": item["label"], "needs": list(item["needs"]),
             "workflow": item["workflow"], "integration": item["kind"],
             **state["stages"][item["id"]]}
            for item in STAGES
        ],
        "events": state["events"][-40:],
        "fullEndToEndCertified": False,
        "tradingOrdersEnabled": False,
    }
