"""Durable, explicitly triggered scientific batch jobs for the isolated review service.

No scheduled execution, restart auto-resumption, credential logging, or production writes.
One unfinished batch globally, enforced by a PostgreSQL unique active-slot constraint.
"""
from __future__ import annotations

import re
import threading
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import main, scientific_batch_import

ACTIVE_SLOT = "scientific-import"
ID_PATTERN = re.compile(r"[0-9a-f]{32}\Z")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def validate_ids(ids: list[str]) -> list[str]:
    if (not isinstance(ids, list) or not 1 <= len(ids) <= scientific_batch_import.MAX_TRIALS
            or any(not isinstance(v, str) or
                   not scientific_batch_import.NCT_PATTERN.fullmatch(v) for v in ids)):
        raise ValueError("Specify 1-25 exact NCT identifiers")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate NCT identifier in batch")
    return ids


def _as_dict(job: main.ScientificBatchJob, *, include_events: bool = True) -> dict:
    result = {
        "id": job.id,
        "status": job.status,
        "nct_ids": job.nct_ids,
        "total": job.total,
        "processed": job.processed,
        "imported": job.imported,
        "already_exists": job.already_exists,
        "failed": job.failed,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
    if include_events:
        result["events"] = job.events or []
    return result


def list_jobs() -> list[dict]:
    with Session(main.ENGINE) as session:
        jobs = session.scalars(
            select(main.ScientificBatchJob)
            .order_by(main.ScientificBatchJob.created_at.desc())
            .limit(20)
        ).all()
        return [_as_dict(job, include_events=False) for job in jobs]


def recovery_diagnostics(*, now: datetime | None = None) -> dict:
    """Read-only diagnostics. A stale timestamp never proves a worker is stopped.

    Never automatically free a PostgreSQL active slot, restart, or retry a job.
    """
    reference = now or _now()
    threshold = reference - timedelta(minutes=60)
    with Session(main.ENGINE) as session:
        active = session.scalars(
            select(main.ScientificBatchJob)
            .where(main.ScientificBatchJob.active_slot == ACTIVE_SLOT)
            .limit(1)
        ).first()
        if active is None:
            return {"active_job": None, "potentially_interrupted": False,
                    "manual_review_required": False}
        job = _as_dict(active, include_events=False)
        stale = bool(active.updated_at and
                     (active.updated_at.replace(tzinfo=timezone.utc)
                      if active.updated_at.tzinfo is None else active.updated_at) < threshold)
        return {
            "active_job": job,
            "potentially_interrupted": stale,
            "manual_review_required": stale,
            "message": ("No automatic retry or unlock. Confirm the previous worker "
                        "has stopped before any operator-led reconciliation."
                        if stale else "An unfinished batch currently holds the exclusive slot."),
        }


def get_job(job_id: str) -> dict | None:
    if not ID_PATTERN.fullmatch(job_id):
        return None
    with Session(main.ENGINE) as session:
        job = session.get(main.ScientificBatchJob, job_id)
        return _as_dict(job) if job else None


def _update(job_id: str, *, event: dict | None = None,
            status: str | None = None, finished: bool = False) -> None:
    with Session(main.ENGINE) as session:
        job = session.get(main.ScientificBatchJob, job_id)
        if job is None:
            raise RuntimeError("Scientific batch job missing")
        now = _now()
        if event is not None and event.get("event") == "trial_finished":
            # Store only allowlisted, bounded values; never raw exception details.
            safe_event = {key: event[key] for key in (
                "index", "nct_id", "status", "error_type", "http_status"
            ) if key in event}
            job.events = [*(job.events or []), safe_event]
            job.processed = event["processed"]
            job.imported = event["imported"]
            job.already_exists = event["already_exists"]
            job.failed = event["failed"]
        if status is not None:
            job.status = status
        if finished:
            job.completed_at = now
            job.active_slot = None
        job.updated_at = now
        session.commit()


def _worker(job_id: str, ids: list[str]) -> None:
    """Persist progress after every trial; process interruption never auto-retries."""
    try:
        _update(job_id, status="running")

        def save_progress(event: dict) -> None:
            if event["event"] == "trial_finished":
                _update(job_id, event=event)

        summary = scientific_batch_import.run_batch(
            ids, emit=save_progress, delay_seconds=1.0
        )
        _update(job_id, status="completed_with_errors" if summary["failed"] else "completed",
                finished=True)
    except Exception:
        # Leave an observable interrupted state instead of leaking a secret/error
        # or silently restarting an import. A DB outage might prevent this update.
        try:
            _update(job_id, status="interrupted", finished=True)
        except Exception:
            pass


def submit_job(ids: list[str], *, start_worker: bool = True) -> dict:
    ids = validate_ids(ids)
    if not main.DATABASE_URL.startswith("postgresql+psycopg://"):
        raise RuntimeError("Persistent PostgreSQL required")
    now = _now()
    job_id = uuid.uuid4().hex
    with Session(main.ENGINE) as session:
        job = main.ScientificBatchJob(
            id=job_id, status="queued", nct_ids=list(ids), events=[],
            total=len(ids), processed=0, imported=0, already_exists=0,
            failed=0, active_slot=ACTIVE_SLOT, created_at=now, updated_at=now,
            completed_at=None,
        )
        session.add(job)
        session.commit()  # Unique active_slot produces IntegrityError on concurrent POST.
        result = _as_dict(job)
    if start_worker:
        try:
            threading.Thread(
                target=_worker, args=(job_id, list(ids)), daemon=True,
                name="scientific-review-batch-" + job_id[:8],
            ).start()
        except Exception:
            _update(job_id, status="interrupted", finished=True)
            raise
    return result
