"""Research-only adapter connecting PREDICTIONS UI to durable jobs.

Creates QUEUED jobs, not executing workers. External scientific runner must
claim and update assessments; no simulated progress or decisions.
"""
from __future__ import annotations

import json
from pathlib import Path

from research.prediction_job_store import create_job, load_job

DEFAULT_ASSESSMENTS = (
    "Phase 3 efficacy and endpoints",
    "Statistical analysis and multiplicity",
    "Safety and adverse events",
    "Trial design and protocol integrity",
    "FDA regulatory and review history",
    "Special designations and dates",
    "Manufacturing and CMC",
    "Historical comparable decisions",
    "Evidence completeness and uncertainty",
    "Integrated scientific decision assessment",
)


def start_prediction_job(directory: str | Path, trial_id: str, assessment_names=DEFAULT_ASSESSMENTS) -> dict:
    """Persist a queued job. This does not launch scientific computation."""
    return create_job(directory, trial_id, list(assessment_names))


def latest_trial_job(directory: str | Path, trial_id: str) -> dict | None:
    """Find latest saved job for a trial; ignore invalid/unrelated files."""
    root = Path(directory)
    if not root.is_dir():
        return None
    candidates = []
    for path in root.glob("*.json"):
        try:
            job = load_job(root, path.stem)
            if job.get("trial_id") == trial_id:
                candidates.append(job)
        except (ValueError, OSError, json.JSONDecodeError, KeyError, TypeError):
            continue
    return max(candidates, key=lambda item: (item.get("created_at_utc", ""), item["job_id"]), default=None)


def checklist_for_trial(directory: str | Path, trial_id: str) -> list[dict]:
    job = latest_trial_job(directory, trial_id)
    if job is None:
        return []
    return [dict(row, trial_id=trial_id) for row in job.get("assessments", [])]
