"""Opt-in bounded background evidence worker, not a validated predictor.

A real scheduler must call run_queued_prediction_jobs and provide a real
trial evidence provider. No scheduler or network access is activated here.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path

from research.prediction_job_store import load_job
from research.predictions_execution_adapter import execute_existing_job


def run_queued_prediction_jobs(
    directory: str | Path,
    evidence_provider: Callable[[str], Mapping],
    *,
    enabled: bool = False,
    max_jobs: int = 10,
) -> dict:
    if not enabled:
        return {"status": "DISABLED", "processed": [], "errors": []}
    if not 1 <= max_jobs <= 100:
        raise ValueError("max_jobs must be between 1 and 100")
    root = Path(directory)
    if not root.is_dir():
        return {"status": "NO_JOBS", "processed": [], "errors": []}
    processed, errors = [], []
    for path in sorted(root.glob("*.json")):
        if len(processed) + len(errors) >= max_jobs:
            break
        try:
            job = load_job(root, path.stem)
            if job.get("status") != "QUEUED":
                continue
            evidence = evidence_provider(job["trial_id"])
            if not isinstance(evidence, Mapping):
                raise ValueError("Evidence provider must return a mapping")
            outcome = execute_existing_job(root, job["job_id"], evidence)
            processed.append({
                "job_id": job["job_id"],
                "trial_id": job["trial_id"],
                "status": outcome["job"]["status"],
                "decision": outcome["prediction"]["decision"],
            })
        except (ValueError, KeyError, OSError, json.JSONDecodeError, TypeError) as exc:
            errors.append({"job_file": path.name, "error": type(exc).__name__})
    return {"status": "FINISHED", "processed": processed, "errors": errors}
