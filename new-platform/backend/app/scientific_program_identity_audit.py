"""Pure, read-only exact trial identity coverage audit for WT, GEM and GEM JR.

A trading/qualification program is NOT necessarily a clinical trial.
Only an exact TRIAL|NCT######## identity may enter the science archive
transfer planner. Application-level or result-level programs are
quarantined for manual source-supported trial association.

No network, SQL, trial imports, approval scores, preset edits or writes.
"""
from __future__ import annotations
import re
from typing import Any

COHORTS = ("WT", "GEM", "GEM_JR")
TRIAL_SOURCE = re.compile(r"TRIAL\|(NCT[0-9]{8})\Z")
PROGRAM_ID = re.compile(r"PDUFA-[0-9]{6,}\Z")
NCT_ID = re.compile(r"NCT[0-9]{8}\Z")
MAX_ROWS = 50000


def audit_exact_programs(rows: Any) -> dict:
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError("Provide a bounded list of published exact program identities")
    programs: dict[str, dict] = {}
    for source in rows:
        if not isinstance(source, dict):
            raise ValueError("Program identity row must be an object")
        program_id = source.get("program_id")
        source_key = source.get("source_key")
        cohorts = source.get("cohorts")
        if not isinstance(program_id, str) or not PROGRAM_ID.fullmatch(program_id):
            raise ValueError("Permanent exact Program ID required")
        if not isinstance(source_key, str) or not source_key.strip():
            raise ValueError("Exact published source identity required")
        if not isinstance(cohorts, list) or not cohorts or any(
            not isinstance(c, str) or c not in COHORTS for c in cohorts
        ) or len(cohorts) != len(set(cohorts)):
            raise ValueError("Explicit distinct GEM JR/GEM/WT membership required")
        # Caller-supplied ticker, drug, inferred NCT or "approved" field
        # cannot turn an application-level program into a trial.
        proposed_nct = source.get("nct_id")
        match = TRIAL_SOURCE.fullmatch(source_key)
        if proposed_nct is not None and (
            not isinstance(proposed_nct, str)
            or not NCT_ID.fullmatch(proposed_nct)
            or match is None
            or proposed_nct != match.group(1)
        ):
            raise ValueError("Unreviewed or contradictory program-to-trial NCT mapping")
        existing = programs.get(program_id)
        if existing:
            if existing["source_key"] != source_key:
                raise ValueError("Permanent Program ID has conflicting source identities")
            existing["cohorts"] = sorted(
                set(existing["cohorts"]) | set(cohorts), key=COHORTS.index
            )
        else:
            programs[program_id] = {
                "program_id": program_id,
                "source_key": source_key,
                "cohorts": sorted(cohorts, key=COHORTS.index),
            }
    linked, unlinked = [], []
    for item in sorted(programs.values(), key=lambda r: r["program_id"]):
        m = TRIAL_SOURCE.fullmatch(item["source_key"])
        if m:
            linked.append({
                "program_id": item["program_id"],
                "nct_id": m.group(1),
                "cohorts": item["cohorts"],
                "identity_status": "EXACT_TRIAL_SOURCE_KEY",
                "scientifically_verified": False,
            })
        else:
            prefix = item["source_key"].split("|", 1)[0]
            unlinked.append({
                "program_id": item["program_id"],
                "cohorts": item["cohorts"],
                "source_type": prefix if prefix in ("APPLICATION", "RESULT")
                               else "OTHER_NON_TRIAL",
                "nct_id": None,
                "identity_status": "REQUIRES_MANUAL_TRIAL_CROSSWALK",
                "scientifically_verified": False,
            })
    return {
        "schema_version": "science-exact-program-identity-audit-v1",
        "mode": "read_only",
        "programs_checked": len(programs),
        "exact_trial_identity_links": len(linked),
        "unlinked_programs": len(unlinked),
        "cohort_coverage": {
            cohort: {
                "programs": sum(cohort in x["cohorts"] for x in programs.values()),
                "linked": sum(cohort in x["cohorts"] for x in linked),
                "unlinked": sum(cohort in x["cohorts"] for x in unlinked),
            }
            for cohort in COHORTS
        },
        "linked": linked,
        "manual_crosswalk_queue": unlinked,
        "automated_mapping_performed": False,
        "cohort_preset_modified": False,
        "scientific_scores_assigned": False,
        "fda_approval_probability": None,
        "note": (
            "Only exact TRIAL|NCT source identities are eligible for scientific "
            "trial-archive planning; application/result source types require "
            "manually verified many-to-many regulatory/trial crosswalks. "
            "An exact NCT is only an identity, not evidence adjudication."
        ),
    }
