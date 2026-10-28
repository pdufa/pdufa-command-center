"""Deterministic, read-only initial queue for Phase-3-ready GEM JR/GEM/WT programs.

Does not modify list membership, infer FDA decisions, or authorize trading.
Input rows come from existing list exports; absent data is not invented.
"""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any

LIST_PRIORITY = {"GEM JR": 0, "GEM": 1, "WT": 2}
CLASSIFICATION_FIELDS = (
    "therapeutic_area", "indication", "disease_subtype", "treatment_setting",
    "drug_modality", "mechanism", "regulatory_pathway", "development_stage",
    "trial_design", "population", "primary_endpoint", "efficacy",
    "safety", "statistical_design", "comparator", "regulatory_history",
    "evidence_maturity", "manufacturing_risk",
)
PHASE3_RELEASED = {"phase3_results_released", "phase3_results_published"}


def build_initial_queue(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Deduplicate by stable program identity, retain memberships and unknowns.

    Requires explicit evidence status; a Phase 3 start or topline expectation
    is not equivalent to released results. Never assigns prediction scores.
    """
    unique: dict[str, dict[str, Any]] = {}
    skipped: dict[str, int] = {}
    for row in rows:
        group = str(row.get("list_name") or "").strip().upper()
        key = str(row.get("program_id") or "").strip()
        if group not in LIST_PRIORITY or not key:
            reason = "invalid_group_or_program_id"
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        if key not in unique:
            unique[key] = {
                "program_id": key,
                "lists": [],
                "classification": {field: None for field in CLASSIFICATION_FIELDS},
                "phase3_evidence_status": "unknown",
                "prediction_status": "not_started",
                "missing_classification_fields": list(CLASSIFICATION_FIELDS),
            }
        item = unique[key]
        if group not in item["lists"]:
            item["lists"].append(group)
        for field in CLASSIFICATION_FIELDS:
            value = row.get(field)
            if isinstance(value, str) and value.strip() and item["classification"][field] is None:
                item["classification"][field] = value.strip()
        status = str(row.get("phase3_evidence_status") or "").strip().lower()
        if status in PHASE3_RELEASED:
            item["phase3_evidence_status"] = status
        elif status and item["phase3_evidence_status"] == "unknown":
            item["phase3_evidence_status"] = status
    for item in unique.values():
        item["lists"].sort(key=LIST_PRIORITY.__getitem__)
        item["missing_classification_fields"] = [
            f for f, v in item["classification"].items() if v is None
        ]
        item["eligible_for_first_pass"] = item["phase3_evidence_status"] in PHASE3_RELEASED
        item["requires_source_verification"] = True
    queue = sorted(unique.values(), key=lambda x: (
        not x["eligible_for_first_pass"],
        min(LIST_PRIORITY[g] for g in x["lists"]),
        len(x["missing_classification_fields"]),
        x["program_id"],
    ))
    return {
        "status": "classification_queue_only",
        "unique_program_count": len(queue),
        "phase3_results_released_count": sum(x["eligible_for_first_pass"] for x in queue),
        "skipped_rows": skipped,
        "prediction_model_validated": False,
        "trading_ready": False,
        "queue": queue,
    }
