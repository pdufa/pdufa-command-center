"""Research triage priority for Stage 1 POST PHASE 3 candidates.

Unlike a source-attested trade score, this ranks WHAT TO INVESTIGATE NEXT
using explicitly observed metadata and dated quote availability. It NEVER
certifies clinical success, second financing, approval, profitability or
entry readiness. A reported, unverified PDUFA date can raise review urgency
but earns NO verified-PDUFA gate.
"""
from __future__ import annotations

from datetime import date
from post_phase3_priority import _market_valid, _financing_valid, _num, _value
from step7_entry import NCT, EVENT, safe_source

REVIEW_COMPONENTS = (
    "Review timing /30", "Review clinical follow-up /20",
    "Review financing follow-up /15", "Review regulatory follow-up /15",
    "Review market follow-up /15", "Review identity /5",
)
REVIEW_TOTAL = (30,20,15,15,15,5)
assert sum(REVIEW_TOTAL) == 100


def review_priority(row, event, financing, market, today, *, snapshot_current=True):
    """Compute a reproducible research worklist score, not a trading score.

    The score remains valid for review even if a gate is blocked; any timing
    or quote points are clearly flagged as unverified/current observations.
    No ticker-only lookup is used to validate clinical/financing evidence.
    """
    p = dict.fromkeys(REVIEW_COMPONENTS, 0)
    caveats = []
    ticker = _value(row.get("Ticker")).upper()
    nct = _value(row.get("NCT ID")).upper()
    key = _value(row.get("Exact event"))
    status = _value(row.get("Entry qualification"))
    d = row.get("Days to PDUFA")
    try:
        days = int(d) if d is not None and str(d).strip() else None
    except (ValueError, TypeError):
        days = None
    if days is not None and days >= 8:
        p["Review timing /30"] = (
            30 if days <= 90 else 22 if days <= 180 else
            10 if days <= 365 else 5
        )
    elif days is not None and 0 <= days < 8:
        caveats.append("Inside final no-new-entry window")
    if days is None:
        caveats.append("No dated PDUFA target available")
    elif _value(row.get("PDUFA verification")).startswith("REVIEW"):
        caveats.append("PDUFA target is reported, NOT independently verified")

    clinical_state = _value(row.get("Phase 3 evidence"))
    clinical_src = safe_source(row.get("Phase 3 source"))
    if clinical_state.startswith("VERIFIED SUCCESS") and clinical_src:
        p["Review clinical follow-up /20"] = 20
    elif "ISSUER ANNOUNCEMENT" in clinical_state and clinical_src:
        p["Review clinical follow-up /20"] = 14
    elif "REGISTRY RESULTS POSTED" in clinical_state:
        p["Review clinical follow-up /20"] = 12
    elif "POTENTIAL ISSUER READOUT" in clinical_state and clinical_src:
        p["Review clinical follow-up /20"] = 10
    elif event:
        state = _value(event.get("phase3_status")).upper()
        if state in {"RESULTS_REVIEW", "RESULTS_VERIFIED", "VERIFIED_SUCCESS", "PRIMARY_MET_VERIFIED"}:
            p["Review clinical follow-up /20"] = 10 if clinical_src else 6
        elif event.get("phase3_date"):
            p["Review clinical follow-up /20"] = 5
    if p["Review clinical follow-up /20"] < 20:
        caveats.append("Phase 3 outcome not fully source-adjudicated")

    # Funding review record existence is a clue ONLY, not proof of a close.
    if financing:
        p["Review financing follow-up /15"] += 5
        if _financing_valid(financing):
            p["Review financing follow-up /15"] += 10
    if p["Review financing follow-up /15"] < 15:
        caveats.append("Post-readout second financing not source-cleared")

    if days is not None and days >= 0:
        p["Review regulatory follow-up /15"] += 7
        if _value(row.get("PDUFA verification")).startswith("VERIFIED") and safe_source(row.get("PDUFA source")):
            p["Review regulatory follow-up /15"] += 8

    # A ticker price snapshot can prioritize *research*, never verify the
    # event-specific technical entry gate.
    quote_valid = bool(snapshot_current and _market_valid(market, today))
    if quote_valid:
        p["Review market follow-up /15"] += 7
        if (_num(market.get("trailing_momentum_pct")) or 0) > 0:
            p["Review market follow-up /15"] += 4
        if (_num(market.get("relative_volume")) or 0) >= 1:
            p["Review market follow-up /15"] += 4
    else:
        caveats.append("Current sourced market observation unavailable")

    if NCT.fullmatch(nct):
        p["Review identity /5"] += 3
    if EVENT.fullmatch(key) and key.split("|",1)[0] == ticker:
        p["Review identity /5"] += 2
    if not snapshot_current:
        caveats.append("Daily snapshot is stale; refresh before any entry qualification")

    if status.startswith(("RED WINDOW", "EXCLUDED")):
        caveats.append("Not a current new-entry candidate")
    score = sum(p.values())
    return {
        "Research priority /100": score,
        "Research priority status": "RESEARCH TRIAGE ONLY — NOT TRADE READY",
        "Research priority limitations": "; ".join(caveats),
        **p,
    }


def assign_review_ranks(rows):
    """Rank every GREEN or REVIEW candidate even when strict score is blank.

    Gate tier remains the first sorting dimension to keep qualified GREEN
    ahead of blocked REVIEW; secondary ranking uses observed research priority.
    Excluded and no-new-entry RED rows are not trade-candidate ranked.
    """
    def gate_order(row):
        value = _value(row.get("Entry qualification"))
        if value.startswith("GREEN"):
            return 0
        if value.startswith("REVIEW — ENTRY BLOCKED"):
            return 1
        if value.startswith("REVIEW — SOURCE SNAPSHOT STALE"):
            return 2
        return 3
    for row in rows:
        row["Research rank"] = None
    active = [row for row in rows
              if _value(row.get("Entry qualification")).startswith(("GREEN", "REVIEW"))]
    active.sort(key=lambda row: (
        gate_order(row), -int(row.get("Research priority /100") or 0),
        _value(row.get("Ticker")), _value(row.get("NCT ID")),
        _value(row.get("Exact event")),
    ))
    for index, row in enumerate(active, 1):
        row["Research rank"] = index
    return rows
