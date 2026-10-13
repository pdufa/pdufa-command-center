"""Absolute, independent GEM trade-entry financing prerequisite.

A historical mention, proposed offering, priced transaction, or a ticker-only
match never proves two SEPARATE closes after the exact program's Phase 3
readout. This checks persisted, reviewer-audited primary-source assertions,
NOT the live contents of SEC filings. An independently fresh SEC recheck and
all remaining entry gates are still required before entry consideration.
"""
from __future__ import annotations

from datetime import date, datetime

from step7_entry import safe_source


def parsed_date(value):
    try:
        return date.fromisoformat(str(value or "").strip()[:10])
    except (ValueError, TypeError):
        return None


def second_post_phase3_close(event_key, phase3_date, stage, *, as_of):
    """Return (verified, second_close_date, reason); reject uncertainty."""
    today = as_of.date() if isinstance(as_of, datetime) else as_of
    if not isinstance(today, date):
        raise ValueError("as_of must be a date")
    if not isinstance(stage, dict) or not event_key or stage.get("event_key") != event_key:
        return False, None, "EXACT EVENT FINANCING RECORD MISSING OR CONFLICTED"
    state = str(stage.get("second_financing_status") or "").strip().upper()
    if (state not in ("CLOSED", "FINISHED")
            or str(stage.get("second_financing_closed") or "").strip().upper() != "YES"
            or str(stage.get("second_financing_audit_status") or "").strip().upper()
               != "VERIFIED_SECOND_POST_PHASE3_FINANCING"):
        return False, None, "CLOSURE #2 NOT INDEPENDENTLY ATTESTED"
    readout = parsed_date(phase3_date)
    first = parsed_date(stage.get("first_financing_date"))
    second = parsed_date(stage.get("second_financing_date"))
    if not (readout and first and second and readout <= first < second <= today):
        return False, None, "TWO DISTINCT POST-READOUT CLOSING DATES NOT VERIFIED"
    if not (safe_source(stage.get("first_financing_source"), sec=True)
            and safe_source(stage.get("second_financing_source"), sec=True)):
        return False, None, "PRIMARY SEC CLOSING EVIDENCE MISSING"
    checked = parsed_date(stage.get("verified_as_of"))
    if checked is None or not 0 <= (today - checked).days <= 7:
        return False, None, "FINANCING VERIFICATION STALE OR FUTURE DATED"
    return True, second.isoformat(), ""


def entry_status(*, closed, qualified, feed_current, days_to_pdufa,
                 excluded=False):
    """Manual-entry REVIEW classification. Never submits an order."""
    if excluded:
        return "NO ENTRY — FDA EVENT RESOLVED"
    if isinstance(days_to_pdufa, int) and days_to_pdufa <= 3:
        return "NO NEW ENTRY — PDUFA −3 EXIT BOUNDARY"
    # Pre-financing must ALWAYS remain watch-only, regardless of any score.
    if not closed:
        return "WATCH ONLY — SECOND FINANCING NOT VERIFIED CLOSED"
    if not feed_current:
        return "HOLD — STALE SOURCE EVIDENCE"
    if qualified:
        return "POST-CLOSE ENTRY REVIEW ELIGIBLE — NOT A TRADE ORDER"
    return "POST-CLOSE REVIEW — OTHER ENTRY GATES NOT MET"
