"""Explicit research-only execution adapter for PREDICTIONS.

No background scheduling, scientific model, or manufactured source data.
Upstream caller must provide actual sourced assessment records.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from research.prediction_assessment_runner import research_decision, run_evidence_checklist
from research.prediction_job_store import load_job
from research.predictions_job_adapter import start_prediction_job


def execute_prediction(
    directory: str | Path,
    trial_id: str,
    evidence_by_assessment: Mapping[str, Mapping],
    *,
    assessment_names=None,
) -> dict:
    """Create, process and return an inspectable job and conservative decision."""
    kwargs = {"assessment_names": assessment_names} if assessment_names is not None else {}
    job = start_prediction_job(directory, trial_id, **kwargs)
    result = run_evidence_checklist(directory, job["job_id"], evidence_by_assessment)
    return {"job": result, "prediction": research_decision(result)}


def execute_existing_job(
    directory: str | Path,
    job_id: str,
    evidence_by_assessment: Mapping[str, Mapping],
) -> dict:
    """Run a previously queued job; caller controls when execution occurs."""
    job = load_job(directory, job_id)
    if job["status"] != "QUEUED":
        raise ValueError("Only queued jobs may be executed")
    result = run_evidence_checklist(directory, job_id, evidence_by_assessment)
    return {"job": result, "prediction": research_decision(result)}
