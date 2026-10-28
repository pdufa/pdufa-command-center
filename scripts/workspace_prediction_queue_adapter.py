"""Read-only adapter for actual workspace candidate records.

No summary-count synthesis. Only explicitly identified GEM JR, GEM, WT rows
are admitted. Ambiguous membership or absent Phase 3 evidence remains unknown.
"""
from collections.abc import Mapping
from typing import Any
from scripts.build_priority_prediction_queue import build_initial_queue

STAGE_NAMES = {"GEM_JR": "GEM JR", "GEM": "GEM", "WT": "WT"}


def workspace_to_priority_queue(payload: Mapping[str, Any]) -> dict:
    """Accept explicit list arrays from a workspace export; fail closed otherwise.

    Expected input: {"lists": {"GEM_JR": [...], "GEM": [...], "WT": [...]}}.
    Each row needs program_id or id. Never infer list membership from score.
    """
    lists = payload.get("lists")
    if not isinstance(lists, Mapping):
        return {"status": "SOURCE_SCHEMA_UNVERIFIED", "reason": "Missing explicit lists mapping",
                "queue": [], "trading_ready": False}
    rows = []
    missing_groups = []
    for stage, label in STAGE_NAMES.items():
        members = lists.get(stage)
        if not isinstance(members, list):
            missing_groups.append(stage)
            continue
        for item in members:
            if not isinstance(item, Mapping):
                continue
            key = item.get("program_id") or item.get("id")
            if not isinstance(key, str) or not key.strip():
                continue
            rows.append({**item, "program_id": key.strip(), "list_name": label})
    result = build_initial_queue(rows)
    result["source_groups_missing"] = missing_groups
    result["status"] = "SOURCE_PARTIAL" if missing_groups else "CLASSIFICATION_QUEUE_BUILT"
    result["source_records_accepted"] = len(rows)
    result["source_verification_required"] = True
    return result
