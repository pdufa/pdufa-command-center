"""Generate Stage 3 research tasks from the EXISTING dated ledgers.

This is a missing-evidence worklist, NOT a historical trade dataset. A
retrospective financing status cannot prove the document was public on
the closing day; first/second public dates must be researched separately.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from post_phase3_trade_backtest import day, https, read_csv, KEY, NCT

FIELDS = (
    "priority", "event_key", "ticker", "issuer_cik", "drug", "indication",
    "nct_id", "phase3_readout_date_reference", "phase3_status_reference",
    "phase3_source_reference", "first_financing_close_date_reference",
    "first_financing_source_reference", "second_financing_close_date_reference",
    "second_financing_source_reference", "financing_audit_status_reference",
    "financing_evidence_note", "pdufa_date_reference",
    "pdufa_status_reference", "pdufa_source_reference", "fda_outcome_reference",
    "missing_historical_requirements", "next_research_step",
    "eligible_for_historical_trade_backtest",
)


def build_backfill_queue(root):
    root = Path(root)
    reg = read_csv(root/"pdufa_candidates.csv")
    funding = read_csv(root/"second_financing_status.csv")
    companies = read_csv(root/"company_registry.csv")
    counts = Counter(str(r.get("event_key") or "").strip() for r in reg)
    fundcounts = Counter(str(r.get("event_key") or "").strip() for r in funding)
    financings = {
        str(r.get("event_key") or "").strip(): r
        for r in funding if str(r.get("event_key") or "").strip()
    }
    cikcounts = Counter(str(r.get("ticker") or "").upper().strip() for r in companies)
    ciks = {
        str(r.get("ticker") or "").upper().strip(): str(r.get("cik10") or "").strip()
        for r in companies if str(r.get("ticker") or "").strip()
    }
    out = []
    for event in reg:
        key = str(event.get("event_key") or "").strip()
        ticker = str(event.get("ticker") or "").upper().strip()
        nct = str(event.get("nct_id") or "").strip()
        cik = ciks.get(ticker, "")
        finance = financings.get(key, {})
        f1 = day(finance.get("first_financing_date"))
        f2 = day(finance.get("second_financing_date"))
        date_ok = bool(f1 and f2 and f1 < f2)
        fund_links = (https(finance.get("first_financing_source"), sec=True, cik=cik)
                      and https(finance.get("second_financing_source"), sec=True, cik=cik)) if cik and cikcounts[ticker] == 1 else False
        historical_funding_candidate = (
            KEY.fullmatch(key) and key.split("|")[0] == ticker and
            counts[key] == 1 and fundcounts[key] == 1 and
            date_ok and fund_links and
            finance.get("second_financing_audit_status") ==
                "VERIFIED_SECOND_POST_PHASE3_FINANCING" and
            finance.get("second_financing_closed") == "YES"
        )
        missing = []
        if not KEY.fullmatch(key) or key.split("|")[0] != ticker:
            missing.append("EXACT_EVENT_IDENTITY")
        if counts[key] != 1 or fundcounts[key] > 1:
            missing.append("DUPLICATE_OR_AMBIGUOUS_EVENT_RECORD")
        if not NCT.fullmatch(nct):
            missing.append("CLINICAL_TRIAL_NCT_ID")
        if not day(event.get("phase3_date")) or not https(event.get("trial_evidence_url")):
            missing.append("SOURCE_DATED_PHASE3_READOUT")
        if str(event.get("phase3_status")) not in {"VERIFIED_SUCCESS", "PRIMARY_MET_VERIFIED"}:
            missing.append("PRIMARY_ENDPOINT_BENEFIT_SAFETY_ADJUDICATION")
        if not historical_funding_candidate:
            missing.append("TWO_DISTINCT_SAME_ISSUER_SEC_FINANCING_CLOSES")
        # Ledger actual closing dates are not their public announcement dates.
        missing.append("FINANCING_1_AND_2_FIRST_PUBLIC_DATES")
        if (event.get("pdufa_confirmation") != "VERIFIED" or
                not https(event.get("pdufa_evidence_url"))):
            missing.append("SOURCE_VERIFIED_HISTORICAL_PDUFA_GOAL")
        missing.append("HISTORICAL_PDUFA_FIRST_PUBLIC_DATE_AND_CHANGES")
        missing.append("SPLIT_ADJUSTED_HISTORICAL_DAILY_OHLCV")
        missing.append("INDEPENDENT_POINT_IN_TIME_DOCUMENT_REVIEW")
        if historical_funding_candidate:
            priority = "1 — DUAL FINANCING LEDGER REVIEW"
            next_step = "Find exact public availability dates for both SEC closes; then issuer Phase 3 readout and historical prices"
        elif finance:
            priority = "2 — FINANCING EVIDENCE REVIEW"
            next_step = "Reconcile financing order, issuer CIK, document dates and whether two closes actually occurred"
        else:
            priority = "3 — CLINICAL EVENT DISCOVERY"
            next_step = "Confirm exact Phase 3 program, first results announcement and financing events"
        out.append({
            "priority":priority, "event_key":key, "ticker":ticker,
            "issuer_cik":cik, "drug":str(event.get("drug") or ""),
            "indication":str(event.get("indication") or ""), "nct_id":nct,
            "phase3_readout_date_reference":str(event.get("phase3_date") or ""),
            "phase3_status_reference":str(event.get("phase3_status") or ""),
            "phase3_source_reference":str(event.get("trial_evidence_url") or ""),
            "first_financing_close_date_reference":str(finance.get("first_financing_date") or ""),
            "first_financing_source_reference":str(finance.get("first_financing_source") or ""),
            "second_financing_close_date_reference":str(finance.get("second_financing_date") or ""),
            "second_financing_source_reference":str(finance.get("second_financing_source") or ""),
            "financing_audit_status_reference":str(finance.get("second_financing_audit_status") or ""),
            "financing_evidence_note":str(finance.get("second_financing_evidence_note") or ""),
            "pdufa_date_reference":str(event.get("pdufa_date") or ""),
            "pdufa_status_reference":str(event.get("pdufa_confirmation") or ""),
            "pdufa_source_reference":str(event.get("pdufa_evidence_url") or ""),
            "fda_outcome_reference":str(event.get("outcome") or ""),
            "missing_historical_requirements":" | ".join(missing),
            "next_research_step":next_step,
            "eligible_for_historical_trade_backtest":"NO — RESEARCH QUEUE ONLY",
        })
    out.sort(key=lambda r:(r["priority"],r["ticker"],r["event_key"]))
    return out, {
        "existing_pdufa_event_records":len(reg),
        "existing_financing_records":len(funding),
        "historical_financing_research_priority":sum(
            r["priority"].startswith("1") for r in out),
        "historical_trade_verified_from_worklist":0,
        "caveat":"Retrospective ledger evidence is only a research clue; never convert these rows into trades without dated public disclosure and verified historical adjusted prices.",
    }
