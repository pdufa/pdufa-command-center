"""Read-only cohort-level inventory for real historical FDA evidence collection.

Reports missing source classes and intake coverage without making approval
predictions or consulting outcome records.
"""
from __future__ import annotations

from typing import Any

from .historical_source_intake import validate_historical_source_intake

_PRIMARY = frozenset({"FDA", "CLINICALTRIALS_GOV", "SEC",
                      "SPONSOR_RELEASE", "PEER_REVIEWED",
                      "CONFERENCE_ABSTRACT"})


def summarize_historical_intake(
    manifest: dict[str, Any], source_records: list[dict[str, Any]]
) -> dict[str, Any]:
    if not isinstance(manifest, dict) or not isinstance(source_records, list):
        raise TypeError("Manifest must be a dict and source records a list")
    trials = manifest.get("trials")
    trials = trials if isinstance(trials, list) else []
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[tuple[Any, Any, Any]] = set()
    for index, trial in enumerate(trials):
        if not isinstance(trial, dict):
            errors.append(f"TRIAL_{index}_INVALID_RECORD")
            continue
        key = tuple(trial.get(field) for field in ("nct_id", "application_id", "indication"))
        if key in seen:
            errors.append(f"TRIAL_{index}_DUPLICATE_EVENT")
        seen.add(key)
        records = [record for record in source_records if isinstance(record, dict) and
                   tuple(record.get(field) for field in ("nct_id", "application_id", "indication")) == key]
        try:
            intake = validate_historical_source_intake(records, trial.get("cutoff_on"))
            intake_errors = intake["errors"]
        except ValueError:
            intake_errors = ["INVALID_CUTOFF"]
        types = sorted({record.get("source_type") for record in records
                        if isinstance(record.get("source_type"), str)})
        has_fda = "FDA" in types
        has_trial_registry = "CLINICALTRIALS_GOV" in types
        missing = [name for name, present in
                   (("FDA", has_fda), ("CLINICALTRIALS_GOV", has_trial_registry))
                   if not present]
        rows.append({
            "nct_id": trial.get("nct_id"),
            "application_id": trial.get("application_id"),
            "indication": trial.get("indication"),
            "source_count": len(records),
            "source_types": types,
            "missing_priority_source_types": missing,
            "intake_metadata_valid": not intake_errors,
            "errors": intake_errors,
        })
    for index, record in enumerate(source_records):
        if not isinstance(record, dict):
            errors.append(f"SOURCE_{index}_INVALID_RECORD")
            continue
        key = tuple(record.get(field) for field in ("nct_id", "application_id", "indication"))
        if key not in seen:
            errors.append(f"SOURCE_{index}_UNMATCHED_EVENT")
    return {
        "trial_count": len(trials),
        "source_count": len(source_records),
        "trial_inventory": rows,
        "intake_metadata_complete": bool(rows) and not errors and all(
            row["intake_metadata_valid"] and not row["missing_priority_source_types"]
            for row in rows
        ),
        "scientific_status": "NOT_VERIFIED",
        "accuracy_evaluated": False,
        "errors": sorted(set(errors)),
    }
