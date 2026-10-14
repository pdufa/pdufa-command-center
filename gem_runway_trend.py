"""Point-in-time SEC cash-runway deterioration and dilution warnings for GEM 3.

A warning is a research observation, not a trade, order, or live SEC alert.
Historical cash-only runway estimates must come from separately dated SEC
Step 4 observations; unchanged snapshots cannot masquerade as trends.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from gem_runway_gate import PASS, HOLD, REVIEW, _day, assess_runway

DILUTION_RISK = {"YES", "TRUE", "1", "ACTIVE", "UNRESOLVED", "UNKNOWN"}
MIN_DECLINE_MONTHS = 3.0
MIN_DECLINE_FRACTION = 0.25
MAX_PRIOR_AGE_DAYS = 365


def load_history(root):
    """Load saved source snapshots only; never claim a live SEC recheck."""
    root = Path(root)
    by_ticker = {}
    evidence_file = root / "gem_runway_evidence.json"
    if evidence_file.is_file():
        try:
            obj = json.loads(evidence_file.read_text(encoding="utf-8"))
            if (isinstance(obj, dict) and obj.get("schema_version") == 1
                    and obj.get("source") == "SEC_STEP4_COMPANYFACTS"
                    and isinstance(obj.get("history", []), list)):
                for snap in obj.get("history", []):
                    if isinstance(snap, dict):
                        ticker = str(snap.get("ticker") or "").strip().upper()
                        if ticker:
                            by_ticker.setdefault(ticker, []).append(snap)
        except (OSError, ValueError, TypeError, UnicodeError):
            pass

    db = root / "sec_step4_snapshots.sqlite3"
    if db.is_file():
        try:
            from sec_step4 import read_history
            for row in read_history(db_path=db):
                snap = json.loads(row["payload_json"])
                if isinstance(snap, dict):
                    ticker = str(snap.get("ticker") or "").strip().upper()
                    if ticker:
                        by_ticker.setdefault(ticker, []).append(snap)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            # Missing history never produces an invented trend.
            pass
    return by_ticker


def assess_trend(ticker, current_snapshot, history, *, as_of, dilution_flag=""):
    """Compare the latest current cash quarter with a *different* earlier quarter.

    Review-only historical estimates are validated against their own original
    as-of dates. We never compare a revised same-quarter copy as a new trend.
    """
    result = {
        "Cash runway trend": "REVIEW — NO COMPARABLE HISTORICAL SEC QUARTER",
        "Cash runway previous (months)": None,
        "Cash runway previous period": "",
        "GEM 3 dilution status": "NO NEW DILUTION FLAG IN SAVED SOURCE",
        "GEM 3 financial alert": "REVIEW — NO VALID CURRENT CASH RUNWAY",
    }
    dilution = str(dilution_flag or "").strip().upper()
    if dilution in DILUTION_RISK:
        result["GEM 3 dilution status"] = (
            "HOLD — DILUTION STATUS UNKNOWN" if dilution == "UNKNOWN"
            else "ALERT — NEW OR UNRESOLVED DILUTION"
        )
    elif not dilution:
        result["GEM 3 dilution status"] = "REVIEW — DILUTION SOURCE HAS NO STATUS"

    current = assess_runway(ticker, current_snapshot, as_of=as_of)
    current_gate = current["Cash runway gate"]
    warning = ("HOLD — RUNWAY UNVERIFIED" if current_gate == REVIEW else
               "ALERT — UNDER 12 MONTHS RUNWAY" if current_gate == HOLD else
               "NO RUNWAY DETERIORATION VERIFIED")
    today = _day(as_of)
    evidence = current_snapshot.get("evidence") if isinstance(current_snapshot, dict) else None
    cash = evidence.get("cash") if isinstance(evidence, dict) else None
    current_end = _day(cash.get("period_end")) if isinstance(cash, dict) else None
    current_cik = str(current_snapshot.get("cik") or "") if isinstance(current_snapshot, dict) else ""
    current_months = current["Cash runway (months)"]

    candidates = []
    if current_months is not None and today and current_end and current_cik:
        for snap in history or ():
            if (not isinstance(snap, dict)
                    or str(snap.get("ticker") or "").strip().upper() != str(ticker or "").upper()
                    or str(snap.get("cik") or "") != current_cik):
                continue
            previous_evidence = snap.get("evidence")
            previous_cash = (previous_evidence.get("cash")
                             if isinstance(previous_evidence, dict) else None)
            previous_end = (_day(previous_cash.get("period_end"))
                            if isinstance(previous_cash, dict) else None)
            observed = _day(snap.get("as_of"))
            if (not previous_end or previous_end >= current_end or not observed
                    or observed > today or not 0 <= (today - previous_end).days <= MAX_PRIOR_AGE_DAYS):
                continue
            checked = assess_runway(ticker, snap, as_of=observed)
            if checked["Cash runway gate"] in (PASS, HOLD):
                candidates.append((previous_end, observed, checked["Cash runway (months)"]))

    if candidates:
        old_end, _, old_months = max(candidates)
        result["Cash runway previous (months)"] = old_months
        result["Cash runway previous period"] = old_end.isoformat()
        drop = old_months - current_months
        declining = drop >= MIN_DECLINE_MONTHS or (old_months > 0 and drop / old_months >= MIN_DECLINE_FRACTION)
        if declining:
            result["Cash runway trend"] = (
                f"DECLINING — {old_months:g} to {current_months:g} months")
            if current_gate == PASS:
                warning = "WATCH — RUNWAY DETERIORATING DESPITE 12+ MONTHS"
        elif drop < -0.01:
            result["Cash runway trend"] = (
                f"IMPROVING — {old_months:g} to {current_months:g} months")
        else:
            result["Cash runway trend"] = "STABLE — NO MATERIAL DECLINE"

    flags = [warning]
    if result["GEM 3 dilution status"].startswith(("HOLD", "ALERT", "REVIEW")):
        flags.append(result["GEM 3 dilution status"])
    result["GEM 3 financial alert"] = "; ".join(flags)
    return result
