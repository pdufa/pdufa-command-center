"""Offline source-identity reconciliation before any isolated science import.

Matches only exact program-to-NCT source keys to already archived main PDUFA
trial metadata. It never copies compressed trial blobs, imports a trial,
performs SQL/network operations, verifies clinical findings, or changes
GEM JR/GEM/WT qualification settings.
"""
from __future__ import annotations

from typing import Any

from .scientific_cohort_import_plan import NCT_RE, plan_from_inventory
from .scientific_program_identity_audit import audit_exact_programs


def reconcile_sources(program_rows: Any, archive_rows: Any) -> dict:
    """Build an exact-identity crosswalk and optional dry-run batch manifest."""
    audit = audit_exact_programs(program_rows)
    if not isinstance(archive_rows, list) or len(archive_rows) > 50000:
        raise ValueError("Use a bounded read-only archive metadata export")
    archived: dict[str, dict] = {}
    for row in archive_rows:
        if not isinstance(row, dict):
            raise ValueError("Archive metadata row must be an object")
        nct = row.get("nct_id")
        if not isinstance(nct, str) or not NCT_RE.fullmatch(nct):
            raise ValueError("Archive metadata requires exact NCT identity")
        if nct in archived:
            if archived[nct] != row:
                raise ValueError("Conflicting source snapshots for one archive identity")
            continue
        archived[nct] = row

    linked_rows, unavailable = [], []
    for match in audit["linked"]:
        nct = match["nct_id"]
        record = archived.get(nct)
        if record is None:
            unavailable.append({
                "program_id": match["program_id"], "nct_id": nct,
                "cohorts": match["cohorts"],
                "status": "SOURCE_ARCHIVE_NOT_FOUND",
            })
            continue
        linked_rows.append({
            "nct_id": nct,
            "cohorts": match["cohorts"],
            "phases": record.get("phases"),
            "has_posted_results": record.get("has_posted_results"),
            "p_value_status": record.get("p_value_status"),
            "source_sha256": record.get("source_sha256"),
        })
    # The planner validates each archive digest, registry phase, status and
    # corroborates any duplicate exact NCT identity before batching.
    plan = plan_from_inventory(linked_rows) if linked_rows else None
    return {
        "schema_version": "science-archive-reconciliation-v1",
        "mode": "read_only",
        "identity_audit": audit,
        "exact_identity_source_matched_programs": len(linked_rows),
        "exact_identity_source_missing_programs": unavailable,
        "proposed_plan": plan,
        "import_executed": False,
        "independent_scientific_review_complete": False,
        "fda_approval_probability": None,
        "note": (
            "Archive source metadata matched by exact NCT only. "
            "Application-level records require manual multi-trial adjudication; "
            "missing archives remain missing. Never infer a clinical result "
            "from presence of registry outcomes or p-value reports."
        ),
    }
