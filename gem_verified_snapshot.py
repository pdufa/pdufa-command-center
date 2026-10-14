"""Exact-event GEM two-benchmark primary-source clearance, not trade permission.

Clinical Phase 3 and the second independently funded post-readout transaction
can be verified even while a separate *global* SEC batch health check is stale.
Do not confuse benchmark clearance with market/regulatory/dilution trade gates.
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from gem_financing_gate import second_post_phase3_close, sec_recheck_current
from gem_two_benchmark import phase3_results_released

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
        phase3 = phase3_results_released(program, event, as_of=today)
        financed, close_date, note = second_post_phase3_close(
            key, event.get("phase3_date"), funding, as_of=today
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
        flags = []
        if not global_sec_healthy:
            flags.append("Global SEC collector PARTIAL/STALE; trading entry on HOLD")
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
            "Phase 3 date": str(event.get("phase3_date") or ""),
            "Phase 3 status": str(event.get("phase3_status") or ""),
            "Phase 3 source": str(event.get("trial_evidence_url") or ""),
            "First close": str(funding.get("first_financing_date") or ""),
            "First SEC source": str(funding.get("first_financing_source") or ""),
            "Second close": close_date or "",
            "Second SEC source": str(funding.get("second_financing_source") or ""),
            "PDUFA saved": str(event.get("pdufa_date") or ""),
            "FDA outcome": outcome,
            "Two-benchmark status": "PASS — BOTH BENCHMARKS SOURCE-CLEARED",
            "Trade status": "HISTORICAL / NO NEW ENTRY" if is_historical
                            else "RESEARCH-QUALIFIED / ENTRY GATES ON HOLD",
            "Still needed": "; ".join(flags),
            "Source review as of": str(funding.get("verified_as_of") or ""),
        }
        (historical if is_historical else active).append(record)
    order = lambda row: (row["Ticker"], row["Exact program"])
    return sorted(active, key=order), sorted(historical, key=order), global_sec_healthy
