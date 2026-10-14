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
from gem_runway_gate import MIN_MONTHS, PASS, HOLD, REVIEW

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


def json_inventory(path):
    file = Path(path)
    if not file.is_file():
        return {"state": "MISSING"}
    try:
        value = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not value:
            return {"state": "INVALID_JSON"}
        return {"state": "PRESENT"}
    except (OSError, UnicodeError, ValueError):
        return {"state": "INVALID_JSON"}


def source_family_health(path, name, as_of):
    """Read an actual source family's dated collection audit, not the UI badge."""
    try:
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        matches = [row for row in state.get("source_checks", [])
                   if row.get("Source") == name]
        if len(matches) != 1:
            return {"status": "MISSING_OR_AMBIGUOUS_SOURCE"}
        row = matches[0]
        checked = datetime.fromisoformat(str(row["Last checked UTC"]).replace("Z", "+00:00"))
        if checked.tzinfo is None:
            raise ValueError("Naive source check date")
        age = (as_of - checked.astimezone(PACIFIC).date()).days
        good = (row.get("Collector status") == "COMPLETE"
                and row.get("Freshness") in ("RECENT", "CURRENT")
                and row.get("Blocked records") == 0
                and 0 <= age <= 1)
        return {
            "status": "CURRENT_SOURCE_ONLY" if good else "PARTIAL_STALE_OR_BLOCKED",
            "last_check_age_days": age,
            "blocked_records": row.get("Blocked records"),
            "source_completeness_not_guaranteed": True,
        }
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError):
        return {"status": "UNVERIFIABLE_SOURCE"}


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
    inputs = {name: (json_inventory(p/name) if name.endswith(".json")
                     else csv_inventory(p/name)) for name in REQUIRED_FILES}
    histories = {name: csv_inventory(p/name) for name in HISTORY_FILES}
    discovery_status = discovery_status or {}
    scan_status = scan_status or {}
    info = gem_discrimination_audit(items, STAGES)
    verified_tracking = [
        row for row in items
        if str(row.get("Phase 3 tracking", "")).startswith("TRACKING")
    ]
    qualified = {stage: info[stage]["qualified"] for stage in STAGES}
    runway_source_status = "NOT PUBLISHED — NO CURRENT SEC COLLECTION"
    runway_collected = 0
    runway_target = 0
    try:
        saved = json.loads((p / "gem_runway_evidence.json").read_text(encoding="utf-8"))
        if (isinstance(saved, dict) and saved.get("schema_version") == 1
                and saved.get("source") == "SEC_STEP4_COMPANYFACTS"
                and isinstance(saved.get("snapshots"), list)
                and isinstance(saved.get("failures"), list)):
            runway_target = saved.get("target_count") if type(saved.get("target_count")) is int else 0
            runway_collected = len(saved["snapshots"])
            collected_date = date.fromisoformat(str(saved.get("as_of_pacific") or ""))
            if collected_date == today and not saved["failures"] and (
                    saved.get("collector_status") == "COMPLETE"):
                runway_source_status = "COLLECTED — CURRENT SEC STEP 4 SNAPSHOTS"
            elif collected_date > today:
                runway_source_status = "HOLD — FUTURE-DATED FINANCIAL COLLECTION"
            elif saved["failures"]:
                runway_source_status = "PARTIAL — SEC RECHECK FAILED FOR SOME TICKERS"
            else:
                runway_source_status = "STALE — SEC RUNWAY COLLECTION NOT CURRENT"
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        pass
    # Supplementary SEC specialist-manager Form 13F. Missing holdings are
    # NOT proof that a manager has no position or that a stock is ineligible.
    hedge_summary = {
        "collector_status": "NOT PUBLISHED",
        "managers_targeted": 0, "managers_complete": 0,
        "issuer_name_matched_tickers": 0,
        "matched_programs": sum(r.get("Hedge-fund signal")
                                == "SOURCE-VERIFIED QUARTERLY 13F HOLDINGS"
                                for r in items),
        "with_manager_accumulation": sum((r.get("Hedge-fund managers adding") or 0) > 0
                                         for r in items),
    }
    try:
        hdata = json.loads((p / "gem_hedge_fund_13f.json").read_text(encoding="utf-8"))
        if (isinstance(hdata, dict) and hdata.get("schema_version") == 1
                and hdata.get("source") == "SEC_13F_XML_INFO_TABLE"
                and isinstance(hdata.get("records"), list)):
            if date.fromisoformat(str(hdata.get("as_of_pacific") or "")) > today:
                hedge_summary["collector_status"] = "HOLD — FUTURE-DATED 13F"
            else:
                hedge_summary.update({
                    "collector_status": str(hdata.get("collector_status") or "UNVERIFIED"),
                    "managers_targeted": hdata.get("manager_count", 0),
                    "managers_complete": hdata.get("managers_complete", 0),
                    "issuer_name_matched_tickers": hdata.get("matched_ticker_count", 0),
                })
    except (OSError, ValueError, KeyError, AttributeError, TypeError, UnicodeError):
        pass
    insider_summary = {
        "collector_status": "NOT PUBLISHED", "issuers_targeted": 0,
        "issuers_complete": 0, "source_errors": 0,
        "matched_program_rows": sum(
            r.get("Insider Form 4 signal") == "SOURCE-VERIFIED SEC FORM 4 OBSERVATIONS"
            for r in items
        ),
        "with_open_market_purchases": sum(
            (r.get("Insider open-market purchases") or 0) > 0 for r in items
        ),
    }
    try:
        insider_src = json.loads((p / "gem_insider_form4.json").read_text(encoding="utf-8"))
        if (isinstance(insider_src, dict) and insider_src.get("schema_version") == 1
                and insider_src.get("source") == "SEC_ISSUER_FORM4_XML"
                and date.fromisoformat(str(insider_src.get("as_of_pacific") or "")) <= today):
            insider_summary.update({
                "collector_status": str(insider_src.get("collector_status") or "UNVERIFIED"),
                "issuers_targeted": insider_src.get("issuer_count", 0),
                "issuers_complete": insider_src.get("issuers_complete", 0),
                "source_errors": len(insider_src.get("issuer_errors") or []),
            })
    except (OSError, ValueError, KeyError, AttributeError, TypeError, UnicodeError):
        pass
    runway_counts = {
        "collector_status": runway_source_status,
        "target_count": runway_target,
        "collected_count": runway_collected,
        "minimum_entry_months": MIN_MONTHS,
        "source_backed_pass": sum(r.get("Cash runway gate") == PASS for r in items),
        "under_12_months": sum(r.get("Cash runway gate") == HOLD for r in items),
        "missing_or_stale": sum(r.get("Cash runway gate", REVIEW) == REVIEW for r in items),
        "deteriorating": sum(str(r.get("Cash runway trend") or "").startswith("DECLINING")
                             for r in items),
        "dilution_alerts": sum(str(r.get("GEM 3 dilution status") or "").startswith(("HOLD", "ALERT"))
                               for r in items),
    }
    source_stale = scan_status.get("feed_current") is not True
    history_complete = (histories[HISTORY_FILES[0]]["state"] == "PRESENT"
                        and histories[HISTORY_FILES[1]]["state"] == "PRESENT"
                        and histories[HISTORY_FILES[0]]["rows"] > 0
                        and histories[HISTORY_FILES[1]]["rows"] > 0)
    missing_required = [n for n, v in inputs.items()
                        if v["state"] != "PRESENT"]
    risks = []
    if runway_source_status != "COLLECTED — CURRENT SEC STEP 4 SNAPSHOTS":
        risks.append("GEM_SEC_CASH_RUNWAY_COLLECTION_MISSING_PARTIAL_OR_STALE")
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
    sec = source_family_health(p/"step7_live_status.json",
                               "SEC financing recheck", today)
    market = source_family_health(p/"step7_live_status.json",
                                  "Market EOD price / volume", today)
    if sec["status"] != "CURRENT_SOURCE_ONLY":
        risks.append("SEC_FINANCING_COVERAGE_BLOCKED_OR_STALE")
    if market["status"] != "CURRENT_SOURCE_ONLY":
        risks.append("MARKET_PRICE_VOLUME_SOURCE_BLOCKED_OR_STALE")
    acceptance = {
        "saved_scan_feed_current": not source_stale,
        "required_saved_sources_valid": not missing_required,
        "phase3_collector_current": clinical["status"] == "CURRENT_CLINICAL_ONLY",
        "phase3_discovery_ledger_reconciled": source_ledger_reconciled,
        "sec_financing_source_current": sec["status"] == "CURRENT_SOURCE_ONLY",
        "market_price_volume_source_current": market["status"] == "CURRENT_SOURCE_ONLY",
        # Do not promote readiness from file existence alone. A holdout
        # requires accepted historical trades and independent validation.
        "historical_return_edge_independently_validated": False,
        "complete_public_issuer_universe_verified": False,
        "live_streamlit_deployment_independently_verified": False,
    }
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
        "cash_runway": runway_counts,
        "hedge_fund_13f": hedge_summary,
        "insider_form4": insider_summary,
        "two_benchmark_candidate_count": sum(
            row.get("Two-benchmark eligible") is True for row in items
        ),
        "two_benchmark_policy": (
            "VERIFIED PHASE 3 RESULTS RELEASE + SECOND SEPARATE POST-READOUT "
            "FINANCING CLOSE; OTHER MEASURES ARE RANKING/RISK ONLY"
        ),
        "strict_entry_gate_shortlist_count": sum(
            row.get("GEM ALL ENTRY GATES") == "PASS — MANUAL REVIEW ONLY"
            for row in items
        ),
        "ranking_discrimination": info,
        "discovery_review_leads": len(discovery),
        "discovery_source_status": discovery_status,
        "clinical_collector": clinical,
        "sec_source_health": sec,
        "market_source_health": market,
        "acceptance_checks": acceptance,
        "all_acceptance_checks_passed": all(acceptance.values()),
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
            "Cash-only SEC runway is backward-looking and cannot guarantee future liquidity.",
            "PDUFA -3 is a research exit deadline, not an executed broker sale.",
            "A relative GEM rank is not a forecast of approval or equity return.",
            "No training or weight promotion from unverified or synthetic records.",
        ],
    }
