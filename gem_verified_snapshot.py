"""Exact-event GEM two-benchmark primary-source clearance, not trade permission.

Clinical Phase 3 and the second independently funded post-readout transaction
can be verified even while a separate *global* SEC batch health check is stale.
Do not confuse benchmark clearance with market/regulatory/dilution trade gates.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from gem_financing_gate import second_post_phase3_close, sec_recheck_current
from gem_two_benchmark import phase3_results_released
from pipeline_source_scope import pipeline_origins, gem_pipeline_id

CLOSED_OUTCOMES = {"APPROVED", "CRL", "REJECTED", "WITHDRAWN", "REFUSED"}


def _records(path):
    try:
        with Path(path).open(newline="", encoding="utf-8-sig") as fd:
            return list(csv.DictReader(fd))
    except (OSError, csv.Error, UnicodeError):
        return []


def _unique(rows):
    """Never certify a missing or multiply mapped exact-program key."""
    seen, duplicate = {}, set()
    for row in rows:
        key = str(row.get("event_key") or "").strip()
        if not key:
            continue
        if key in seen:
            duplicate.add(key)
        else:
            seen[key] = row
    for key in duplicate:
        seen.pop(key, None)
    return seen


def _date(value):
    try:
        return date.fromisoformat(str(value or "").strip()[:10])
    except (TypeError, ValueError):
        return None


def source_cleared_gems(root="data", *, as_of=None):
    """Return (current_two_benchmark, historical_two_benchmark, source_health).

    Results are tied to a unique clinical exact event, an actual Phase 3
    endpoint/readout, and two chronologically distinct SEC-linked close dates.
    This does not modify the SEC collector's global health or place trades.
    """
    root = Path(root)
    today = as_of or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    if not isinstance(today, date):
        raise ValueError("as_of must be a date")
    events = _unique(_records(root / "pdufa_candidates.csv"))
    finance = _unique(_records(root / "second_financing_status.csv"))
    pipeline_ids, pipeline_tickers = pipeline_origins(root, today=today)
    global_sec_healthy = sec_recheck_current(root, as_of=today)
    active, historical = [], []
    for key, event in events.items():
        funding = finance.get(key)
        if not funding:
            continue
        ticker = str(event.get("ticker") or "").strip().upper()
        nct = str(event.get("nct_id") or "").strip().upper()
        if not ticker or not nct:
            continue
        program = {"Ticker": ticker, "NCT ID": nct, "Exact event": key}
        pipeline_id = gem_pipeline_id(program, pipeline_ids, pipeline_tickers)
        if not pipeline_id:
            continue
        phase3 = phase3_results_released(program, event, as_of=today)
        financed, close_date, note = second_post_phase3_close(
            key, event.get("phase3_date"), funding, as_of=today,
            require_fresh=False,
        )
        if not (phase3 and financed):
            continue
        pd_date = _date(event.get("pdufa_date"))
        outcome = str(event.get("outcome") or "").strip().upper()
        is_historical = (
            outcome in CLOSED_OUTCOMES
            or str(event.get("check_status") or "").upper().startswith("RESOLVED_")
            or str(event.get("monitor_eligibility") or "").upper() == "EXCLUDED"
            or (pd_date is not None and (pd_date - today).days <= 3)
        )
        days_to_pdufa = (pd_date - today).days if pd_date else None
        target_verified = bool(
            str(event.get("pdufa_confirmation") or "").startswith("VERIFIED")
            and str(event.get("pdufa_evidence_url") or "").startswith("https://")
        )
        if days_to_pdufa is None:
            timing_window = "PDUFA UNKNOWN — RESEARCH"
        elif days_to_pdufa <= 3:
            timing_window = "EXIT / RESOLVED — NO NEW ENTRY"
        elif days_to_pdufa <= 13:
            timing_window = "4–13 DAYS — EXIT PREPARATION"
        elif days_to_pdufa <= 30:
            timing_window = "14–30 DAYS — LATE WINDOW"
        elif days_to_pdufa <= 90:
            timing_window = "31–90 DAYS — PRIMARY MONITOR"
        else:
            timing_window = ">90 DAYS — EARLY MONITOR"
        flags = []
        if not global_sec_healthy:
            flags.append("Global SEC collector PARTIAL/STALE; trading entry on HOLD")
        audit_date = _date(funding.get("verified_as_of"))
        if audit_date is None or (today - audit_date).days > 7:
            flags.append("Program-specific SEC evidence needs a fresh recheck before trading")
        if not str(event.get("pdufa_confirmation") or "").startswith("VERIFIED"):
            flags.append("PDUFA target date not independently verified")
        if is_historical:
            flags.append("FDA outcome resolved or scheduled exit boundary passed")
        else:
            flags.append("Other trading gates NOT cleared; no order authorization")
        record = {
            "Ticker": ticker,
            "Drug": str(event.get("drug") or "").strip(),
            "Indication": str(event.get("indication") or "").strip(),
            "NCT ID": nct,
            "Exact program": key,
            "Pipeline ID": pipeline_id,
            "Phase 3 date": str(event.get("phase3_date") or ""),
            "Phase 3 status": str(event.get("phase3_status") or ""),
            "Phase 3 source": str(event.get("trial_evidence_url") or ""),
            "First close": str(funding.get("first_financing_date") or ""),
            "First SEC source": str(funding.get("first_financing_source") or ""),
            "Second close": close_date or "",
            "Second SEC source": str(funding.get("second_financing_source") or ""),
            "PDUFA saved": str(event.get("pdufa_date") or ""),
            "PDUFA days left": days_to_pdufa,
            "PDUFA timing window": timing_window,
            "PDUFA verified": target_verified,
            "Planned exit (PDUFA −3)": (
                (pd_date - timedelta(days=3)).isoformat() if pd_date else ""
            ),
            "FDA outcome": outcome,
            "Two-benchmark status": "PASS — BOTH BENCHMARKS SOURCE-CLEARED",
            "Trade status": "HISTORICAL / NO NEW ENTRY" if is_historical
                            else "RESEARCH-QUALIFIED / ENTRY GATES ON HOLD",
            "Still needed": "; ".join(flags),
            "Source review as of": str(funding.get("verified_as_of") or ""),
        }
        (historical if is_historical else active).append(record)
    def order(row):
        days = row["PDUFA days left"]
        return (
            0 if isinstance(days, int) and 30 <= days <= 90 else 1,
            0 if row["PDUFA verified"] else 1,
            abs(days - 60) if isinstance(days, int) else 1_000_000,
            row["Ticker"], row["Exact program"],
        )
    return sorted(active, key=order), sorted(
        historical, key=lambda row: (row["Ticker"], row["Exact program"])
    ), global_sec_healthy
