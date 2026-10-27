"""Full-coverage GEM Phase 3 + two-financing review of the saved financing block.

This reviews EVERY exact-event row in second_financing_status.csv, even when the
historical second close is absent. It makes investigation work visible without
inventing readout dates, document contents, or verifying SEC URL freshness.
The program-level two-benchmark clearance engine remains the sole authority for
promoting a row. Trade-entry authorization is always separate.
"""
from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from gem_verified_snapshot import source_cleared_gems
from gem_secondary_research import research_search_links

TWO_CLOSE_ATTESTED = "VERIFIED_SECOND_POST_PHASE3_FINANCING"
POSITIVE_PHASE3 = {"VERIFIED_SUCCESS", "PRIMARY_MET_VERIFIED", "RESULTS_VERIFIED"}
NON_PHASE3 = {"PHASE_1_2_NOT_PHASE_3", "NO_QUALIFYING_PHASE3"}
RESOLVED = {"APPROVED", "CRL", "REJECTED", "WITHDRAWN", "REFUSED"}
NCT = re.compile(r"^NCT\d{8}$")


def _read(path):
    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    except (OSError, UnicodeError, csv.Error):
        return []


def _unique(rows):
    by_key, duplicated = {}, set()
    for row in rows:
        key = str(row.get("event_key") or "").strip()
        if not key:
            continue
        if key in by_key:
            duplicated.add(key)
        else:
            by_key[key] = row
    for key in duplicated:
        by_key.pop(key, None)
    return by_key, duplicated


