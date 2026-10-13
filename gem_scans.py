"""Source-conservative, independently ranked GEM scans for the SCANS sub-tab.

All three rankings use saved, exact-event-linked evidence from Stage 1.
A GEM score measures evidenced setup strength, NOT FDA approval probability,
expected stock appreciation, or authorization to enter a trade.
No result is inferred from an unsuccessful, partial, or stale source scan.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from post_phase3_unified import build_queue, read_rows
from trade_window import EXIT_BUFFER_DAYS as TRADE_EXIT_DAYS_BEFORE_PDUFA, MIN_NEW_ENTRY_DAYS

STAGES = ("Phase 3", "Post-Financing", "PDUFA")
# Stage-specific evidence-rubric weights, all totaling 100.
WEIGHTS = {
    "Phase 3": {
        "Clinical evidence /30": 60,
        "Trading setup /20": 25,
        "Market activity /10": 15,
    },
    "Post-Financing": {
        "Clinical evidence /30": 30,
        "Financing evidence /20": 35,
        "Trading setup /20": 25,
        "Market activity /10": 10,
    },
    "PDUFA": {
        "Clinical evidence /30": 25,
        "PDUFA evidence /15": 35,
        "Financing evidence /20": 15,
        "Trading setup /20": 10,
        "Market activity /10": 15,
    },
}
DENOMINATORS = {
    "Clinical evidence /30": 30,
    "Financing evidence /20": 20,
    "Trading setup /20": 20,
    "PDUFA evidence /15": 15,
    "Market activity /10": 10,
}
assert all(sum(weight.values()) == 100 for weight in WEIGHTS.values())

SCAN_QUALIFIERS = {
    "Phase 3": (
        "Current saved source feed; unique exact regulatory event",
        "Verified successful Phase 3 result and all clinical evidence gates",
        "Source-attested post-readout price base and normalized volume",
        "Fresh, valid market quote and no critical evidence conflict",
    ),
    "Post-Financing": (
        "All Phase 3 scan qualifiers",
        "Two separate post-Phase-3 financings with exact-event SEC evidence",
        "Second financing independently marked closed; dilution gate verified",
        "Verified PDUFA date with at least 4 calendar days remaining (planned exit: PDUFA -3)",
    ),
    "PDUFA": (
        "All Phase 3 scan qualifiers",
        "Source-verified future PDUFA date: at least 4 days remaining; no arbitrary 90-day maximum",
        "Second post-Phase-3 financing independently verified closed",
        "Financing and unresolved-dilution evidence gates verified",
        "Active unresolved FDA application (not decided, CRL or expired)",
    ),
}


def _number(value):
    try:
        n = float(value)
        return n if n == n and 0 <= n < float("inf") else 0.0
    except (TypeError, ValueError, OverflowError):
        return 0.0


def _score(record, stage):
    return round(sum(
        min(_number(record.get(field)), DENOMINATORS[field])
        / DENOMINATORS[field] * weight
        for field, weight in WEIGHTS[stage].items()
    ))


def _event_map(root):
    """Only unique exact keys can provide conflict and dilution assertions."""
    unique, duplicated = {}, set()
    for row in read_rows(Path(root) / "pdufa_candidates.csv"):
        key = (row.get("event_key") or "").strip()
        if not key:
            continue
        if key in unique:
            duplicated.add(key)
        unique[key] = row
    for key in duplicated:
        unique.pop(key, None)
    return unique


def _reasons(record, event, stage, feed_current):
    reasons = []
    days = record.get("Days to PDUFA")
    qualification = str(record.get("Entry qualification") or "")
    event_key = str(record.get("Exact event") or "").strip()
    if not feed_current or record.get("Evidence score /100") is None:
        reasons.append("Source snapshot stale or program evidence unrated")
    if not event_key or not event:
        reasons.append("Unique exact regulatory event not verified")
    if qualification.startswith("EXCLUDED") or (
        qualification.startswith("RED WINDOW") and
        days is not None and days <= TRADE_EXIT_DAYS_BEFORE_PDUFA
    ):
        reasons.append("FDA decision resolved or PDUFA -3 exit window reached")
    if event and str(event.get("conflict_flag") or "").upper() not in (
        "", "NO", "NONE", "FALSE", "0", "PASS"
    ):
        reasons.append("Unresolved clinical/regulatory conflict")
    if (record.get("Phase 3 evidence") != "VERIFIED SUCCESS — SOURCE LINKED"
            or _number(record.get("Clinical evidence /30")) != 30):
        reasons.append("Successful Phase 3 endpoint, benefit or safety not fully attested")
    if _number(record.get("Trading setup /20")) != 20:
        reasons.append("Verified post-readout price base / normalized volume missing")
    if _number(record.get("Market activity /10")) < 4:
        reasons.append("Fresh sourced market quote unavailable")
    if stage == "Post-Financing":
        if record.get("PDUFA verification") != "VERIFIED — SOURCE LINKED":
            reasons.append("PDUFA date and planned -3 exit not source verified")
        if str(record.get("2nd Financing Completed") or "") != "YES — VERIFIED (HISTORICAL)":
            reasons.append("Second separate post-Phase-3 financing closure not verified")
        if _number(record.get("Financing evidence /20")) != 20:
            reasons.append("Exact-event SEC closing / unresolved-dilution clearance incomplete")
        if days is None or days < MIN_NEW_ENTRY_DAYS:
            reasons.append("No verified future trading window through PDUFA -3")
    if stage == "PDUFA":
        if (record.get("PDUFA verification") != "VERIFIED — SOURCE LINKED"
                or _number(record.get("PDUFA evidence /15")) != 15):
            reasons.append("PDUFA date and FDA event not source-verified")
        if days is None or days < MIN_NEW_ENTRY_DAYS:
            reasons.append("Inside PDUFA -3 exit boundary or PDUFA date missing")
        if str(record.get("2nd Financing Completed") or "") != "YES — VERIFIED (HISTORICAL)":
            reasons.append("Verified post-Phase-3 second financing required")
        if _number(record.get("Financing evidence /20")) != 20:
            reasons.append("Verified financing / dilution clearance missing")
    if stage in ("Post-Financing", "PDUFA") and event:
        if str(event.get("new_dilution_flag") or "").strip().upper() not in (
            "NO", "FALSE", "0", "NONE", "CLEARED", "RESOLVED"
        ):
            reasons.append("Current dilution not explicitly cleared in event evidence")
    return reasons


def build_gem_scans(root="data", as_of=None):
    """Return all research records, stage-wise scored/ranked only when qualified.

    Each exact event receives up to three INDEPENDENT ranks. Incomplete or
    out-of-window records stay visible as REVIEW rows with no score or rank.
    """
    records, source_status = build_queue(root, as_of=as_of)
    events = _event_map(root)
    results = []
    for record in records:
        item = dict(record)
        # Stage 1 still enforces its older PDUFA -7 research entry cutoff.
        # The GEM scanner independently verifies the FDA source for days 4–7,
        # without bypassing actual clinical, financing or dilution gates.
        days = record.get("Days to PDUFA")
        if (days is not None and MIN_NEW_ENTRY_DAYS <= days <= 7 and
                record.get("PDUFA verification") == "VERIFIED — SOURCE LINKED" and
                str(record.get("Entry qualification") or "").startswith("RED WINDOW")):
            item["PDUFA evidence /15"] = 15
        event = events.get(str(record.get("Exact event") or "").strip())
        for stage in STAGES:
            reasons = _reasons(item, event, stage, source_status["feed_current"])
            item[stage + " qualifier"] = ("QUALIFIED — RESEARCH ONLY" if not reasons else "REVIEW — NOT QUALIFIED")
            item[stage + " missing"] = "; ".join(reasons)
            item[stage + " score"] = _score(item, stage) if not reasons else None
            item[stage + " rank"] = None
            item[stage + " GEM"] = "—"
        results.append(item)

    for stage in STAGES:
        # Ticker-level rankings: a company with multiple programs occupies
        # ONE rank position. Its highest eligible exact event represents it.
        best = {}
        for item in results:
            ticker = str(item.get("Ticker") or "").strip().upper()
            value = item[stage + " score"]
            if not ticker or value is None:
                continue
            current = best.get(ticker)
            if (current is None or
                    (-value, str(item.get("Exact event") or ""),
                     str(item.get("NCT ID") or "")) <
                    (-current[stage + " score"],
                     str(current.get("Exact event") or ""),
                     str(current.get("NCT ID") or ""))):
                best[ticker] = item
        ordered = sorted(
            best.values(), key=lambda r: (
                -r[stage + " score"], str(r.get("Ticker") or ""),
                str(r.get("Exact event") or ""),
            )
        )
        last_score, rank = None, None
        for position, item in enumerate(ordered, 1):
            if item[stage + " score"] != last_score:
                rank = position
                last_score = item[stage + " score"]
            item[stage + " rank"] = rank
            item[stage + " GEM"] = f"#{rank} ({item[stage + ' score']})"

    details = dict(source_status)
    tickers = {str(row.get("Ticker") or "").strip().upper()
               for row in results if str(row.get("Ticker") or "").strip()}
    details["scan_counts"] = {
        stage: {
            "qualified": len({str(item.get("Ticker") or "").strip().upper()
                              for item in results if item[stage + " rank"] is not None}),
            "review": len(tickers) - len({str(item.get("Ticker") or "").strip().upper()
                                         for item in results if item[stage + " rank"] is not None}),
            "qualifying_programs": sum(item[stage + " score"] is not None for item in results),
        }
        for stage in STAGES
    }
    details["trade_exit_days_before_pdufa"] = TRADE_EXIT_DAYS_BEFORE_PDUFA
    details["last_eligible_entry_days_before_pdufa"] = MIN_NEW_ENTRY_DAYS
    details["rubric"] = "STAGE-EVIDENCE-GEMS-V2-D3 — NOT APPROVAL OR RETURN FORECAST"
    return results, details

def ticker_gems(items):
    """One display row per ticker with independently ranked GEM programs.

    Individual exact-event evidence rows remain in the stage details/exports.
    Do not merge Phase 3 evidence from one NCT into financing on another.
    """
    groups = {}
    for item in items:
        ticker = str(item.get("Ticker") or "").strip().upper()
        if not ticker:
            continue
        if ticker not in groups:
            groups[ticker] = {"Ticker": ticker, "Drug": "",
                              **{stage + " GEM": "—" for stage in STAGES}}
        summary = groups[ticker]
        for stage in STAGES:
            if item.get(stage + " rank") is not None:
                summary[stage + " GEM"] = item[stage + " GEM"]
                summary[stage + " program"] = str(item.get("Drug") or "")
                summary[stage + " event"] = str(item.get("Exact event") or "")
                if stage == "Post-Financing":
                    summary["Drug"] = str(item.get("Drug") or "")
        if not summary.get("Drug"):
            summary["Drug"] = str(item.get("Drug") or "")
    return sorted(groups.values(), key=lambda r: (
        min((int(r[stage + " GEM"].split(" ")[0][1:]) for stage in STAGES
             if r[stage + " GEM"] != "—"), default=10**9), r["Ticker"]))
