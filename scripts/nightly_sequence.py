"""Validate the completed source stage of an ongoing, awaited nightly run."""
from __future__ import annotations

WORKFLOW_NAME = "PDUFA Overnight Sequential Scans"
WORKFLOW_PATH = ".github/workflows/pdufa-overnight-sequential.yml"
RUN_TITLE = "POOL + PIPELINE — PDUFA overnight"
SOURCE_JOBS = tuple(f"Live PDUFA {family} source check" for family in
                    ("FDA", "SEC", "FINANCIAL", "MARKET", "ISSUER"))
SOURCE_TAILS = ("Combined coverage / missing source audit",
                "Publish reconciled source verification to SCANS",
                "Refresh source-labeled Step 7 EOD market snapshots",
                "Refresh validated PIPELINE early-clinical feed after sources / publish")
TERMINAL = {"success", "failure", "timed_out", "cancelled", "skipped"}


def completed_source_stage(run, jobs, *, current_run_id, conclusion, repository):
    """Never describe the still-running parent as a completed workflow."""
    if (str(run.get("id")) != str(current_run_id) or
            run.get("display_title") != RUN_TITLE or
            run.get("path", "").split("@", 1)[0] != WORKFLOW_PATH or
            run.get("head_branch") != "main" or
            (run.get("head_repository") or {}).get("full_name") != repository or
            run.get("status") != "in_progress" or conclusion not in TERMINAL):
        raise ValueError("Unverified active nightly parent or source-stage conclusion")
    source_jobs = [job for job in jobs if job.get("name", "").startswith("sources /")]
    for name in SOURCE_JOBS + SOURCE_TAILS:
        matches = [job for job in source_jobs if job.get("name", "").endswith("/ " + name)]
        if len(matches) != 1 or matches[0].get("status") != "completed":
            raise ValueError("Source stage is missing, ambiguous or still running: " + name)
    if not source_jobs or any(job.get("status") != "completed" for job in source_jobs):
        raise ValueError("Source publication or PIPELINE early-clinical refresh has not finished")
    if conclusion == "success" and any(job.get("conclusion") != "success" for job in source_jobs):
        raise ValueError("Failed or skipped source jobs cannot be reported as successful")
    failed_jobs = [{"id": job.get("id"), "name": job.get("name"),
                    "conclusion": job.get("conclusion")} for job in jobs
                   if job.get("status") == "completed" and
                   job.get("conclusion") in ("failure", "timed_out", "cancelled")]
    return {
        "run_id": run["id"], "workflow": WORKFLOW_NAME,
        "stage": "sources", "conclusion": conclusion,
        "parent_status": "in_progress", "trigger_event": run.get("event"),
        "created_at": run.get("created_at"),
        "completed_at": max((job.get("completed_at") or "" for job in source_jobs), default="") or None,
        "url": run.get("html_url"), "needs_attention": conclusion != "success" or bool(failed_jobs),
        "failed_parent_jobs": failed_jobs,
        "note": "Source jobs finished; the parent is still running scoring/error checks/repair. Source coverage remains independent.",
    }
