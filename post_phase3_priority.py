"""Evidence-only priority ordering for the POST PHASE 3 candidate table.

This is NOT probability of FDA approval, price appreciation, or actual
clinical quality. Missing source evidence is never converted to an assumed
PASS. GREEN entry eligibility is calculated independently by Stage 1.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from step7_entry import GATES, safe_source

PACIFIC = ZoneInfo("America/Los_Angeles")
WEIGHTS = {
    "Clinical evidence /30": 30,
    "Financing evidence /20": 20,
    "Trading setup /20": 20,
    "PDUFA evidence /15": 15,
    "Market activity /10": 10,
    "Company track record /5": 5,
}
CATEGORIES = tuple(WEIGHTS)
TOTAL = sum(WEIGHTS.values())
assert TOTAL == 100


def _value(raw):
    return str(raw or "").strip()


def _day(raw):
    try:
        value = _value(raw)[:10]
        return date.fromisoformat(value)
    except ValueError:
        return None


def _num(raw):
    try:
        n = float(_value(raw))
        return n if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _passed_gates(financing):
    """Only explicit, uniquely named gate PASS statuses count."""
    details = _value(financing.get("Audited gate details"))
    passed = set()
    for piece in details.split(" | "):
        key, sep, verdict = piece.partition(":")
        if sep and key.strip() in GATES and verdict.strip().startswith("PASS"):
            passed.add(key.strip())
    return passed


def _market_valid(market, today):
    if not market or not safe_source(market.get("market_source")):
        return False
    session = _day(market.get("last_session"))
    try:
        checked = datetime.fromisoformat(
            _value(market.get("checked_at_utc")).replace("Z", "+00:00")
        )
    except ValueError:
        return False
    if not session or checked.tzinfo is None:
        return False
    checked_day = checked.astimezone(PACIFIC).date()
    return bool(
        market.get("market_status") == "MARKET_UPDATED"
        and market.get("last_session_freshness") == "RECENT EOD"
        and _num(market.get("last_close_usd")) is not None
        and _num(market.get("last_close_usd")) > 0
        and 0 <= (today - session).days <= 5
        and 0 <= (today - checked_day).days <= 3
    )


def _financing_valid(financing):
    scan = _value(financing.get("Source scan")).upper()
    return bool(
        _value(financing.get("Historical second closing")).startswith("DOCUMENTED")
        and _value(financing.get("Recheck freshness")) == "RECENT"
        and scan not in {"", "NOT_CHECKED", "SOURCE_UNAVAILABLE", "NO_SOURCE"}
        and not any(token in scan for token in ("BLOCKED", "ERROR", "PARTIAL"))
        and safe_source(financing.get("Second source"), sec=True)
    )


def score_candidate(event, financing, market, today, *,
                    snapshot_current=True):
    """Rate evidentiary support (not intrinsic investment quality).

    All scoring uses exact event financing joins supplied by build_queue.
    Ticker-only market bars are used solely for market observations.
    An otherwise scored stale snapshot is marked UNRATED, not silently fresh.
    """
    points = dict.fromkeys(CATEGORIES, 0)
    notes = []
    if not snapshot_current:
        return {
            "Evidence score /100": None,
            **points,
            "Rating coverage": "0/6 — stale feed",
            "Rating status": "NOT RATED — SNAPSHOT STALE",
            "Rating limitations": "Refresh daily clinical, SEC, and market evidence",
        }

    if not event:
        return {
            "Evidence score /100": None,
            **points,
            "Rating coverage": "0/6 — research lead",
            "Rating status": "NOT RATED — UNMATCHED RESEARCH LEAD",
            "Rating limitations": "Exact program and qualifying evidence must be reviewed",
        }

    passed = _passed_gates(financing)
    clinical = (_value(event.get("phase3_status")).upper()
                in {"VERIFIED_SUCCESS", "PRIMARY_MET_VERIFIED"}
                and _day(event.get("phase3_date")) is not None
                and safe_source(event.get("trial_evidence_url"))
                and bool(_value(event.get("nct_id"))))
    if clinical:
        for key, weight in (
            ("trial_identity", 4), ("phase3_primary", 12),
            ("clinical_benefit", 10), ("safety", 4),
        ):
            if key in passed:
                points["Clinical evidence /30"] += weight
    if points["Clinical evidence /30"] < 30:
        notes.append("Phase 3 endpoint/benefit/safety evidence incomplete")

    financing_source = _financing_valid(financing)
    if financing_source:
        if "second_financing" in passed:
            points["Financing evidence /20"] += 16
        if "no_unresolved_dilution" in passed:
            points["Financing evidence /20"] += 4
    if points["Financing evidence /20"] < 20:
        notes.append("SEC financing and/or dilution clearance incomplete")

    quote_valid = _market_valid(market, today)
    if quote_valid and financing:
        if "post_readout_price_base" in passed:
            points["Trading setup /20"] += 12
        if "normalized_volume" in passed:
            points["Trading setup /20"] += 8
    if points["Trading setup /20"] < 20:
        notes.append("Price base and/or volume normalization not attested")

    pdufa_day = _day(event.get("pdufa_date"))
    conflict = _value(event.get("conflict_flag")).upper()
    pdufa_valid = bool(
        _value(event.get("pdufa_confirmation")).upper().startswith("VERIFIED")
        and safe_source(event.get("pdufa_evidence_url"))
        and pdufa_day is not None
        and (pdufa_day - today).days > 7
        and conflict in {"", "NO", "NONE", "FALSE", "0", "PASS"}
    )
    if pdufa_valid:
        points["PDUFA evidence /15"] = 15
    else:
        notes.append("Future PDUFA date not source-verified or outside entry window")

    if quote_valid:
        points["Market activity /10"] += 4
        momentum = _num(market.get("trailing_momentum_pct"))
        relative_volume = _num(market.get("relative_volume"))
        if momentum is not None and momentum > 0:
            points["Market activity /10"] += 3
        if relative_volume is not None and relative_volume >= 1:
            points["Market activity /10"] += 3
        if points["Market activity /10"] < 10:
            notes.append("Market activity lacks positive momentum or relative volume")
    else:
        notes.append("Recent market quote unavailable")
    # Intentionally no company record points: saved product revenue and
    # pipeline records do not yet have this module's attested source links.
    notes.append("Company history/pipeline score awaiting source audit")
    if quote_valid:
        notes.append("Short interest/float not independently scored")
    score = sum(points.values())
    coverage = sum(1 for v in points.values() if v > 0)
    substantive = (
        points["Clinical evidence /30"] > 0 or
        points["Financing evidence /20"] > 0 or
        points["PDUFA evidence /15"] > 0
    )
    return {
        "Evidence score /100": score if substantive else None,
        **points,
        "Rating coverage": f"{coverage}/6 categories evidenced",
        "Rating status": (
            "PARTIAL — SOURCE-SUPPORTED RESEARCH POINTS"
            if substantive else "NOT RATED — INSUFFICIENT VERIFIED PROGRAM EVIDENCE"
        ),
        "Rating limitations": "; ".join(notes),
    }


def assign_priority_ranks(rows):
    """Rank only rated, active rows. Unrated/RED/EXCLUDED have no ordinal rank.

    The main table groups eligibility separately, preserving the hard gate
    regardless of these optional evidence-priority rankings.
    """
    candidates = [
        row for row in rows
        if row.get("Evidence score /100") is not None
        and not _value(row.get("Entry qualification")).startswith(
            ("RED WINDOW", "EXCLUDED")
        )
    ]
    ordered = sorted(
        candidates, key=lambda r: (
            -r["Evidence score /100"], _value(r.get("Ticker")),
            _value(r.get("NCT ID")), _value(r.get("Exact event"))
        )
    )
    for index, row in enumerate(ordered, 1):
        row["Evidence rank"] = index
    for row in rows:
        row.setdefault("Evidence rank", None)
    return rows
