"""Pure offline research worklist export for historical FDA source collection.

Converts a validated collection plan to stable JSON-compatible rows; no
network, persistence, outcomes, predictions or implicit source discovery.
"""
from __future__ import annotations

from typing import Any

from .historical_collection_queue import plan_historical_source_collection


def build_historical_research_worklist(
    manifest: dict[str, Any], source_records: list[dict[str, Any]]
) -> dict[str, Any]:
    plan = plan_historical_source_collection(manifest, source_records)
    tasks: list[dict[str, Any]] = []
    for item in plan["tasks"]:
        tasks.append({
            "event_key": {
                "nct_id": item["nct_id"],
                "application_id": item["application_id"],
                "indication": item["indication"],
            },
            "source_type": item["source_type"],
            "action": item["task"],
            "status": "NOT_STARTED",
            "source_url": None,
            "published_on": None,
            "retrieved_on": None,
            "sha256": None,
            "availability": "UNVERIFIED",
            "notes": None,
        })
    return {
        "schema_version": "1",
        "collection_executed": False,
        "task_count": len(tasks),
        "tasks": tasks,
        "accuracy_evaluated": False,
        "scientific_status": "NOT_VERIFIED",
        "errors": plan["errors"],
    }
