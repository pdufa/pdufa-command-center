"""Explain Phase-3-qualified GEM research with optional financing review.

Clinical qualification is exact-program and independent of the optional second
financing. Missing SEC evidence is a risk flag, not research disqualification.
"""
from __future__ import annotations

from collections import Counter
import csv
from pathlib import Path

PHASE3_PASS = "PASS — VERIFIED RESULTS RELEASE"
FINANCING_PASS = "PASS — TWO POST-READOUT CLOSES"

GROUPS = (
    "Phase 3 qualified — financing verified",
    "Phase 3 qualified — financing optional / unverified",
    "Awaiting Phase 3 verification — financing observed",
    "Awaiting Phase 3 verification",
)


def classify(row, *, sec_current=False, feed_current=False, finance_recheck=None):
    """Return a conservative display diagnosis; never modify a trading gate."""
    phase3 = row.get("Phase 3 Verified") == PHASE3_PASS
    financed = row.get("Second Financing Closed") == FINANCING_PASS
    eligible = row.get("_eligible") is True
    # A verified financing alone can NEVER create clinical eligibility.
    if phase3 and eligible:
        group = GROUPS[0] if financed else GROUPS[1]
    elif financed:
        group = GROUPS[2]
    else:
        group = GROUPS[3]
    missing = []
    if not phase3:
        missing.append("Exact-program dated Phase 3 results + source / NCT identity")
    if not financed:
        missing.append("Optional: second financing not verified; inspect cash runway, dilution and SEC evidence")
    if phase3 != eligible:
        missing.append("Saved research eligibility conflicts with Phase 3 evidence")
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
        "Missing / recheck needed": "; ".join(missing) or "Clinical evidence verified; review current risks",
        "Latest SEC transaction audit": attempt,
        "GEM eligible — saved": eligible and phase3,
        "Current SEC source": "CURRENT" if sec_current else "BLOCKED / STALE / NOT VERIFIED",
        "Current clinical feed": "CURRENT" if feed_current else "STALE / NOT VERIFIED",
    }


def report_rows(master_rows, *, sec_current=False, feed_current=False, rechecks=(), clinical_rechecks=()):
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
    clinical_by_event, clinical_duplicate = {}, set()
    for record in clinical_rechecks or ():
        key = str(record.get("event_key") or "").strip()
        if not key:
            continue
        if key in clinical_by_event:
            clinical_duplicate.add(key)
        else:
            clinical_by_event[key] = record
    for key in clinical_duplicate:
        clinical_by_event.pop(key, None)
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
            "Latest Phase 3 registry audit": (
                clinical_by_event.get(event, {}).get("source_recheck_status")
                or "NOT RUN / NO MATCH"
            ),
            "Registry audit needed": (
                clinical_by_event.get(event, {}).get("verification_needed") or ""
            ),
        })
    return result


def group_counts(details):
    counts = Counter(row.get("Verification group") for row in details)
    return {name: counts.get(name, 0) for name in GROUPS}


def load_saved_rechecks(root, filename):
    """Read research-only source checks without treating old files as a PASS."""
    if filename not in ("gem_two_close_recheck.csv", "gem_phase3_exact_recheck.csv"):
        raise ValueError("Unsupported GEM audit file")
    try:
        with (Path(root) / filename).open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error):
        return []
