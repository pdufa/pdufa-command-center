"""Research-only opt-in batch scheduling for eligible prediction candidates.

Invoked by an external scheduler. No autonomous execution or invented results.
"""
from __future__ import annotations

from pathlib import Path
from collections.abc import Iterable, Mapping

from research.predictions_job_adapter import latest_trial_job, start_prediction_job
from research.predictions_tab import eligible_trials


def schedule_eligible_predictions(
    job_directory: str | Path,
    candidate_rows: Iterable[Mapping],
    *,
    enabled: bool = False,
    max_new_jobs: int = 25,
) -> dict:
    """Queue candidates without duplicating existing queued/running jobs.

    Completed/blocked jobs are not automatically repeated; explicit manual
    refresh policy must be defined before rescheduling.
    """
    if not enabled:
        return {"status": "DISABLED", "queued": [], "skipped": []}
    if not 1 <= max_new_jobs <= 100:
        raise ValueError("max_new_jobs must be between 1 and 100")
    queued, skipped = [], []
    for trial in eligible_trials(candidate_rows):
        trial_id = trial["trial_id"]
        existing = latest_trial_job(job_directory, trial_id)
        if existing is not None:
            skipped.append({"trial_id": trial_id, "reason": f"EXISTING_{existing['status']}"})
            continue
        if len(queued) >= max_new_jobs:
            skipped.append({"trial_id": trial_id, "reason": "BATCH_LIMIT"})
            continue
        job = start_prediction_job(job_directory, trial_id)
        queued.append({"trial_id": trial_id, "job_id": job["job_id"]})
    return {"status": "QUEUED" if queued else "NO_NEW_JOBS", "queued": queued, "skipped": skipped}
