"""Read-only status summary for a historical source research worklist.

Never treats a user-entered status as proof of evidence provenance. Only
metadata checks from the intake inventory can establish intake readiness.
"""
from __future__ import annotations

from typing import Any

from .historical_intake_inventory import summarize_historical_intake
from .historical_research_worklist import build_historical_research_worklist


def summarize_historical_collection_progress(
    manifest: dict[str, Any], source_records: list[dict[str, Any]]
) -> dict[str, Any]:
    inventory = summarize_historical_intake(manifest, source_records)
    worklist = build_historical_research_worklist(manifest, source_records)
    rows = inventory["trial_inventory"]
    return {
        "trial_count": inventory["trial_count"],
        "source_metadata_record_count": inventory["source_count"],
        "trials_with_priority_source_metadata": sum(
            not row["missing_priority_source_types"] for row in rows
        ),
        "trials_with_valid_intake_metadata": sum(
            row["intake_metadata_valid"] for row in rows
        ),
        "trials_requiring_review": sum(
            bool(row["missing_priority_source_types"]) or not row["intake_metadata_valid"]
            for row in rows
        ),
        "open_collection_tasks": worklist["task_count"],
        "source_bytes_verified": False,
        "collection_executed": False,
        "scientific_status": "NOT_VERIFIED",
        "accuracy_evaluated": False,
        "errors": sorted(set(inventory["errors"] + worklist["errors"])),
    }
