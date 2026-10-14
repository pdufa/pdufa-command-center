"""Two-benchmark GEM trading-candidate queue with separate, advisory ranking.

The user's only positive eligibility benchmarks:
  (1) verified, publicly released SUCCESSFUL Phase 3 results for the exact drug;
  (2) SEC-attested closing of the SECOND separate post-readout financing.
No cash-runway, market, clinical-success, safety, dilution or FDA-window score
can silently become a third positive benchmark. Scores rank candidates,
not expected returns or an instruction to trade.
"""
from __future__ import annotations

import math
from datetime import date

from post_phase3_unified import parsed_date, https_source

VERIFIED_READOUT_STATES = frozenset((
    "VERIFIED_SUCCESS", "PRIMARY_MET_VERIFIED", "RESULTS_VERIFIED",
    "VERIFIED_FAILURE", "PRIMARY_FAILED_VERIFIED", "VERIFIED_NEGATIVE",
))
POSITIVE_READOUT_STATES = frozenset(("VERIFIED_SUCCESS", "PRIMARY_MET_VERIFIED"))
NEGATIVE_READOUT_STATES = frozenset((
    "VERIFIED_FAILURE", "PRIMARY_FAILED_VERIFIED", "VERIFIED_NEGATIVE",
))
SAFE_DILUTION = frozenset(("NO", "NONE", "FALSE", "0"))
DILUTION_ALERTS = frozenset(("YES", "TRUE", "1", "ACTIVE", "UNRESOLVED"))
WEIGHTS = {
    "Phase 3 quality /30": 30,
    "Financial runway /20": 20,
    "Dilution overhang /15": 15,
    "Trading activity /20": 20,
    "PDUFA timing /5": 5,
    "Hedge-fund accumulation /10": 10,
}
assert sum(WEIGHTS.values()) == 100


def _num(value):
    try:
        if value is None or isinstance(value, bool) or str(value).strip() == "":
            return None
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _bounded(value, cap):
    x = _num(value)
    return min(cap, max(0.0, x)) if x is not None else 0.0


def phase3_results_released(row, event, *, as_of):
    """Require actual source-linked readout, not trial completion or registry date."""
    if not isinstance(event, dict):
        return False
    ticker = str(row.get("Ticker") or "").strip().upper()
    nct = str(row.get("NCT ID") or "").strip().upper()
    key = str(row.get("Exact event") or "").strip()
    event_ticker = str(event.get("ticker") or "").strip().upper()
    event_nct = str(event.get("nct_id") or "").strip().upper()
    source = event.get("trial_evidence_url")
    released = parsed_date(event.get("phase3_date"))
    observed = parsed_date(as_of)
    status = str(event.get("phase3_status") or "").strip().upper()
    return bool(
        ticker and nct and key.startswith(ticker + "|")
        and event_ticker == ticker and event_nct == nct
        and observed and released and released <= observed
        # A published negative or generic "results verified" readout must
        # never pass the successful-Phase-3 GEM eligibility benchmark.
        and status in POSITIVE_READOUT_STATES
        and https_source(source)
    )


def second_financing_closed(row, event, *, as_of):
    """Use independently checked event-key two-close attestation from Stage 1.

    Stage 1 has already compared both actual separate SEC-documented closes
    with this exact program's Phase 3 date. A claimed close, pricing,
    announcement or same-transaction tranche is not evidence of a second close.
    """
    if not isinstance(event, dict):
        return False
    first = parsed_date(event.get("phase3_date"))
    close = parsed_date(row.get("Verified 2nd financing close date"))
    today = parsed_date(as_of)
    return bool(
        row.get("2nd Financing Completed") == "YES — VERIFIED (HISTORICAL)"
        and first and close and today and first <= close <= today
    )


def _runway_points(months):
    n = _num(months)
    if n is None or n < 0:
        return 0
    if n >= 24:
        return 20
    if n >= 18:
        return 17
    if n >= 12:
        return 13
    if n >= 6:
        return 7
    return 2


def _window_points(days, verified):
    """A window preference, NEVER an eligibility requirement."""
    if verified != "VERIFIED — SOURCE LINKED":
        return 0
    if not isinstance(days, int) or isinstance(days, bool):
        return 0
    if 30 <= days <= 90:
        return 5
    if 14 <= days <= 29:
        return 4
    if 91 <= days <= 180:
        return 3
    if days >= 181:
        return 2
    if 4 <= days <= 13:
        return 1
    return 0


