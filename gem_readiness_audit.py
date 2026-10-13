"""Deterministic, fail-closed GEM research readiness and source-coverage audit.

Never calls external sites, verifies historical returns, makes orders, or claims
full-universe coverage. Dated source data and zero-valued histories are visible.
"""
from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from gem_phase3_discovery import gem_discrimination_audit
from gem_scans import STAGES, TRADE_EXIT_DAYS_BEFORE_PDUFA

PACIFIC = ZoneInfo("America/Los_Angeles")
HISTORY_FILES = (
    "gem_historical_snapshots.csv",
    "post_phase3_historical_adjusted_ohlcv.csv",
)
REQUIRED_FILES = (
    "pdufa_candidates.csv",
    "step7_live_status.json",
    "step7_financing_review.csv",
    "second_financing_status.csv",
    "step7_market_status.csv",
    "phase3_announcements.csv",
)


def csv_inventory(path):
    p = Path(path)
    if not p.is_file():
        return {"state": "MISSING", "rows": 0}
    try:
        with p.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            header = reader.fieldnames
            if not header or not all(header) or len(set(header)) != len(header):
                return {"state": "INVALID_HEADER", "rows": 0}
            count = 0
            for row in reader:
                if None in row:
                    return {"state": "MALFORMED_ROW", "rows": count}
                count += 1
            return {"state": "PRESENT", "rows": count}
    except (OSError, UnicodeError, csv.Error):
        return {"state": "UNREADABLE", "rows": 0}


