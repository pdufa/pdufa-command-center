"""Deterministic, read-only queue of missing historical primary evidence.

This plans research work only. It does not fetch documents, score studies,
access FDA outcomes, or imply the requested documents are publicly available.
"""
from __future__ import annotations

from typing import Any

from .historical_intake_inventory import summarize_historical_intake


def plan_historical_source_collection(
    manifest: dict[str, Any], source_records: list[dict[str, Any]]
) -> dict[str, Any]:
    inventory = summarize_historical_intake(manifest, source_records)
    tasks: list[dict[str, Any]] = []
    for row in inventory["trial_inventory"]:
        for source_type in row["missing_priority_source_types"]:
            tasks.append({
                "nct_id": row["nct_id"],
                "application_id": row["application_id"],
                "indication": row["indication"],
                "source_type": source_type,
                "task": "VERIFY_AND_COLLECT_PRIMARY_SOURCE",
                "status": "NOT_STARTED",
                "public_availability": "UNKNOWN",
            })
        if not row["intake_metadata_valid"]:
            tasks.append({
                "nct_id": row["nct_id"],
                "application_id": row["application_id"],
                "indication": row["indication"],
                "source_type": "EXISTING_SOURCE_METADATA",
                "task": "REVIEW_SOURCE_PROVENANCE_AND_DATES",
                "status": "NOT_STARTED",
                "public_availability": "UNKNOWN",
            })
    return {
        "trial_count": inventory["trial_count"],
        "missing_source_task_count": len(tasks),
        "tasks": tasks,
        "collection_executed": False,
        "accuracy_evaluated": False,
        "scientific_status": "NOT_VERIFIED",
        "errors": inventory["errors"],
    }
