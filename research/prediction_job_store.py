"""Research-only durable prediction job store; no simulated background work.

A runner must explicitly update each assessment. JSON files are written
atomically and are not intended as a concurrent multiworker queue.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import tempfile
import uuid

STATUSES = {"NOT_STARTED", "RUNNING", "COMPLETED", "BLOCKED", "FAILED", "MISSING_EVIDENCE"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(directory: str | Path, trial_id: str, assessment_names: list[str]) -> dict:
    if not trial_id.strip() or not assessment_names or len(set(assessment_names)) != len(assessment_names):
        raise ValueError("Trial ID and unique assessments required")
    job = {
        "job_id": uuid.uuid4().hex,
        "trial_id": trial_id,
        "created_at_utc": _now(),
        "status": "QUEUED",
        "assessments": [
            {"title": name, "status": "NOT_STARTED", "details": "", "evidence": [], "uncertainty": ""}
            for name in assessment_names
        ],
    }
    save_job(directory, job)
    return job


def save_job(directory: str | Path, job: dict) -> None:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    job_id = job.get("job_id", "")
    if not isinstance(job_id, str) or len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
        raise ValueError("Invalid job ID")
    target = root / f"{job_id}.json"
    fd, temp_path = tempfile.mkstemp(prefix=".prediction-", suffix=".tmp", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(job, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, target)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def load_job(directory: str | Path, job_id: str) -> dict:
    if len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
        raise ValueError("Invalid job ID")
    return json.loads((Path(directory) / f"{job_id}.json").read_text(encoding="utf-8"))


def update_assessment(
    directory: str | Path, job_id: str, title: str, status: str, *,
    details: str = "", evidence: list[str] | None = None, uncertainty: str = "",
) -> dict:
    if status not in STATUSES:
        raise ValueError("Invalid assessment status")
    job = load_job(directory, job_id)
    matches = [row for row in job["assessments"] if row["title"] == title]
    if len(matches) != 1:
        raise ValueError("Assessment not found or ambiguous")
    row = matches[0]
    row.update(status=status, details=details, evidence=evidence or [], uncertainty=uncertainty)
    states = {entry["status"] for entry in job["assessments"]}
    job["status"] = (
        "COMPLETED" if states == {"COMPLETED"}
        else "BLOCKED" if "BLOCKED" in states or "MISSING_EVIDENCE" in states
        else "FAILED" if "FAILED" in states
        else "RUNNING" if "RUNNING" in states or "COMPLETED" in states
        else "QUEUED"
    )
    job["updated_at_utc"] = _now()
    save_job(directory, job)
    return job
