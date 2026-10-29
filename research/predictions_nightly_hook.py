"""Optional hook for a nightly scan orchestrator.

Nothing is scheduled or enabled by importing this module. The production
scan orchestration must explicitly call it after its trial feeds refresh.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from research.predictions_background_scheduler import schedule_eligible_predictions
from research.predictions_background_worker import run_queued_prediction_jobs


def after_nightly_scan(
    job_directory: str | Path,
    candidate_rows: Iterable[Mapping],
    evidence_provider: Callable[[str], Mapping],
    *,
    enabled: bool = False,
    max_new_jobs: int = 25,
    max_processed_jobs: int = 10,
) -> dict:
    """Queue eligible trials and process bounded jobs only with explicit opt-in."""
    if not enabled:
        return {
            "status": "DISABLED",
            "schedule": {"status": "DISABLED", "queued": [], "skipped": []},
            "worker": {"status": "DISABLED", "processed": [], "errors": []},
        }
    schedule = schedule_eligible_predictions(
        job_directory, candidate_rows, enabled=True, max_new_jobs=max_new_jobs,
    )
    worker = run_queued_prediction_jobs(
        job_directory, evidence_provider, enabled=True, max_jobs=max_processed_jobs,
    )
    return {"status": "FINISHED", "schedule": schedule, "worker": worker}