def _normalized_drug(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def _phase3_source_leads(rows, event, *, today):
    """Conservative exact-NCT or exact-drug match to independent result ledger.

    These are ONLY retrieval leads. Registry postings and issuer-release URLs
    require endpoint, success, safety, and indication adjudication by a reviewer.
    """
    ticker = str(event.get("ticker") or "").upper().strip()
    nct = str(event.get("nct_id") or "").upper().strip()
    drug = _normalized_drug(event.get("drug"))
    collected = {}
    for row in rows:
        if str(row.get("ticker") or "").upper().strip() != ticker:
            continue
        trial = str(row.get("nct_id") or "").upper().strip()
        alt_drug = _normalized_drug(row.get("drug"))
        matched_nct = bool(NCT.fullmatch(nct) and trial == nct)
        matched_drug = bool(drug and alt_drug and drug == alt_drug)
        if not (matched_nct or matched_drug):
            continue
        if not NCT.fullmatch(trial):
            continue
        published = _date(row.get("phase3_results_posted_at"))
        source = str(row.get("phase3_results_source") or "")
        if (str(row.get("source_type") or "") not in {
                "CLINICALTRIALS_RESULTS", "ISSUER_TOPLINE_RELEASE"}
                or not published or published > today or
                not source.startswith("https://")):
            continue
        key = (trial, str(row.get("source_type")), source)
        collected[key] = {
            "nct": trial, "date": published.isoformat(), "source": source,
            "type": str(row.get("source_type")),
        }
    return sorted(collected.values(), key=lambda x: (
        x["type"] != "ISSUER_TOPLINE_RELEASE", x["date"], x["nct"]
    ))


def _date(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except (ValueError, TypeError):
        return None


def build_financing_review(root="data", *, as_of=None):
    """Return (one row PER financing key, audit summary).

    Fail closed for missing/duplicate events, unverifiable financing, and
    unverified clinical dates. A historical second-close claim is never a
    positive benchmark result by itself.
    """
    root = Path(root)
    today = as_of or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    if not isinstance(today, date):
        raise ValueError("as_of must be a date")
    financing_rows = _read(root / "second_financing_status.csv")
    clinical_announcements = _read(root / "phase3_announcements.csv")
    events, duplicate_event_keys = _unique(_read(root / "pdufa_candidates.csv"))
    finance, duplicate_finance_keys = _unique(financing_rows)
    cleared, historical, global_sec_current = source_cleared_gems(root, as_of=today)
    # GEM research membership now permits an optional second financing. That
    # clinical qualification is not the two-close certification this report
    # displays. Keep the finance denominator exact and fail closed for missing
    # or duplicated funding records without changing GEM membership itself.
    def financing_certified(record):
        key = record["Exact program"]
        return (record.get("Second financing verified") is True
                and key in finance and key in events
                and key not in duplicate_finance_keys
                and key not in duplicate_event_keys)

    cleared = [record for record in cleared if financing_certified(record)]
    historical = [record for record in historical if financing_certified(record)]
    clearance = {x["Exact program"]: (x, False) for x in cleared}
    clearance.update({x["Exact program"]: (x, True) for x in historical})
    rows = []
    for event_key in sorted({str(r.get("event_key") or "").strip()
                             for r in financing_rows if r.get("event_key")}):
        financing = finance.get(event_key, {})
        event = events.get(event_key, {})
        ticker = str(event.get("ticker") or event_key.split("|")[0]).strip().upper()
        drug = str(event.get("drug") or "").strip()
        indication = str(event.get("indication") or "").strip()
        nct = str(event.get("nct_id") or "").strip().upper()
        leads = _phase3_source_leads(clinical_announcements, event, today=today)
        phase_date = _date(event.get("phase3_date"))
        first = _date(financing.get("first_financing_date"))
        second = _date(financing.get("second_financing_date"))
        fin_type = str(financing.get("second_financing_audit_status") or "").strip()
        issue = []
        ambiguous = (event_key in duplicate_finance_keys or
                     event_key in duplicate_event_keys or not financing or not event or
                     ticker != event_key.split("|")[0].upper())
        excluded_phase3 = (str(event.get("phase3_status") or "").upper() in NON_PHASE3
                           or fin_type in NON_PHASE3)
        phase3_verified = bool(
            phase_date and phase_date <= today
            and str(event.get("phase3_status") or "").strip().upper() in POSITIVE_PHASE3
            and bool(NCT.fullmatch(nct))
            and str(event.get("trial_evidence_url") or "").startswith("https://")
        )
        if ambiguous:
            issue.append("Resolve duplicated/missing exact regulatory or financing event")
        if excluded_phase3:
            issue.append("Confirm the program is a qualifying completed Phase 3, not Phase 2/3")
        elif not phase3_verified:
            if not NCT.fullmatch(nct):
                issue.append("Find exact Phase 3 NCT and match drug/indication")
            if not phase_date or phase_date > today:
                issue.append("Verify actual dated Phase 3 results readout at company IR / SEC")
            if str(event.get("phase3_status") or "").strip().upper() not in POSITIVE_PHASE3:
                issue.append("Verify positive Phase 3 primary endpoint and safety")
            if not str(event.get("trial_evidence_url") or "").startswith("https://"):
                issue.append("Attach company primary Phase 3 results source")
        if fin_type == TWO_CLOSE_ATTESTED:
            if not (first and second and phase_date and phase_date <= first < second <= today):
                issue.append("Prove both distinct closings occurred AFTER verified readout")
            if not (str(financing.get("first_financing_source") or "").startswith(
                    "https://www.sec.gov/Archives/edgar/data/") and
                    str(financing.get("second_financing_source") or "").startswith(
                    "https://www.sec.gov/Archives/edgar/data/")):
                issue.append("Attach two exact SEC closing/funding filings")
            if not financing.get("verified_as_of") or (
                _date(financing["verified_as_of"]) is None or
                not 0 <= (today - _date(financing["verified_as_of"])).days <= 7
            ):
                issue.append("Refresh dated SEC two-close attestation")
        elif fin_type in {"ONE_POST_PHASE3_CLOSE_VERIFIED_SECOND_NOT_FOUND",
                          "ONE_POST_PHASE3_CLOSE_VERIFIED_SECOND_NOT_PROVEN"}:
            issue.append("Find SEC evidence of SECOND distinct funded post-readout close")
        else:
            issue.append("Find and verify TWO distinct funded post-readout financings")
        saved_pdufa = _date(event.get("pdufa_date"))
        days_to_pdufa = (saved_pdufa - today).days if saved_pdufa else None
        pdufa_verified = bool(
            str(event.get("pdufa_confirmation") or "").startswith("VERIFIED")
            and str(event.get("pdufa_evidence_url") or "").startswith("https://")
        )
        if days_to_pdufa is None:
            timing_window = "DATE UNKNOWN"
        elif days_to_pdufa <= 3:
            timing_window = "EXIT/RESOLVED"
        elif days_to_pdufa <= 13:
            timing_window = "4–13 DAYS"
        elif days_to_pdufa <= 30:
            timing_window = "14–30 DAYS"
        elif days_to_pdufa <= 90:
            timing_window = "31–90 DAYS — PRIORITY"
        else:
            timing_window = ">90 DAYS"
        outcome = str(event.get("outcome") or "").strip().upper()
        time_closed = bool(
            outcome in RESOLVED
            or str(event.get("check_status") or "").strip().upper().startswith("RESOLVED_")
            or str(event.get("monitor_eligibility") or "").strip().upper() == "EXCLUDED"
            or (saved_pdufa and (saved_pdufa - today).days <= 3)
        )
        cert, certified_historical = clearance.get(event_key, (None, False))
        if cert is not None:
            classification = ("CLEARED 2/2 — HISTORICAL / EXIT"
                              if certified_historical else "CLEARED 2/2 — ACTIVE RESEARCH")
            issue = [cert["Still needed"]]
            priority = 0 if not certified_historical else 5
        elif time_closed:
            classification = "HISTORICAL / EXIT — NOT NEW ENTRY"
            priority = 6
        elif ambiguous:
            classification = "EVENT IDENTITY CONFLICT — MANUAL CHECK"
            priority = 7
        elif excluded_phase3:
            classification = "NO QUALIFYING PHASE 3 YET — REVIEW"
            priority = 8
        elif fin_type == TWO_CLOSE_ATTESTED:
            classification = "PRIORITY — TWO-CLOSE LEAD; AUDIT P3 / SEC"
            priority = 1 if phase3_verified else 2
        elif phase3_verified:
            classification = "PRIORITY — P3 VERIFIED; FIND FINANCING"
            priority = 3
        else:
            classification = "RESEARCH — CLINICAL + FINANCING INCOMPLETE"
            priority = 4
        if leads and not phase3_verified and not excluded_phase3:
            issue.append(
                f"Review {len(leads)} matched Phase 3 issuer/registry source lead(s); "
                "do not treat a posted result as endpoint verification"
            )
        links = research_search_links({
            "Ticker": ticker, "Drug": drug, "Indication": indication, "NCT ID": nct
        })
        rows.append({
            "Ticker": ticker, "Drug": drug, "Indication": indication,
            "Exact program": event_key, "NCT ID": nct,
            "Review status": classification,
            "Phase 3 source-clear": bool(phase3_verified and not ambiguous and not excluded_phase3),
            "Phase 3 readout date": str(event.get("phase3_date") or ""),
            "Primary clinical source": str(event.get("trial_evidence_url") or ""),
            "Matched Phase 3 source leads": len(leads),
            "Phase 3 discovery examples": "; ".join(
                x["nct"] + " " + x["date"] + " " + x["type"]
                for x in leads[:4]),
            "Phase 3 discovery source": leads[0]["source"] if leads else "",
            "Financing ledger claim": fin_type or "NO HISTORICAL CLOSURE ATTESTATION",
            "Financing close #1": str(financing.get("first_financing_date") or ""),
            "Financing source #1": str(financing.get("first_financing_source") or ""),
            "Financing close #2": str(financing.get("second_financing_date") or ""),
            "Financing source #2": str(financing.get("second_financing_source") or ""),
            "PDUFA (saved)": str(event.get("pdufa_date") or ""),
            "PDUFA days left": days_to_pdufa,
            "PDUFA window": timing_window,
            "PDUFA date verified": pdufa_verified,
            "PDUFA primary source": str(event.get("pdufa_evidence_url") or ""),
            "Missing evidence / next actions": "; ".join(dict.fromkeys(issue)),
            "Investor news / source search": links.get("confirmed_issuer_news")
                or links.get("find_issuer_news", ""),
            "SEC program search": links.get("sec_program_search", ""),
            "ClinicalTrials.gov search": links.get("clinical_trials", ""),
            "Reddit leads (not evidence)": links.get("reddit_program", ""),
            "Two benchmark clearance": cert is not None,
            "Trade entry authorized": False,
            "Priority": priority,
        })
    rows.sort(key=lambda x: (x["Priority"], x["Ticker"], x["Exact program"]))
    status_count = Counter(x["Review status"] for x in rows)
    return rows, {
        "as_of_pacific": today.isoformat(),
        "financing_programs_reviewed": len(rows),
        "unique_tickers": len({x["Ticker"] for x in rows}),
        "saved_phase3_result_ledger_rows": len(clinical_announcements),
        "financing_programs_with_matched_phase3_source_leads": sum(
            x["Matched Phase 3 source leads"] > 0 for x in rows),
        "historically_attested_two_close": sum(
            x["Financing ledger claim"] == TWO_CLOSE_ATTESTED for x in rows),
        "active_benchmark_cleared": len(cleared),
        "historical_benchmark_cleared": len(historical),
        "pending_or_excluded": len(rows) - len(cleared) - len(historical),
        "global_sec_financing_source_current": global_sec_current,
        "trade_entries_authorized": 0,
        "by_status": dict(sorted(status_count.items())),
        "caveat": ("All financing-block exact events reviewed from SAVED records. "
                   "Research searches are links, not completed internet or SEC "
                   "recrawls. New qualifications need validated official "
                   "clinical and two-funding evidence; trade gates separate."),
    }