def assess(row, event, *, as_of, feed_current=True, sec_current=True):
    """Return two hard benchmarks and a scored priority on qualifying programs."""
    released = phase3_results_released(row, event, as_of=as_of)
    financed = second_financing_closed(row, event, as_of=as_of)
    eligible = bool(released and financed)
    flags = []
    if not feed_current:
        flags.append("Saved clinical/market feed stale — refresh before acting")
    if not sec_current:
        flags.append("Current SEC rescan unavailable — reverify prior closing attestation")
    state = str(event.get("phase3_status") or "").strip().upper() if event else ""
    if state in NEGATIVE_READOUT_STATES:
        flags.append("Verified Phase 3 negative outcome — serious clinical risk")
    if event and str(event.get("conflict_flag") or "").strip().upper() not in (
        "", "NO", "NONE", "FALSE", "0", "PASS"
    ):
        flags.append("Conflicting clinical/regulatory evidence")
    dilution = str(event.get("new_dilution_flag") or "").strip().upper() if event else ""
    if dilution in DILUTION_ALERTS:
        flags.append("New or unresolved dilution reported")
    elif dilution not in SAFE_DILUTION:
        flags.append("Dilution exposure not independently cleared")
    runway = _num(row.get("Cash runway (months)"))
    if runway is None:
        flags.append("Cash runway unknown or stale")
    elif runway < 12:
        flags.append("Under 12 months of estimated cash runway")
    if str(row.get("Cash runway trend") or "").startswith("DECLINING"):
        flags.append("Cash runway has materially declined")
    days = row.get("Days to PDUFA")
    if isinstance(days, int) and not isinstance(days, bool) and days <= 3:
        flags.append("Inside PDUFA -3 planned exit boundary; pre-decision setup expired")
    elif not isinstance(days, int) or isinstance(days, bool):
        flags.append("PDUFA window not verified")
    elif row.get("PDUFA verification") != "VERIFIED — SOURCE LINKED":
        flags.append("PDUFA date needs source verification")
    if event and str(event.get("outcome") or "").upper() in (
        "APPROVED", "CRL", "REJECTED", "WITHDRAWN", "REFUSED"
    ):
        flags.append("FDA event already resolved; not a pre-PDUFA opportunity")

    out = {
        "Benchmark 1 — Phase 3 released": "PASS — VERIFIED RESULTS RELEASE" if released
                                          else "PENDING — VERIFIED READOUT MISSING",
        "Benchmark 2 — Financing #2 closed": "PASS — TWO POST-READOUT CLOSES" if financed
                                          else "PENDING — SECOND CLOSE UNVERIFIED",
        "Two-benchmark entry status": (
            "QUALIFIED — PRIORITIZE FOR MANUAL ENTRY REVIEW"
            if eligible else "WATCH — TWO BENCHMARKS NOT YET MET"
        ),
        "Two-benchmark eligible": eligible,
        "Two-benchmark priority /100": None,
        "Two-benchmark rank": None,
        "Two-benchmark risk flags": "; ".join(flags) or "No flagged issue in saved data",
    }
    if not eligible:
        return out
    # Score clinical quality using independently assessed details, rather
    # than treating a dated readout as an automatically successful result.
    clinical = round(_bounded(row.get("Clinical evidence /30"), 30))
    if state in NEGATIVE_READOUT_STATES:
        clinical = 0
    elif state not in POSITIVE_READOUT_STATES:
        clinical = min(clinical, 12)
    if event and str(event.get("conflict_flag") or "").strip().upper() not in (
        "", "NO", "NONE", "FALSE", "0", "PASS"
    ):
        clinical = 0
    technical = round(
        12 * _bounded(row.get("Trading setup /20"), 20) / 20
        + 8 * _bounded(row.get("Market activity /10"), 10) / 10
    )
    hedge = row.get("Hedge-fund accumulation /10")
    hedge_points = int(min(10, _bounded(hedge, 10))) if (
        row.get("Hedge-fund signal") == "SOURCE-VERIFIED QUARTERLY 13F HOLDINGS"
    ) else 0
    points = {
        "Phase 3 quality /30": clinical,
        "Financial runway /20": _runway_points(runway),
        "Dilution overhang /15": 15 if dilution in SAFE_DILUTION else 0,
        "Trading activity /20": technical if feed_current else 0,
        "PDUFA timing /5": _window_points(days, row.get("PDUFA verification")),
        "Hedge-fund accumulation /10": hedge_points,
    }
    out.update(points)
    out["Two-benchmark priority /100"] = sum(points.values())
    return out


def assign_ranks(rows):
    """Prioritize eligible records only; missing factors remain zero, not invented."""
    qualified = [row for row in rows if row.get("Two-benchmark eligible") is True]
    qualified.sort(key=lambda row: (
        -int(row.get("Two-benchmark priority /100") or 0),
        str(row.get("Ticker") or ""), str(row.get("Exact event") or ""),
    ))
    for place, row in enumerate(qualified, 1):
        row["Two-benchmark rank"] = place
    return qualified
