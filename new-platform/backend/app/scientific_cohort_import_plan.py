"""Pure, offline, read-only prioritization of exact-NCT science archive transfers.

This module NEVER connects to any database, fetches a registry URL, imports a
trial, enables a scan, schedules work, or writes a source archive. It only
produces a deterministic proposed manifest from an explicit approved source
inventory with separately authenticated list memberships.

A valid manifest is NOT evidence verification, readiness to score, a forecast,
or permission to execute an import.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

NCT_RE = re.compile(r"NCT[0-9]{8}\Z")
SHA_RE = re.compile(r"[a-fA-F0-9]{64}\Z")
COHORTS = ("WT", "GEM", "GEM_JR")
PHASES = frozenset(("PHASE1", "PHASE2", "PHASE3", "PHASE4", "EARLY_PHASE1", "NA"))
PVAL_STATES = frozenset(("REPORTED", "NOT_REPORTED", "NO_POSTED_RESULTS"))
MAX_BATCH = 25
MAX_ROWS = 50000
MAX_INPUT_BYTES = 16_000_000


def _parse_row(row: Any) -> dict:
    if not isinstance(row, dict):
        raise ValueError("Every inventory row must be an object")
    nct = row.get("nct_id")
    cohorts = row.get("cohorts")
    phases = row.get("phases")
    source_hash = row.get("source_sha256")
    has_results = row.get("has_posted_results")
    pval = row.get("p_value_status")
    if not isinstance(nct, str) or not NCT_RE.fullmatch(nct):
        raise ValueError("Exact NCT identity required")
    if not isinstance(cohorts, list) or not cohorts or any(
        not isinstance(x, str) or x not in COHORTS for x in cohorts
    ) or len(cohorts) != len(set(cohorts)):
        raise ValueError("Every trial requires distinct, validated GEM JR/GEM/WT membership")
    if not isinstance(phases, list) or any(
        not isinstance(x, str) or x not in PHASES for x in phases
    ) or len(phases) != len(set(phases)):
        raise ValueError("Phases must be a distinct, recognized registry phase list")
    if type(has_results) is not bool or pval not in PVAL_STATES:
        raise ValueError("Registry results presence and p-value status required")
    if not isinstance(source_hash, str) or not SHA_RE.fullmatch(source_hash):
        raise ValueError("Archived source SHA-256 must be present")
    if not has_results and pval != "NO_POSTED_RESULTS":
        raise ValueError("P-value state contradicts no posted results")
    if has_results and pval == "NO_POSTED_RESULTS":
        raise ValueError("P-value state contradicts posted results")
    return {
        "nct_id": nct,
        "cohorts": sorted(cohorts, key=COHORTS.index),
        "phases": sorted(phases),
        "has_posted_results": has_results,
        "p_value_status": pval,
        "source_sha256": source_hash.lower(),
    }


def plan_from_inventory(rows: Any) -> dict:
    """Return a proposed read-only transfer plan; never start an import."""
    if not isinstance(rows, list) or not rows or len(rows) > MAX_ROWS:
        raise ValueError("Provide 1-50,000 explicit archive inventory rows")
    by_nct: dict[str, dict] = {}
    for row in rows:
        item = _parse_row(row)
        existing = by_nct.get(item["nct_id"])
        if existing is None:
            by_nct[item["nct_id"]] = item
            continue
        # Duplicate memberships for the *same exact source* are permitted.
        # Different source hashes or contradictory evidence are never merged.
        for field in ("phases", "has_posted_results", "p_value_status", "source_sha256"):
            if existing[field] != item[field]:
                raise ValueError("Conflicting source snapshot for exact NCT identity")
        existing["cohorts"] = sorted(
            set(existing["cohorts"]) | set(item["cohorts"]), key=COHORTS.index
        )
    items = list(by_nct.values())
    # WT, then GEM, then GEM JR. Within each cohort prioritize phase 3/4,
    # posted results, then source p-value presence, all with a stable NCT tie.
    def key(item: dict) -> tuple:
        stage = min(COHORTS.index(c) for c in item["cohorts"])
        phase_34 = bool({"PHASE3", "PHASE4"} & set(item["phases"]))
        return (stage, not phase_34, not item["has_posted_results"],
                item["p_value_status"] != "REPORTED", item["nct_id"])
    items.sort(key=key)
    canonical = json.dumps(items, sort_keys=True, separators=(",", ":"))
    proposed_batches = [
        {
            "batch_number": i // MAX_BATCH + 1,
            "nct_ids": [entry["nct_id"] for entry in items[i:i + MAX_BATCH]],
            "operator_approval_required": True,
            "executed": False,
        }
        for i in range(0, len(items), MAX_BATCH)
    ]
    return {
        "schema_version": "science-archive-transfer-plan-v1",
        "mode": "read_only_proposal",
        "source_dataset": "prevalidated_exact_trial_membership_and_archived_registry_metadata",
        "snapshot_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "input_rows": len(rows),
        "unique_trials": len(items),
        "with_phase_3_or_4": sum(
            bool({"PHASE3", "PHASE4"} & set(item["phases"])) for item in items
        ),
        "with_posted_results": sum(item["has_posted_results"] for item in items),
        "with_reported_pvalue_status": sum(
            item["p_value_status"] == "REPORTED" for item in items
        ),
        "cohort_memberships": {
            cohort: sum(cohort in item["cohorts"] for item in items) for cohort in COHORTS
        },
        "batch_limit": MAX_BATCH,
        "planned_batches": proposed_batches,
        "trials": items,
        "source_byte_hashes_independently_verified": False,
        "scientific_findings_independently_verified": 0,
        "analysis_grade": None,
        "reluctance_grade": None,
        "fda_approval_probability": None,
        "import_executed": False,
        "note": (
            "A source checksum field and a posted-result flag do not establish "
            "independent scientific evidence. No scientific import starts here. "
            "Each 25-trial batch requires separately authorized execution on "
            "the isolated scientific PostgreSQL service after identity, "
            "provenance, costs, and rollback checks."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True,
                        help="Explicitly exported UTF-8 JSON array; no remote fetch")
    parser.add_argument("--output", type=Path, required=True,
                        help="Local proposed plan path; no source or DB mutation")
    args = parser.parse_args(argv)
    try:
        if args.inventory.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError("Inventory exceeds bounded input limit")
        rows = json.loads(args.inventory.read_text(encoding="utf-8"))
        plan = plan_from_inventory(rows)
        # Do not overwrite a prior audit artifact, even with a different snapshot.
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(plan, stream, indent=2, sort_keys=True)
            stream.write("\n")
        print(json.dumps({
            "status": "DRY_RUN_ONLY",
            "unique_trials": plan["unique_trials"],
            "planned_batches": len(plan["planned_batches"]),
            "snapshot_sha256": plan["snapshot_sha256"],
            "import_executed": False,
        }, sort_keys=True))
        return 0
    except (ValueError, TypeError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        # Do not print input file paths or raw source data.
        print(json.dumps({"status": "PLAN_REJECTED", "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
