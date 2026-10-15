"""Single GEM master list across Phase 3, financing and PDUFA research.

Every saved program remains visible. Exactly two source-verified event gates
control the eligibility/rank; stage and timing labels are descriptive only.
Legacy three-stage rubrics remain in the audit backend, not extra lists.
"""
from __future__ import annotations

PDUFA_DISPLAY_WINDOW_DAYS = 90
PHASE3_OK = "PASS — VERIFIED RESULTS RELEASE"
FINANCING_OK = "PASS — TWO POST-READOUT CLOSES"

MASTER_COLUMNS = [
    "GEM Rank", "GEM Score /100", "GEM Stage", "GEM Status",
    "Ticker", "Drug", "Indication", "NCT ID", "Pipeline ID",
    "Date Found", "Date Left", "Date Re-entered", "Listing status",
    "Phase 3 Verified", "Second Financing Closed",
    "Phase 3 Result Date", "Second Financing Close Date",
    "PDUFA Date", "Days to PDUFA", "PDUFA Date Verified", "Planned Exit (-3 days)",
    "Phase 3 Quality /30", "Financial Runway /20",
    "Trading Activity /20", "Dilution /15",
    "Hedge-Fund Accumulation /10", "PDUFA Timing /5",
    "Cash Runway (months)", "Cash Runway Trend",
    "Financing Watch", "Dilution Warning",
    "Hedge-Fund Signal", "Hedge-Fund Managers Adding",
    "Insider Form 4 Signal", "Insider Purchases", "Insider Sales",
    "Risks / Evidence Gaps",
    "Phase 3 Source", "Financing Source", "PDUFA Source",
    "Hedge-Fund Source Links", "Insider Source Links",
    "Exact Program / Event",
]


def _days(value):
    """Only exact integer days are sufficient for a PDUFA-stage label."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def gem_stage(item):
    """A descriptive lifecycle stage; never itself grants GEM eligibility."""
    days = _days(item.get("Days to PDUFA"))
    if (item.get("PDUFA verification") == "VERIFIED — SOURCE LINKED"
            and days is not None and days <= PDUFA_DISPLAY_WINDOW_DAYS):
        return "PDUFA"
    if item.get("Benchmark 2 — Financing #2 closed") == FINANCING_OK:
        return "Post-Financing"
    if item.get("Benchmark 1 — Phase 3 released") == PHASE3_OK:
        return "Phase 3"
    return "Research / Unverified"


def gem_status(item):
    """Respect the independent two-benchmark rule; never promote stage alone."""
    if item.get("Two-benchmark eligible") is True:
        days = _days(item.get("Days to PDUFA"))
        risks = str(item.get("Two-benchmark risk flags") or "").lower()
        if ("fda event already resolved" in risks
                or (days is not None and days <= 3)):
            return "EXIT / FDA DECISION WARNING"
        return "ELIGIBLE — RANKED; MANUAL REVIEW"
    if item.get("Benchmark 1 — Phase 3 released") == PHASE3_OK:
        return "WATCH — FINANCING #2 UNVERIFIED"
    return "REVIEW — PHASE 3 UNVERIFIED"


def _sort_key(item):
    """Rank eligible programs first; track all unverified programs afterward."""
    eligible = item.get("Two-benchmark eligible") is True
    phase3 = item.get("Benchmark 1 — Phase 3 released") == PHASE3_OK
    rank = item.get("Two-benchmark rank")
    days = _days(item.get("Days to PDUFA"))
    return (
        0 if eligible else (1 if phase3 else 2),
        rank if eligible and isinstance(rank, int) else 1_000_000,
        abs(days) if days is not None else 1_000_000,
        str(item.get("Ticker") or ""), str(item.get("Exact event") or ""),
    )


def build_gem_master_list(items):
    """One row per existing exact program; no synthetic or cross-program joins."""
    result = []
    for item in sorted(items, key=_sort_key):
        qualified = item.get("Two-benchmark eligible") is True
        # Never show a rank or 100-point score on a watch/unverified record.
        rank = item.get("Two-benchmark rank") if qualified else None
        score = item.get("Two-benchmark priority /100") if qualified else None
        result.append({
            "GEM Rank": rank,
            "GEM Score /100": score,
            "GEM Stage": gem_stage(item),
            "GEM Status": gem_status(item),
            "Ticker": item.get("Ticker"),
            "Drug": item.get("Drug"),
            "Indication": item.get("Indication"),
            "NCT ID": item.get("NCT ID"),
            "Pipeline ID": item.get("Pipeline ID", ""),
            "Phase 3 Verified": item.get("Benchmark 1 — Phase 3 released"),
            "Second Financing Closed": item.get("Benchmark 2 — Financing #2 closed"),
            "Phase 3 Result Date": item.get("Phase 3 result date (source)"),
            "Second Financing Close Date": item.get("Verified 2nd financing close date"),
            "PDUFA Date": item.get("PDUFA date"),
            "Days to PDUFA": item.get("Days to PDUFA"),
            "PDUFA Date Verified": item.get("PDUFA verification") == "VERIFIED — SOURCE LINKED",
            "Planned Exit (-3 days)": item.get("Planned exit (-3 days)"),
            "Phase 3 Quality /30": item.get("Phase 3 quality /30") if qualified else None,
            "Financial Runway /20": item.get("Financial runway /20") if qualified else None,
            "Trading Activity /20": item.get("Trading activity /20") if qualified else None,
            "Dilution /15": item.get("Dilution overhang /15") if qualified else None,
            "Hedge-Fund Accumulation /10": item.get("Hedge-fund accumulation /10") if qualified else None,
            "PDUFA Timing /5": item.get("PDUFA timing /5") if qualified else None,
            "Cash Runway (months)": item.get("Cash runway (months)"),
            "Cash Runway Trend": item.get("Cash runway trend"),
            "Financing Watch": item.get("Financing watch"),
            "Dilution Warning": item.get("GEM 3 dilution status"),
            "Hedge-Fund Signal": item.get("Hedge-fund signal"),
            "Hedge-Fund Managers Adding": item.get("Hedge-fund managers adding"),
            "Insider Form 4 Signal": item.get("Insider Form 4 signal"),
            "Insider Purchases": item.get("Insider open-market purchases"),
            "Insider Sales": item.get("Insider open-market sales"),
            "Risks / Evidence Gaps": item.get("Two-benchmark risk flags"),
            "Phase 3 Source": item.get("Phase 3 source"),
            "Financing Source": item.get("Financing source"),
            "PDUFA Source": item.get("PDUFA source"),
            "Hedge-Fund Source Links": item.get("Hedge-fund source links"),
            "Insider Source Links": item.get("Insider source links"),
            "Exact Program / Event": item.get("Exact event"),
            # Internal boolean for filtering and audits, not an extra gate.
            "_eligible": qualified,
        })
    return result
