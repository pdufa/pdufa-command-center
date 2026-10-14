"""Potential GEM research list from unique, saved exact-program source leads.

Phase 3 registry postings and historical financing records are OBSERVATIONS,
not GEM qualification. A stock may be worth researching without being ready to
trade. The two independent GEM entry benchmarks are never changed here.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime

POSITIVE_RESULT_LABELS = {
    "RESULTS_VERIFIED", "VERIFIED_SUCCESS", "PRIMARY_MET_VERIFIED",
}
RESOLVED = {"APPROVED", "CRL", "REJECTED", "WITHDRAWN", "REFUSED"}
HISTORICAL_TWO_CLOSE = "VERIFIED_SECOND_POST_PHASE3_FINANCING"
REGISTRY_POSTED = "POSTED_RESULTS_DISCOVERY_ONLY"


def _rows(path):
    try:
        with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except (OSError, csv.Error, UnicodeError):
        return []


def _unique(rows, key="event_key"):
    """Never use evidence with an empty or duplicated program identifier."""
    out, duplicated = {}, set()
    for row in rows:
        k = str(row.get(key) or "").strip()
        if not k:
            continue
        if k in out:
            duplicated.add(k)
        else:
            out[k] = row
    for k in duplicated:
        out.pop(k, None)
    return out


def _parse_date(v):
    try:
        return date.fromisoformat(str(v or "").strip()[:10])
    except (ValueError, TypeError):
        return None


def build_potential_list(root="data", *, as_of=None):
    """Return (active, timing_hold), with audit-grounded reasons and next steps.

    Active is a *research* watchlist. Past/resolved events are reported in a
    separate historical/timing hold section, not silently requalified.
    """
    root = Path(root)
    today = as_of or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    events = _unique(_rows(root / "pdufa_candidates.csv"))
    trials = _unique(_rows(root / "gem_phase3_exact_recheck.csv"))
    financing = _unique(_rows(root / "gem_two_close_recheck.csv"))
    if not events:
        return [], []

    active, holds = [], []
    for key, event in events.items():
        ticker = str(event.get("ticker") or "").strip().upper()
        if not ticker or not str(event.get("drug") or "").strip():
            continue
        trial = trials.get(key, {})
        funding = financing.get(key, {})
        phase = str(event.get("phase3_status") or "").strip().upper()
        # A known Phase 1/2 posting is not a Phase 3 result, even if it has a date.
        phase3_excluded = phase == "PHASE_1_2_NOT_PHASE_3"
        registry = (trial.get("source_recheck_status") == REGISTRY_POSTED and
                    trial.get("nct_results_posted") and not phase3_excluded)
        dated_source = (phase in POSITIVE_RESULT_LABELS and
                        _parse_date(event.get("phase3_date")) is not None and
                        _parse_date(event.get("phase3_date")) <= today and
                        str(event.get("trial_evidence_url") or "").startswith("https://")
                        and not phase3_excluded)
        readout_review = (phase == "RESULTS_REVIEW" and
                          _parse_date(event.get("phase3_date")) is not None and
                          _parse_date(event.get("phase3_date")) <= today and
                          str(event.get("trial_evidence_url") or "").startswith("https://")
                          and not phase3_excluded)
        finance_lead = funding.get("historical_audit_status") == HISTORICAL_TWO_CLOSE

        if not (registry or dated_source or readout_review or finance_lead):
            continue

        reasons = []
        needed = []
        if dated_source:
            reasons.append("Dated, source-linked Phase 3 readout in saved program ledger")
            needed.append("Independently adjudicate exact trial identity and Phase 3 outcome")
        elif readout_review:
            reasons.append("Dated issuer/SEC Phase 3 result source cited (result still in review)")
            needed.append("Confirm exact Phase 3 trial, endpoint result and dated issuer release")
        elif registry:
            nct = str(trial.get("nct_results_posted") or "").replace(" | ", ", ")
            reasons.append("Results posted on ClinicalTrials.gov for " + nct +
                           " (research lead, not confirmed positive Phase 3)")
            needed.append("Match posted study to correct Phase 3 drug/indication and issuer readout")
        else:
            needed.append("Find source-linked exact-program Phase 3 results, date and trial ID")

        sec1 = funding.get("first_sec_status") == "VERIFIED"
        sec2 = funding.get("second_sec_status") == "VERIFIED"
        verified_transactions = int(sec1) + int(sec2)
        if finance_lead:
            if verified_transactions == 2:
                reasons.append("Historical two-close financing claim; both cited SEC documents rechecked")
                needed.append("Confirm separate qualifying financing deals AFTER the verified Phase 3 readout")
            else:
                reasons.append("Historical two-close financing claim; " +
                               str(verified_transactions) + "/2 SEC documents rechecked")
                needed.append("Reverify missing SEC transactions and two separate post-readout closes")
        else:
            needed.append("Verify two distinct post-Phase 3 financings and second closing")

        pdufa = _parse_date(event.get("pdufa_date"))
        outcome = str(event.get("outcome") or "").strip().upper()
        resolved = outcome in RESOLVED
        window_end = bool(pdufa is not None and (pdufa - today).days <= 3)
        on_hold = resolved or window_end
        if resolved:
            timing_note = "FDA outcome already recorded: " + outcome
        elif window_end:
            timing_note = "At/past planned PDUFA −3 exit boundary; not a new-entry research setup"
        else:
            timing_note = "Timing unresolved / check dated PDUFA source"
            if pdufa:
                timing_note = "Reported PDUFA " + pdufa.isoformat() + " (verify current source)"

        row = {
            "Ticker": ticker,
            "Drug": str(event.get("drug") or ""),
            "Indication": str(event.get("indication") or ""),
            "Why potential": "; ".join(reasons),
            "Still needed": "; ".join(dict.fromkeys(needed)),
            "GEM status": "POTENTIAL — RESEARCH ONLY / NOT QUALIFIED",
            "Evidence type": ("Phase 3 + financing" if (registry or dated_source or readout_review) and finance_lead
                              else "Historical financing" if finance_lead else "Phase 3 data"),
            "SEC documents rechecked": verified_transactions,
            "NCT ID": str(event.get("nct_id") or trial.get("nct_ids") or ""),
            "PDUFA date (saved)": str(event.get("pdufa_date") or ""),
            "Timing / resolution": timing_note,
            "Exact program": key,
            "Clinical source": str(event.get("trial_evidence_url") or trial.get("saved_trial_source") or ""),
            "Financing SEC source": str(funding.get("second_sec_url") or ""),
            "Source review date": str(trial.get("checked_at_utc") or funding.get("checked_at_utc") or "")[:10],
            "_order": (
                0 if (registry or dated_source or readout_review) and finance_lead else
                1 if finance_lead else 2,
                -verified_transactions,
                ticker, key,
            ),
        }
        (holds if on_hold else active).append(row)

    for group in (active, holds):
        group.sort(key=lambda row: row["_order"])
        for row in group:
            row.pop("_order", None)
    return active, holds
