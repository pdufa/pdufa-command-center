"""Read-only audit of historical GEM/GEM JR trial-reference *candidates*.

The archived stage snapshot is NOT the current published GEM/GEM JR membership
and a field named "nct_id" on an APPLICATION|... row is a *hint* rather than
an approved regulatory-to-trial association. A pipe-delimited field may cite
multiple trials. Never collapse it to one arbitrary study.

Pure Python: no database operations, network, import, scoring, or preset writes.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any

NCT_RE = re.compile(r"NCT[0-9]{8}\Z")
TRIAL_RE = re.compile(r"TRIAL\|(NCT[0-9]{8})\Z")
SOURCE_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
STAGES = ("GEM", "GEM_JR")
MAX_ROWS = 50000
MAX_NCTS_PER_PROGRAM = 8


def _iso_date(value: Any) -> date:
    if not isinstance(value, str) or not SOURCE_DATE_RE.fullmatch(value):
        raise ValueError("Snapshot date must be ISO YYYY-MM-DD")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Malformed calendar date")
    return parsed


def _nct_hints(raw: Any) -> list[str]:
    if raw is None or raw == "":
        return []
    if not isinstance(raw, str) or len(raw) > 160:
        raise ValueError("Trial hints must be a bounded pipe-delimited string")
    parts = raw.split("|")
    if (not 1 <= len(parts) <= MAX_NCTS_PER_PROGRAM
            or any(not NCT_RE.fullmatch(x) for x in parts)
            or len(parts) != len(set(parts))):
        raise ValueError("Trial hint contains invalid/duplicate NCT identity")
    return parts


def audit_historical_crosswalk(
    snapshot: Any,
    *,
    reference_date: str,
    archived_nct_ids: Any,
    freshness_days: int = 2,
) -> dict:
    """Inspect historical stage snapshots and archive NCT coverage, no writes."""
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1:
        raise ValueError("Expected saved historical stage snapshot version 1")
    stages = snapshot.get("stages")
    if not isinstance(stages, dict) or any(k not in stages for k in STAGES):
        raise ValueError("Both historical GEM and GEM_JR lists are required")
    if not isinstance(freshness_days, int) or not 0 <= freshness_days <= 7:
        raise ValueError("Bounded freshness policy required")
    ref = _iso_date(reference_date)
    if not isinstance(archived_nct_ids, (set, list, tuple)):
        raise ValueError("Archived identities must be explicitly supplied")
    archive = set()
    for value in archived_nct_ids:
        if not isinstance(value, str) or not NCT_RE.fullmatch(value):
            raise ValueError("Invalid archived exact NCT reference")
        archive.add(value)
    records = []
    for stage in STAGES:
        stage_info = stages[stage]
        if not isinstance(stage_info, dict):
            raise ValueError("Invalid saved stage details")
        snap_date = _iso_date(stage_info.get("last_complete_snapshot"))
        age = (ref - snap_date).days
        if age < 0:
            raise ValueError("Future saved stage date cannot be considered current")
        entries = stage_info.get("entries")
        if not isinstance(entries, dict) or len(entries) > MAX_ROWS:
            raise ValueError("Historical stage members missing or oversized")
        for key, entry in sorted(entries.items()):
            if not isinstance(key, str) or len(key) > 240 or not isinstance(entry, dict):
                raise ValueError("Invalid saved stage entry")
            if not key.startswith(("TRIAL|", "APPLICATION|", "RESULT|")):
                raise ValueError("Unexpected saved program source type")
            if entry.get("pipeline_id") != key:
                raise ValueError("Published stage key and entry identity conflict")
            if entry.get("status") not in ("ACTIVE", "LEFT"):
                raise ValueError("Saved stage status unavailable")
            hints = _nct_hints(entry.get("nct_id"))
            m = TRIAL_RE.fullmatch(key)
            if key.startswith("TRIAL|") and (not m or hints != [m.group(1)]):
                raise ValueError("Direct TRIAL source cannot contradict exact NCT")
            if any(not isinstance(entry.get(x, ""), str)
                   for x in ("first_found", "last_seen")):
                raise ValueError("Malformed historical appearance dates")
            records.append({
                "stage": stage,
                "source_key": key,
                "status_at_snapshot": entry["status"],
                "snapshot_as_of": snap_date.isoformat(),
                "snapshot_age_days": age,
                "current_membership_verified": False,
                "source_type": key.split("|", 1)[0],
                "hinted_nct_ids": hints,
                "archive_matched_nct_ids": sorted(n for n in hints if n in archive),
                "archive_missing_nct_ids": sorted(n for n in hints if n not in archive),
                "association_status": (
                    "DIRECT_TRIAL_SOURCE_IDENTITY_ONLY" if m else
                    "APPLICATION_TRIAL_ASSOCIATION_REQUIRES_REVIEW" if hints else
                    "NO_EXACT_TRIAL_HINT"
                ),
                "scientifically_verified": False,
                "automatic_crosswalk_performed": False,
            })
    hinted = sorted({n for item in records for n in item["hinted_nct_ids"]})
    matching = sorted(n for n in hinted if n in archive)
    missing = sorted(n for n in hinted if n not in archive)
    age_days = {
        stage: (ref - _iso_date(stages[stage]["last_complete_snapshot"])).days
        for stage in STAGES
    }
    return {
        "schema_version": "science-historical-crosswalk-candidates-v1",
        "mode": "read_only_historical_audit",
        "reference_date": reference_date,
        "snapshot_dates": {
            stage: stages[stage]["last_complete_snapshot"] for stage in STAGES
        },
        "snapshot_ages_days": age_days,
        "historical_snapshot_only": True,
        "current_membership_verified": False,
        "freshness_lapsed": any(d > freshness_days for d in age_days.values()),
        "historical_entries": len(records),
        "one_trial_hint_entries": sum(
            len(x["hinted_nct_ids"]) == 1 for x in records
        ),
        "multi_trial_hint_entries": sum(
            len(x["hinted_nct_ids"]) > 1 for x in records
        ),
        "no_trial_hint_entries": sum(
            not x["hinted_nct_ids"] for x in records
        ),
        "direct_trial_source_entries": sum(
            x["association_status"] == "DIRECT_TRIAL_SOURCE_IDENTITY_ONLY"
            for x in records
        ),
        "application_trial_review_queue": sum(
            x["association_status"] == "APPLICATION_TRIAL_ASSOCIATION_REQUIRES_REVIEW"
            for x in records
        ),
        "distinct_hinted_trials": len(hinted),
        "distinct_archived_hinted_trials": len(matching),
        "missing_archive_nct_ids": missing,
        "suggested_automatic_import_batches": [],
        "independently_verified_clinical_sources": 0,
        "approved_regulatory_trial_crosswalks": 0,
        "fda_approval_probability": None,
        "import_executed": False,
        "presets_modified": False,
        "records": records,
        "note": (
            "A historical application NCT field is a candidate crosswalk, not "
            "approved trial membership. Archive presence establishes only "
            "record availability; scientific, source and FDA adjudication "
            "remain separate. Multi-trial references must not be silently "
            "collapsed into one trial or auto-imported."
        ),
    }
