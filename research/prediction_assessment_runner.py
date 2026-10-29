"""Explicit, synchronous research assessment runner.

Runs only when invoked by a worker. Evidence must be supplied by trusted
upstream ingestion; absence is marked MISSING_EVIDENCE. No synthetic PoA.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from research.prediction_job_store import load_job, update_assessment


def run_evidence_checklist(
    directory: str | Path,
    job_id: str,
    evidence_by_assessment: Mapping[str, Mapping],
) -> dict:
    """Record evidence availability, not a scientific PASS/CRL judgment.

    The caller supplies independently collected evidence and must separately
    implement scientific reasoning and prospective validation.
    """
    job = load_job(directory, job_id)
    for row in job["assessments"]:
        title = row["title"]
        source = evidence_by_assessment.get(title)
        if not source or not source.get("source_urls") or not source.get("findings"):
            update_assessment(
                directory, job_id, title, "MISSING_EVIDENCE",
                details="No complete sourced findings available for this assessment.",
                uncertainty="Assessment cannot be completed.",
            )
            continue
        urls = source["source_urls"]
        findings = source["findings"]
        if not isinstance(urls, list) or not urls or not all(
            isinstance(url, str) and url.startswith("https://") for url in urls
        ):
            update_assessment(
                directory, job_id, title, "MISSING_EVIDENCE",
                details="Source references are missing or malformed.",
                uncertainty="Assessment cannot be completed.",
            )
            continue
        update_assessment(
            directory, job_id, title, "COMPLETED",
            details=str(findings),
            evidence=urls,
            uncertainty=str(source.get("uncertainty") or "Not independently quantified"),
        )
    return load_job(directory, job_id)


def research_decision(job: Mapping) -> dict:
    """Fail closed: evidence ingestion is not a calibrated prediction model."""
    assessments = job.get("assessments", [])
    completed = bool(assessments) and all(
        row.get("status") == "COMPLETED" for row in assessments
    )
    return {
        "decision": "ABSTAIN",
        "readiness": "EVIDENCE_RECORDED_MODEL_NOT_VALIDATED" if completed else "NOT_READY",
        "probabilities": None,
        "reason": "Scientific prediction and prospective calibration are not connected.",
    }