def clinical_collection_status(path, as_of):
    file = Path(path)
    if not file.is_file():
        return {"status": "NOT_RECORDED", "pacific_day": None, "age_days": None}
    try:
        obj = json.loads(file.read_text(encoding="utf-8"))
        stamp = datetime.fromisoformat(
            str(obj["finished_at"]).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("naive collection timestamp")
        pacific_day = stamp.astimezone(PACIFIC).date()
        age = (as_of - pacific_day).days
        completed = obj.get("complete") is True and obj.get("status") in (
            "COMPLETE", "COMPLETE WITH WARNINGS")
        label = ("FUTURE_TIMESTAMP" if age < 0 else
                 "PARTIAL_SOURCE_CHECK" if not completed else
                 "CURRENT_CLINICAL_ONLY" if age <= 1 else
                 "STALE_CLINICAL_ONLY")
        return {"status": label, "pacific_day": pacific_day.isoformat(),
                "age_days": age, "matched_posted_results": obj.get("matched_posted_results"),
                "stored_results": obj.get("stored_results"),
                "source_completed": completed}
    except (ValueError, TypeError, KeyError, OSError, AttributeError):
        return {"status": "UNVERIFIABLE", "pacific_day": None, "age_days": None}


def build_readiness_report(root, items, scan_status, discovery, discovery_status,
                           *, as_of=None):
    today = as_of or datetime.now(PACIFIC).date()
    if not isinstance(today, date) or isinstance(today, datetime):
        raise ValueError("as_of must be a date")
    p = Path(root)
    inputs = {name: ({"state": "PRESENT"} if name.endswith(".json") and
                       (p/name).is_file() else
                       {"state": "MISSING"} if name.endswith(".json") else
                       csv_inventory(p/name)) for name in REQUIRED_FILES}
    histories = {name: csv_inventory(p/name) for name in HISTORY_FILES}
    discovery_status = discovery_status or {}
    scan_status = scan_status or {}
    info = gem_discrimination_audit(items, STAGES)
    verified_tracking = [
        row for row in items
        if str(row.get("Phase 3 tracking", "")).startswith("TRACKING")
    ]
    qualified = {stage: info[stage]["qualified"] for stage in STAGES}
    source_stale = scan_status.get("feed_current") is not True
    history_complete = (histories[HISTORY_FILES[0]]["state"] == "PRESENT"
                        and histories[HISTORY_FILES[1]]["state"] == "PRESENT"
                        and histories[HISTORY_FILES[0]]["rows"] > 0
                        and histories[HISTORY_FILES[1]]["rows"] > 0)
    missing_required = [n for n, v in inputs.items()
                        if v["state"] != "PRESENT"]
    risks = []
    if source_stale:
        risks.append("CURRENT_RANKING_FEED_STALE_OR_UNVERIFIED")
    if missing_required:
        risks.append("REQUIRED_SAVED_INPUTS_MISSING_OR_INVALID")
    if discovery_status.get("unprocessed_due_to_limit"):
        risks.append("DISCOVERY_LEDGER_NOT_FULLY_PROCESSED")
    if discovery_status.get("ambiguous_duplicates"):
        risks.append("CONFLICTING_DISCOVERY_IDENTITIES_REQUIRE_REVIEW")
    if discovery_status.get("rejected_missing_or_future_evidence"):
        risks.append("DISCOVERY_SOURCE_TIMESTAMPS_REQUIRE_REVIEW")
    if not history_complete:
        risks.append("UNVALIDATED_HISTORICAL_STOCK_RETURNS")
    if any(v["status"] in ("NO_DISCRIMINATION_ALL_TIED",
                         "LIMITED_DISCRIMINATION") for v in info.values()):
        risks.append("RANKING_TIES_REDUCE_DISCRIMINATION")
    clinical = clinical_collection_status(p/"phase3_intake_status.json", today)
    if clinical["status"] != "CURRENT_CLINICAL_ONLY":
        risks.append("PHASE3_COLLECTOR_COVERAGE_NOT_CURRENTLY_VERIFIED")
    # A saved collector state may describe data retained only as a past
    # workflow artifact, while the current checkout has an empty CSV. A
    # "complete" collector badge must NOT mask missing discovery observations.
    ledger = inputs["phase3_announcements.csv"]
    stored_results = clinical.get("stored_results")
    source_ledger_reconciled = (
        ledger["state"] == "PRESENT" and
        isinstance(stored_results, int) and not isinstance(stored_results, bool) and
        stored_results == ledger["rows"]
    )
    if not source_ledger_reconciled:
        risks.append("PHASE3_RESULT_LEDGER_MISSING_OR_COUNT_MISMATCH")
    all_source_issues = bool(source_stale or missing_required or
                             not source_ledger_reconciled)
    return {
        "as_of_pacific": today.isoformat(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_status": ("HOLD_STALE_OR_MISSING_SOURCES"
                            if all_source_issues else
                            "RESEARCH_ONLY_RANKING_NOT_RETURN_VALIDATED"),
        "full_universe_coverage_verified": False,
        "historical_return_edge_validated": False,
        "live_weights_changed": False,
        "automated_trading_enabled": False,
        "exit_days_before_pdufa": TRADE_EXIT_DAYS_BEFORE_PDUFA,
        "saved_pipeline_events": len(items),
        "verified_phase3_tracking": len(verified_tracking),
        "awaiting_second_financing": sum(
            row.get("2nd Financing Completed") != "YES — VERIFIED (HISTORICAL)"
            for row in verified_tracking),
        "ranked": qualified,
        "ranking_discrimination": info,
        "discovery_review_leads": len(discovery),
        "discovery_source_status": discovery_status,
        "clinical_collector": clinical,
        "phase3_saved_ledger_reconciled": source_ledger_reconciled,
        "phase3_saved_ledger_rows": ledger["rows"],
        "phase3_collector_reported_stored_rows": stored_results,
        "required_source_inventory": inputs,
        "missing_required_inputs": missing_required,
        "historical_data_inventory": histories,
        "blocking_or_review_flags": risks,
        "limitations": [
            "Local saved source feeds are NOT continuous real-time discovery.",
            "A Phase 3 registry posting or issuer topline is not proof of success.",
            "A financing filing announcement is not proof of separate second close.",
            "PDUFA -3 is a research exit deadline, not an executed broker sale.",
            "A relative GEM rank is not a forecast of approval or equity return.",
            "No training or weight promotion from unverified or synthetic records.",
        ],
    }
