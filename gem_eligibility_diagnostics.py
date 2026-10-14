"""Explain GEM's exactly two saved eligibility benchmarks without changing them.

Buckets are derived from the same exact-event PASS markers as gem_master_list.
Source freshness is displayed separately and can never create an eligible row.
"""
from __future__ import annotations

from collections import Counter

PHASE3_PASS = "PASS — VERIFIED RESULTS RELEASE"
FINANCING_PASS = "PASS — TWO POST-READOUT CLOSES"

GROUPS = (
    "Eligible — saved evidence",
    "Awaiting financing verification",
    "Awaiting Phase 3 verification",
    "Awaiting both verifications",
)


def classify(row, *, sec_current=False, feed_current=False, finance_recheck=None):
    """Return a conservative display diagnosis; never modify a trading gate."""
    phase3 = row.get("Phase 3 Verified") == PHASE3_PASS
    financed = row.get("Second Financing Closed") == FINANCING_PASS
    eligible = row.get("_eligible") is True
    # A contradictory saved marker cannot create a positive diagnosis.
    if eligible and phase3 and financed:
        group = GROUPS[0]
    elif phase3 and not financed:
        group = GROUPS[1]
    elif financed and not phase3:
        group = GROUPS[2]
    else:
        group = GROUPS[3]
    missing = []
    if not phase3:
        missing.append("Exact-program dated Phase 3 results + source / NCT identity")
    if not financed:
        missing.append("Two distinct post-readout financing closes + SEC evidence")
    if eligible and group != GROUPS[0]:
        missing.append("Saved eligibility conflicts with benchmark markers")
    if not sec_current:
        missing.append("Current SEC recheck unavailable / blocked (source health)")
    if not feed_current:
        missing.append("Clinical / market source feed stale (source health)")
    recheck = finance_recheck or {}
    attempt = str(recheck.get("recheck_status") or "NOT RUN / NO MATCH")
    if attempt != "NOT RUN / NO MATCH" and attempt != "TRANSACTIONS_RECHECKED_REVIEW":
        missing.append("Latest SEC two-transaction recheck: " + attempt)
    return {
        "Verification group": group,
        "Missing / recheck needed": "; ".join(missing) or "Both saved benchmarks passed; review current risks",
        "Latest SEC transaction audit": attempt,
        "GEM eligible — saved": eligible and group == GROUPS[0],
        "Current SEC source": "CURRENT" if sec_current else "BLOCKED / STALE / NOT VERIFIED",
        "Current clinical feed": "CURRENT" if feed_current else "STALE / NOT VERIFIED",
    }


def report_rows(master_rows, *, sec_current=False, feed_current=False, rechecks=()):
    """One diagnosis per program. Duplicate audit keys never cross-link trials."""
    by_event, ambiguous = {}, set()
    for record in rechecks or ():
        key = str(record.get("event_key") or "").strip()
        if not key:
            continue
        if key in by_event:
            ambiguous.add(key)
        else:
            by_event[key] = record
    for key in ambiguous:
        by_event.pop(key, None)
    result = []
    for row in master_rows:
        event = str(row.get("Exact Program / Event") or "").strip()
        detail = classify(
            row, sec_current=sec_current, feed_current=feed_current,
            finance_recheck=by_event.get(event),
        )
        result.append({
            "Ticker": row.get("Ticker"),
            "Drug": row.get("Drug"),
            "Exact Program / Event": event,
            "Phase 3 Verified": row.get("Phase 3 Verified"),
            "Second Financing Closed": row.get("Second Financing Closed"),
            "Phase 3 Result Date": row.get("Phase 3 Result Date"),
            "Second Financing Close Date": row.get("Second Financing Close Date"),
            **detail,
            "Phase 3 Source": row.get("Phase 3 Source"),
            "Financing Source": row.get("Financing Source"),
        })
    return result


def group_counts(details):
    counts = Counter(row.get("Verification group") for row in details)
    return {name: counts.get(name, 0) for name in GROUPS}
