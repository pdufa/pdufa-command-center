"""Stage 1 of the unified post-Phase-3 trading workflow.

Source-preserving discovery and conservative qualification. Research leads,
registry results and issuer readouts are never treated as successful Phase 3.
An event-key financing join cannot be replaced by a ticker-only join.
GREEN is an attested research gate, not an executed trade or a buy order.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from step7_entry import GATES, safe_source
from post_phase3_priority import WEIGHTS, score_candidate, assign_priority_ranks
from post_phase3_review_priority import REVIEW_COMPONENTS, review_priority, assign_review_ranks

PACIFIC = ZoneInfo("America/Los_Angeles")
NCT = re.compile(r"^NCT\d{8}$")
TICKER = re.compile(r"^[A-Z0-9.-]{1,15}$")
RESOLVED = {"APPROVED", "CRL", "REJECTED", "WITHDRAWN", "REFUSED"}
COLUMNS = (
    "Research rank", "Ticker", "Research priority /100", "Entry qualification",
    "Evidence rank", "Evidence score /100", "Drug", "Indication", "NCT ID",
    "Research priority status", "Research priority limitations",
    "Rating status", "Rating coverage", *REVIEW_COMPONENTS,
    *WEIGHTS.keys(), "Rating limitations", "Source lane",
    "Exact event", "Phase 3 evidence", "Financing #2", "Financing cycle (separate)",
    "PDUFA verification", "Days to PDUFA", "PDUFA date",
    "Planned exit (-7 days)", "Next action", "Blockers",
    "Registry source", "Phase 3 source", "Financing source",
    "PDUFA source", "As of Pacific",
)


def clean(value):
    return str(value or "").strip()


def parsed_date(value):
    try:
        return date.fromisoformat(clean(value)[:10])
    except ValueError:
        return None


def https_source(value):
    try:
        u = urlparse(clean(value))
        return (u.scheme == "https" and bool(u.hostname)
                and not u.username and not u.password)
    except ValueError:
        return False


def read_rows(path):
    try:
        with Path(path).open(newline="", encoding="utf-8-sig") as f:
            return [dict(row) for row in csv.DictReader(f)]
    except (OSError, UnicodeError, csv.Error):
        return []


def source_day(root):
    try:
        value = json.loads((Path(root) / "step7_live_status.json").read_text(encoding="utf-8"))
        stamp = datetime.fromisoformat(clean(value.get("generated_at_utc")).replace("Z", "+00:00"))
        return stamp.astimezone(PACIFIC).date() if stamp.tzinfo else None
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def _blank(lane, ticker, drug, indication, nct, today):
    return {
        "Source lane": lane, "Ticker": ticker, "Drug": drug,
        "Indication": indication, "NCT ID": nct,
        "Exact event": "", "Phase 3 evidence": "REVIEW — RESULT NOT ADJUDICATED",
        "Financing #2": "REVIEW — EXACT EVENT NOT VERIFIED",
        "Financing cycle (separate)": "REVIEW — FINANCING UNVERIFIED",
        "Entry qualification": "REVIEW — RESEARCH LEAD",
        "Research rank": None, "Research priority /100": 0,
        "Research priority status": "RESEARCH TRIAGE ONLY — NOT TRADE READY",
        "Research priority limitations": "Unmatched program; prioritize document collection",
        **dict.fromkeys(REVIEW_COMPONENTS, 0),
        "Evidence rank": None, "Evidence score /100": None,
        "Rating status": "NOT RATED — UNMATCHED RESEARCH LEAD",
        "Rating coverage": "0/6 — research lead",
        "Rating limitations": "Exact program and qualifying evidence must be reviewed",
        **dict.fromkeys(WEIGHTS, 0),
        "PDUFA verification": "REVIEW — SOURCE MISSING",
        "Days to PDUFA": None, "PDUFA date": "",
        "Planned exit (-7 days)": "", "Next action": "Verify exact Phase 3 result and issuer",
        "Blockers": "No exact-event clinical/financing gate review",
        "Registry source": "", "Phase 3 source": "", "Financing source": "",
        "PDUFA source": "", "As of Pacific": today.isoformat(),
    }


def build_queue(root, as_of=None):
    """Return source-dated rows and status without network calls.

    Research intake may be widened by adding independently sourced leads to
    post_phase3_discoveries.csv. They NEVER bypass exact-event gate review.
    """
    root = Path(root)
    today = (as_of.astimezone(PACIFIC).date() if isinstance(as_of, datetime)
             and as_of.tzinfo else as_of if isinstance(as_of, date)
             and not isinstance(as_of, datetime) else datetime.now(PACIFIC).date())
    current_feed = source_day(root) == today
    regulatory_rows = read_rows(root / "pdufa_candidates.csv")
    financing_rows = read_rows(root / "step7_financing_review.csv")
    trials = read_rows(root / "step7_pre_phase3_feed.csv")
    external = read_rows(root / "post_phase3_discoveries.csv")
    market_rows = read_rows(root / "step7_market_status.csv")
    market_by_ticker = {}
    duplicate_market = set()
    for record in market_rows:
        price_ticker = clean(record.get("ticker")).upper()
        if price_ticker in market_by_ticker:
            duplicate_market.add(price_ticker)
        elif price_ticker:
            market_by_ticker[price_ticker] = record
    for price_ticker in duplicate_market:
        market_by_ticker.pop(price_ticker, None)
    finance_stages = {}
    stage_duplicates = set()
    for fin in read_rows(root / "second_financing_status.csv"):
        key = clean(fin.get("event_key"))
        if key in finance_stages:
            stage_duplicates.add(key)
        elif key:
            finance_stages[key] = fin
    for key in stage_duplicates:
        finance_stages.pop(key, None)

    regulatory = {}
    ambiguous = set()
    for row in regulatory_rows:
        key = clean(row.get("event_key"))
        if not key:
            continue
        if key in regulatory:
            ambiguous.add(key)
        regulatory[key] = row
    for key in ambiguous:
        regulatory.pop(key, None)

    financing = {}
    funding_conflicts = set()
    for row in financing_rows:
        key = clean(row.get("Exact financing event"))
        if not key:
            continue
        if key in financing:
            funding_conflicts.add(key)
        financing[key] = row
    for key in funding_conflicts:
        financing.pop(key, None)

    rows = []
    mapped = set()
    for key, event in regulatory.items():
        funding = financing.get(key, {})
        if not funding and not (
            clean(event.get("phase3_date")) or
            clean(event.get("phase3_status")).upper() in
            {"VERIFIED_SUCCESS", "PRIMARY_MET_VERIFIED", "RESULTS_REVIEW", "RESULTS_VERIFIED"}
        ):
            continue
        ticker = clean(event.get("ticker")).upper()
        nct = clean(event.get("nct_id")).upper()
        if not TICKER.fullmatch(ticker):
            continue
        drug = clean(event.get("drug"))
        indication = clean(event.get("indication"))
        pdufa = parsed_date(event.get("pdufa_date"))
        days = (pdufa - today).days if pdufa else None
        exit_date = (pdufa - timedelta(days=7)) if pdufa else None
        outcome = clean(event.get("outcome")).upper()
        excluded = (outcome in RESOLVED or
                    clean(event.get("check_status")).upper().startswith("RESOLVED_") or
                    clean(event.get("monitor_eligibility")).upper() == "EXCLUDED" or
                    (pdufa is not None and days < 0))
        verified_date = (clean(event.get("pdufa_confirmation")).upper().startswith("VERIFIED")
                         and https_source(event.get("pdufa_evidence_url")))
        conflict = clean(event.get("conflict_flag")).upper() not in {"", "NO", "NONE", "FALSE", "0", "PASS"}
        clinical = (clean(event.get("phase3_status")).upper()
                    in {"VERIFIED_SUCCESS", "PRIMARY_MET_VERIFIED"}
                    and https_source(event.get("trial_evidence_url"))
                    and parsed_date(event.get("phase3_date")) is not None)
        gate = clean(funding.get("Current gate"))
        details = clean(funding.get("Audited gate details"))
        scan = clean(funding.get("Source scan")).upper()
        attested_ready = (
            gate.startswith("ENTRY READY") and
            clean(funding.get("Proposed trade status")).startswith("ENTRY READY") and
            all(f"{gate_name}: PASS" in details for gate_name in GATES) and
            clean(funding.get("Recheck freshness")) == "RECENT" and
            scan not in {"", "NOT_CHECKED", "SOURCE_UNAVAILABLE", "NO_SOURCE"} and
            not any(term in scan for term in ("BLOCKED", "ERROR", "PARTIAL")) and
            clean(funding.get("Historical second closing")).startswith("DOCUMENTED") and
            safe_source(funding.get("Second source"), sec=True)
        )
        fin_stage = finance_stages.get(key, {})
        stage_name = clean(fin_stage.get("second_financing_status")).upper()
        fin_review_date = parsed_date(fin_stage.get("verified_as_of"))
        stage_fresh = bool(fin_review_date and 0 <= (today - fin_review_date).days <= 7)
        if (stage_name in {"CLOSED", "FINISHED"} and
                clean(fin_stage.get("second_financing_audit_status")) == "VERIFIED_SECOND_POST_PHASE3_FINANCING" and
                clean(fin_stage.get("second_financing_closed")).upper() == "YES" and
                https_source(fin_stage.get("second_financing_source"))):
            financing_cycle = "RED — FINANCING CLOSED (HISTORICAL)"
        elif stage_fresh and stage_name in {"RUNNING", "IN_PROGRESS"}:
            financing_cycle = "YELLOW — FINANCING RUNNING (AS OF REVIEW)"
        elif stage_fresh and stage_name in {"STARTED", "LAUNCHED"}:
            financing_cycle = "GREEN — FINANCING STARTED (AS OF REVIEW)"
        else:
            financing_cycle = "REVIEW — FINANCING UNVERIFIED"
        green = (current_feed and funding and attested_ready and verified_date and
                 clinical and not conflict and pdufa is not None and days > 7)
        if excluded:
            status, action = "EXCLUDED — FDA DECIDED / DATE PASSED", "Historical only; do not open a position"
        elif pdufa is not None and days <= 7:
            status, action = "RED WINDOW — NO NEW ENTRY", "Scheduled exit window; do not initiate a new trade"
        elif not current_feed:
            status, action = "REVIEW — SOURCE SNAPSHOT STALE", "Refresh saved source feed and financing checks"
        elif green:
            status, action = "GREEN — GATES ATTESTED", "Review evidence and execution plan before any trade"
        else:
            status = "REVIEW — ENTRY BLOCKED"
            if not funding:
                action = "Verify financing sequence for exact clinical program"
            elif not verified_date:
                action = "Verify PDUFA date against dated primary source"
            elif not clinical:
                action = "Review successful Phase 3 primary endpoint, benefit and safety"
            elif conflict:
                action = "Resolve conflicting clinical/regulatory evidence"
            else:
                action = "Clear missing clinical, financing, dilution and market gates"
        item = _blank("SAVED REGULATORY PIPELINE", ticker, drug, indication, nct, today)
        item.update({
            "Exact event": key,
            "Phase 3 evidence": ("VERIFIED SUCCESS — SOURCE LINKED" if clinical
                                 else "REVIEW — RESULT NOT ADJUDICATED"),
            "Financing #2": clean(funding.get("Historical second closing")) or "REVIEW — NOT DOCUMENTED",
            "Financing cycle (separate)": financing_cycle,
            "Entry qualification": status,
            "PDUFA verification": ("VERIFIED — SOURCE LINKED" if verified_date else "REVIEW — NOT VERIFIED"),
            "Days to PDUFA": days, "PDUFA date": pdufa.isoformat() if pdufa else "",
            "Planned exit (-7 days)": exit_date.isoformat() if exit_date else "",
            "Next action": action,
            "Blockers": clean(funding.get("Gate reasons")) or (
                "No exact-event financing review available" if not funding else clean(funding.get("Why blocked"))),
            "Registry source": "https://clinicaltrials.gov/study/" + nct if NCT.fullmatch(nct) else "",
            "Phase 3 source": clean(event.get("trial_evidence_url")),
            "Financing source": clean(funding.get("Second source")),
            "PDUFA source": clean(event.get("pdufa_evidence_url")),
        })
        item.update(score_candidate(event, funding, market_by_ticker.get(ticker), today,
                                    snapshot_current=current_feed))
        rows.append(item)
        if NCT.fullmatch(nct):
            mapped.add((ticker, nct, drug.casefold(), indication.casefold()))

    leads_seen = set()
    for trial in trials:
        if "3" not in clean(trial.get("Trial phase")):
            continue
        category = clean(trial.get("Research category")).upper()
        if not ("RESULT POSTED" in category or "ISSUER READOUT ANNOUNCED" in category):
            continue
        ticker = clean(trial.get("Ticker")).upper()
        nct = clean(trial.get("NCT ID")).upper()
        drug = clean(trial.get("Drug"))
        indication = clean(trial.get("Indication"))
        identity = (ticker, nct, drug.casefold(), indication.casefold())
        if not TICKER.fullmatch(ticker) or not NCT.fullmatch(nct) or identity in mapped or identity in leads_seen:
            continue
        leads_seen.add(identity)
        item = _blank("SAVED TRIAL PIPELINE", ticker, drug, indication, nct, today)
        issuer = "ISSUER READOUT ANNOUNCED" in category
        item.update({
            "Phase 3 evidence": ("ISSUER ANNOUNCEMENT — SUCCESS UNVERIFIED" if issuer
                                 else "REGISTRY RESULTS POSTED — REVIEW"),
            "Registry source": clean(trial.get("NCT source")) or "https://clinicaltrials.gov/study/" + nct,
            "Phase 3 source": clean(trial.get("Issuer readout source")) if issuer else clean(trial.get("Registry primary result source")),
            "Next action": "Review issuer primary readout and program-specific financing" if issuer
                           else "Review registry endpoints and find issuer readout",
        })
        rows.append(item)

    for lead in external:
        ticker = clean(lead.get("ticker")).upper()
        nct = clean(lead.get("nct_id")).upper()
        drug = clean(lead.get("drug"))
        indication = clean(lead.get("indication"))
        reported = parsed_date(lead.get("readout_date"))
        source = clean(lead.get("source_url"))
        if not (TICKER.fullmatch(ticker) and NCT.fullmatch(nct)
                and drug and indication and reported and reported <= today and https_source(source)):
            continue
        item = _blank("INDEPENDENT RESEARCH — SOURCE LINKED", ticker, drug, indication, nct, today)
        item.update({
            "Phase 3 evidence": "POTENTIAL ISSUER READOUT — REVIEW REQUIRED",
            "Phase 3 source": source,
            "Registry source": "https://clinicaltrials.gov/study/" + nct,
            "Next action": "Review actual Phase 3 results and map to an exact financing event",
        })
        rows.append(item)

    # Research queue ranks can exist WITHOUT any certified clinical/financing
    # success. All exact-event funding links remain source-conservative.
    for row in rows:
        event_key = clean(row.get("Exact event"))
        item_event = regulatory.get(event_key) if event_key else None
        item_funding = financing.get(event_key) if event_key else None
        item_market = market_by_ticker.get(clean(row.get("Ticker")).upper())
        row.update(review_priority(row, item_event, item_funding, item_market,
                                   today, snapshot_current=current_feed))
    assign_review_ranks(rows)
    assign_priority_ranks(rows)
    # No ticker-only financing upgrade: each program keeps its own exact event identity.
    rank = {"GREEN — GATES ATTESTED": 0, "REVIEW — ENTRY BLOCKED": 1,
            "REVIEW — SOURCE SNAPSHOT STALE": 2, "REVIEW — RESEARCH LEAD": 3,
            "RED WINDOW — NO NEW ENTRY": 4, "EXCLUDED — FDA DECIDED / DATE PASSED": 5}
    rows.sort(key=lambda r: (rank.get(r["Entry qualification"], 3),
                             -r["Research priority /100"],
                             -(r["Evidence score /100"] if r["Evidence score /100"] is not None else -1),
                             r["Days to PDUFA"] if r["Days to PDUFA"] is not None else 99999,
                             r["Ticker"], r["NCT ID"], r["Exact event"]))
    return rows, {
        "as_of": today.isoformat(), "feed_current": current_feed,
        "financing_events": len(financing_rows), "saved_trial_rows": len(trials),
        "independent_research_rows": len(external),
        "green_count": sum(r["Entry qualification"].startswith("GREEN") for r in rows),
        "review_count": sum(r["Entry qualification"].startswith("REVIEW") for r in rows),
        "research_leads": sum(r["Source lane"] != "SAVED REGULATORY PIPELINE" for r in rows),
        "count": len(rows),
        "research_ranked": sum(row["Research rank"] is not None for row in rows),
        "strict_evidence_rated": sum(row["Evidence score /100"] is not None for row in rows),
    }
