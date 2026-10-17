"""Source adapter and native Streamlit bridge for the reference GEM dashboards.

The component owns presentation and local exploration. Existing engines own
membership, qualification, freshness and scores. No synthetic market/clinical
observations are introduced to fill the reference artwork.
"""
from __future__ import annotations

import csv
import hashlib
import math
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

from gem_membership_history import (
    read_history, empty_history, enrich_stage_rows, departed_stage_rows,
)
from gem_potential_list import build_potential_list
from gem_verified_snapshot import source_cleared_gems
from gem_stage_dossier import scan_health
from gem_runway_gate import load_snapshots, assess_runway
from gem_visual_page import _rankings, _show
from ticker_toggle_panel import _init_browser_selection, _toggle, clean_ticker


FRONTEND = Path(__file__).resolve().parent / "gem_reference_frontend"
_dashboard = components.declare_component("gem_reference_dashboard", path=str(FRONTEND))
POLICIES = {"pre", "partial", "hold"}


def _text(value, fallback="—"):
    return _show(value, fallback)


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _money(value):
    number = _number(value)
    if number is None:
        return "—"
    for size, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(number) >= size:
            return f"${number / size:,.2f}{suffix}"
    return f"${number:,.2f}"


def _pct(value, *, probability=False):
    number = _number(value)
    if probability and number is not None and 0 <= number <= 1:
        number *= 100
    return f"{number:g}%" if number is not None else "—"


def _csv(root, name):
    try:
        with (Path(root) / name).open(newline="", encoding="utf-8-sig") as stream:
            return list(csv.DictReader(stream))
    except (OSError, UnicodeError, csv.Error):
        return []


def _unique(rows, field):
    """Refuse ambiguous exact identities rather than choosing the last row."""
    result, duplicates = {}, set()
    for row in rows:
        key = str(row.get(field) or "").strip()
        if not key:
            continue
        if key in result:
            duplicates.add(key)
        result[key] = row
    return {key: row for key, row in result.items() if key not in duplicates}


def _source(label, reference, url, day, verified=False):
    return {"label": label, "reference": reference or "Source unavailable",
            "url": url or "", "date": day or "",
            "status": "Verified" if verified else "Review",
            "type": "pass" if verified else "review"}


def _fallback_checks(record, event, profile, *, junior, exit_risk=False):
    """Show observed conditions without assigning new points or a total."""
    p3 = not junior and str(record.get("Phase 3 status") or "") == "PRIMARY_MET_VERIFIED"
    if exit_risk:
        values = [
            ("Target reached", "Requires a position-specific trade plan", None),
            ("ATR trailing stop", "ATR requires saved high / low prices", None),
            ("Two closes below SMA20", "Observe current saved EOD closes", None),
            ("SMA50 breakdown", "Requires at least 50 saved closes", None),
            ("MACD crossover", "Requires at least 60 saved closes", None),
            ("RSI overbought", "Review RSI; no automatic partial sale", None),
            ("Material negative news", "Review primary clinical / SEC sources", None),
            ("PDUFA decision", _text(record.get("PDUFA timing window")), None),
            ("Volume breakdown", "Review source-backed volume and trend", None),
            ("Closing support lost", _text(profile.get("base", {}).get("status")), None),
        ]
    else:
        values = [
            ("Successful Phase 3", _text(record.get("Phase 3 status") or record.get("Evidence type")), True if p3 else None),
            ("PDUFA date confirmed", _text(record.get("PDUFA saved") or record.get("PDUFA date (saved)")), True if record.get("PDUFA verified") else None),
            ("Financing verified", "Track / verify" if junior else "Two distinct post-readout SEC closes", None if junior else True),
            ("Cash runway", "Independent cash-only SEC assessment", None),
            ("Market cap / float", "Review saved values and liquidity", None),
            ("Approval probability", "Saved estimate; not a calibrated trade score", None),
            ("Technical setup", _text(profile.get("recommendation")), None),
            ("Relative strength", "Benchmark comparison not available", None),
            ("Trade plan / reward-risk", "Define entry, stop and target", None),
            ("Catalyst / news flow", "Review dated program-specific sources", None),
        ]
    return [{"label": label, "detail": detail, "status": passed, "points": "—"}
            for label, detail, passed in values]


def _checks(factors, record, event, profile, *, junior, exit_risk=False):
    if not factors:
        return _fallback_checks(record, event, profile, junior=junior, exit_risk=exit_risk)
    return [{"label": str(label), "detail": str(reason),
             "status": None if earned is None else bool(earned > 0),
             "points": f"{'—' if earned is None else earned}/{weight}"}
            for label, weight, earned, reason in factors]


def _hierarchy(record, event, company, registry, pvalues):
    """Company → actual drug/indication → NCT. Siblings keep their own evidence."""
    ticker, selected_nct = record["Ticker"], str(record.get("NCT ID") or "")
    own = [r for r in registry if r.get("ticker") == ticker and
           ("3" in str(r.get("phase") or "") or r.get("nct_id") == selected_nct)]
    by_nct = _unique(own, "nct_id")
    # The selected exact application may not be in this registry snapshot.
    if selected_nct and selected_nct not in by_nct:
        by_nct[selected_nct] = {"nct_id": selected_nct, "drug": record.get("Drug"),
                                "indication": record.get("Indication"), "phase": "Phase 3"}
    groups = {}
    for nct, trial in by_nct.items():
        selected = nct == selected_nct
        drug = _text(record.get("Drug") if selected else trial.get("drug"))
        indication = _text(record.get("Indication") if selected else trial.get("indication"))
        group = groups.setdefault((drug, indication), {
            "drug": drug, "indication": indication, "selected": False, "trials": [],
        })
        group["selected"] = group["selected"] or selected
        statistics = [r for r in pvalues if r.get("nct_id") == nct and r.get("ticker") == ticker]
        endpoints = "; ".join(dict.fromkeys(_text(r.get("primary_endpoint"), "") for r in statistics)).strip("; ")
        pvals = "; ".join(dict.fromkeys(_text(r.get("p_value"), "") for r in statistics)).strip("; ")
        verified = selected and str(record.get("Phase 3 status") or "") == "PRIMARY_MET_VERIFIED"
        source = ((record.get("Phase 3 source") or record.get("Clinical source") or
                   event.get("trial_evidence_url")) if selected else trial.get("source_url"))
        group["trials"].append({
            "nct": nct, "phase": _text(trial.get("phase"), "Phase 3"),
            "selected": selected, "url": source or f"https://clinicaltrials.gov/study/{nct}",
            "endpoint": endpoints or "Not available in saved feed",
            "p_value": pvals or (_text(event.get("reported_p_values")) if selected else "—"),
            "readout": (record.get("Phase 3 date") or event.get("phase3_date") or "")
                       if selected else trial.get("results_posted", ""),
            "patients": None, "result": "Primary met" if verified else _text(trial.get("status"), "Review source"),
            "result_type": "pass" if verified else "unknown",
            "note": ("Successful Phase 3 is source-cleared for this exact program." if verified
                     else "A registry status alone does not establish a successful primary endpoint."),
        })
    return sorted(groups.values(), key=lambda x: (not x["selected"], x["drug"], x["indication"]))



def _criterion_facts(record, event, master, profile, funding, pvalues, ticker, clinical_url):
    """Exact-program, read-only observations for clickable research criteria.

    Numbers, flags and source links are not promoted to proof of an absence
    of risk. Unknowns are deliberately omitted, so the frontend ranks last.
    """
    facts = {}

    def observed(key, label, detail, *, metric=0, tier=1):
        metric = _number(metric)
        facts[key] = {"tier": int(tier), "metric": metric if metric is not None else 0,
                      "label": str(label)[:92], "detail": str(detail)[:450]}

    nct = str(record.get("NCT ID") or "").strip().upper()
    exact = [row for row in pvalues
             if str(row.get("nct_id") or "").strip().upper() == nct
             and str(row.get("ticker") or "").strip().upper() == ticker
             and nct.startswith("NCT") and len(nct) == 11]
    endpoints = [str(row.get("primary_endpoint") or "").strip()
                 for row in exact if str(row.get("primary_endpoint") or "").strip()]
    values = [str(row.get("p_value") or "").strip()
              for row in exact if str(row.get("p_value") or "").strip()]
    if not values and nct and str(event.get("nct_id") or "").strip().upper() == nct:
        raw = str(event.get("reported_p_values") or "").strip()
        if raw:
            values = [raw]
    if clinical_url and str(clinical_url).startswith("https://") and (endpoints or values):
        raw = values[0] if len(values) == 1 else ""
        match = re.fullmatch(r"\s*(?:p\s*)?(?:=|<|<=)?\s*(0?\.\d+|[01](?:\.0+)?)\s*", raw, re.I)
        value = _number(match.group(1)) if match else None
        if value is not None and 0 <= value <= 1:
            observed("endpoint", "Recorded p: " + raw,
                     "Exact NCT endpoint: " + ("; ".join(endpoints)[:170] or "endpoint not separately labeled") +
                     "; numeric p-value is descriptive and does not prove clinical success",
                     metric=-value, tier=2)
        else:
            observed("endpoint", "Endpoint/p-value cited",
                     "Exact-program endpoint/p-value text recorded; no unambiguous numeric primary p-value",
                     tier=1)

    status = str(event.get("conflict_flag") or "").strip().upper()
    score = _number(event.get("safety_score"))
    if status in {"YES", "TRUE", "1", "ACTIVE", "CONFLICT", "REVIEW"}:
        observed("safety", "Safety / evidence conflict flagged",
                 "Program-specific conflict flag in saved ledger: " + status,
                 metric=-1)
    elif score is not None:
        observed("safety", f"Safety score (saved): {score:g}",
                 "Saved, uncalibrated score; does not establish that serious adverse events are absent",
                 metric=score)
    elif status in {"NO", "NONE", "FALSE", "0", "PASS"}:
        observed("safety", "No conflict flag recorded",
                 "Saved flag only; not a clinical safety clearance", tier=1)

    note = str(funding.get("second_financing_evidence_note") or "")
    for key, expression, label in (
        ("warrants", r"\bwarrants?\b", "Warrants mentioned"),
        ("convertibles", r"\bconvertible(?:\s+notes?|\s+debt|\s+securities)?\b", "Convertibles mentioned"),
    ):
        if note and re.search(expression, note, flags=re.I):
            observed(key, label + " in SEC review note",
                     "Potential financing structure exposure mentioned in saved source review. Terms and current outstanding balances require direct SEC recheck.",
                     tier=1)
    dilution = str(event.get("new_dilution_flag") or "").strip().upper()
    if dilution in {"YES", "TRUE", "1", "ACTIVE", "UNRESOLVED"}:
        observed("dilution", "Dilution risk flagged", "Explicit dilution flag: " + dilution,
                 tier=1, metric=-1)
    elif dilution in {"NO", "NONE", "FALSE", "0"}:
        observed("dilution", "No new dilution flag (saved)",
                 "A saved negative flag does not certify the current capitalization table",
                 tier=1, metric=0)

    for key, column, direction, description in (
        ("short", "short_interest", -1, "Saved short-interest figure; lower numeric values first, unit/feed review required"),
        ("float", "shares_float", 1, "Saved public float; larger float first, not an automatic liquidity pass"),
        ("institutional", "institutional_ownership_pct", 1, "Saved institutional ownership percentage, not a current filing reconciliation"),
        ("clinical_quality", "science_score", 1, "Saved uncalibrated science score, not a source-verified trial success rating"),
        ("cmc", "cmc_score", 1, "Saved uncalibrated CMC score, not FDA manufacturing clearance"),
        ("poa", "approval_probability", 1, "Saved approval estimate is not a calibrated or assured probability"),
    ):
        val = _number(event.get(column))
        if val is not None and val >= 0:
            observed(key, f"Saved figure: {val:g}", description, metric=direction*val, tier=1)

    master = master or {}
    insider_source = str(master.get("Insider Source Links") or "")
    for key, column in (("insider_buy", "Insider Purchases"),
                        ("insider_sell", "Insider Sales")):
        raw = str(master.get(column) or "").strip()
        if raw and raw.upper() not in {"—", "-", "N/A", "NONE", "UNKNOWN", "UNVERIFIED"}:
            val = _number(raw)
            observed(key, "Saved insider activity: " + raw[:55],
                     "Source link recorded" if insider_source.startswith("https://") else
                     "Saved issuer-level claim; individual Form 4 evidence unavailable here",
                     metric=(val if key == "insider_buy" else -val) if val is not None else 0,
                     tier=2 if insider_source.startswith("https://") else 1)

    hedge = _number(master.get("Hedge-fund accumulation /10"))
    hedge_status = str(master.get("Hedge-fund Signal") or "")
    hedge_source = str(master.get("Hedge-fund Source Links") or "")
    if hedge is not None and hedge_status == "SOURCE-VERIFIED QUARTERLY 13F HOLDINGS" and hedge_source.startswith("https://"):
        observed("hedge", f"13F signal: {hedge:g}/10",
                 "Source-linked quarterly 13F holdings; not evidence of current intraday buying",
                 metric=hedge, tier=2)

    base = profile.get("base") or {}
    base_status = str(base.get("status") or "")
    if profile.get("fresh") and base_status and not base_status.upper().startswith(("STALE", "NOT AVAILABLE", "UNKNOWN")):
        touches = _number(base.get("touches"))
        observed("base", "Daily-close base: " + base_status[:65],
                 "Source-saved closing-price approximation, not an intraday accumulation confirmation",
                 metric=touches or 0, tier=1)
        breakout = _number(base.get("breakout_rvol"))
        if breakout is not None:
            observed("breakout", f"Observed breakout RVOL: {breakout:g}×",
                     "Saved daily-close breakout-volume observation; external candlesticks require independent review",
                     metric=breakout, tier=1)

    regulatory_score = _number(event.get("regulatory_score"))
    outcome = str(event.get("outcome") or "").strip().upper()
    regulatory_note = str(event.get("regulatory_summary") or "").strip()
    if outcome in {"APPROVED", "CRL", "REJECTED", "WITHDRAWN", "REFUSED"}:
        observed("regulatory", "Resolved: " + outcome,
                 "Historical FDA outcome, not an open pre-PDUFA opportunity",
                 metric=-1, tier=1)
    elif regulatory_score is not None:
        observed("regulatory", f"Saved regulatory score: {regulatory_score:g}",
                 "Saved uncalibrated regulatory score; does not confirm FDA clearance",
                 metric=regulatory_score, tier=1)
    elif regulatory_note and regulatory_note.upper() not in {"UNVERIFIED", "UNKNOWN", "N/A"}:
        observed("regulatory", "Saved regulatory review note",
                 "Saved narrative only; no validated numerical regulatory ranking", tier=1)
    return facts


def _candidate(stage, ranked, root, today, companies, financings, runway, registry, pvalues):
    record, event, master, profile, score = ranked
    junior = stage == "GEM JR"
    ticker = clean_ticker(record.get("Ticker"))
    identifier = str(record.get("Pipeline ID") or record.get("Exact program") or "")
    company = _text(event.get("company") or companies.get(ticker, {}).get("company"), ticker)
    funding = financings.get(str(record.get("Exact program") or ""), {})
    first = record.get("First close") or funding.get("first_financing_date") or ""
    second = record.get("Second close") or funding.get("second_financing_date") or ""
    first_url = record.get("First SEC source") or funding.get("first_financing_source") or ""
    second_url = record.get("Second SEC source") or funding.get("second_financing_source") or ""
    clinical_url = record.get("Phase 3 source") or record.get("Clinical source") or event.get("trial_evidence_url") or ""
    p3_date = record.get("Phase 3 date") or event.get("phase3_date") or ""
    pdufa = record.get("PDUFA saved") or record.get("PDUFA date (saved)") or event.get("pdufa_date") or ""
    pdufa_url = event.get("pdufa_evidence_url") or ""
    pdufa_verified = bool(record.get("PDUFA verified") or (
        str(event.get("pdufa_confirmation") or "").startswith("VERIFIED") and pdufa_url))
    runway_result = assess_runway(ticker, runway.get(ticker), as_of=today.isoformat(),
                                 second_close=second or None)
    runway_months = runway_result["Cash runway (months)"]
    entry, risk = score.get("entry"), score.get("exit_risk")
    status = "Research" if junior else "Qualified · Hold"
    status_type = "review" if junior else "pass"
    trade_status = _text(record.get("Trade status") or record.get("Still needed"))
    if "NO NEW ENTRY" in trade_status:
        status, status_type = "Entry hold", "hold"
    financings_display = [{"date": d, "url": u, "amount": "—", "price": "—", "warrants": "—",
                           "status": "Confirmed" if not junior and d and u else "Review",
                           "type": "pass" if not junior and d and u else "review"}
                          for d, u in ((first, first_url), (second, second_url))]
    sources = [
        _source("Phase 3 results", "Primary clinical evidence", clinical_url, p3_date,
                not junior and bool(clinical_url)),
        _source("Financing #1", "SEC closing evidence", first_url, first, not junior and bool(first_url)),
        _source("Financing #2", "SEC closing evidence", second_url, second, not junior and bool(second_url)),
        _source("PDUFA target", "Primary regulatory source", pdufa_url, pdufa, pdufa_verified),
        _source("Cash runway", "SEC Companyfacts", runway_result.get("Cash runway source"),
                runway_result.get("Cash runway as of"), runway_months is not None),
    ]
    alerts = [{"date": s["date"], "ticker": ticker, "type": s["label"],
               "detail": s["reference"], "url": s["url"]} for s in sources if s["date"] and s["url"]]
    gaps = str(record.get("Still needed") or "").strip()
    if gaps:
        alerts.insert(0, {"date": record.get("Source review as of") or record.get("Source review date") or "",
                          "ticker": ticker, "type": "Review", "detail": gaps, "url": ""})
    snapshot = runway.get(ticker) or {}
    cash = snapshot.get("cash_usd") if runway_months is not None else event.get("cash")
    info = [
        ("Ticker", ticker), ("Company", company), ("Indication", _text(record.get("Indication"))),
        ("Phase", "Phase 3 · " + _text(record.get("Phase 3 status") or record.get("Evidence type"))),
        ("P3 Readout", p3_date or "—"), ("PDUFA", pdufa or "—"),
    ]
    if junior:
        info.append(("Financing Status", _text(record.get("SEC documents rechecked"), "Review source")))
    else:
        info.extend([("Financing #1", first or "—"), ("Financing #2", second or "—")])
    info.extend([
        ("Cash Runway", f"{runway_months:g} months" if runway_months is not None else "Unverified"),
        ("Market Cap (saved)", _money(event.get("market_cap"))),
        ("PoA (saved estimate)", _pct(event.get("approval_probability"), probability=True)),
        ("Short Interest (saved)", _pct(event.get("short_interest"))),
        ("Entry Score", f"{entry}/100" if entry is not None else "N/A"),
        ("Exit Risk", f"{risk}/100" if risk is not None else "N/A"),
    ])
    return {
        "id": identifier, "ticker": ticker, "company": company,
        "drug": _text(record.get("Drug")), "indication": _text(record.get("Indication")),
        "nct": _text(record.get("NCT ID")), "readout": p3_date, "pdufa": pdufa,
        "pdufa_verified": pdufa_verified, "runway": runway_months,
        "runway_reason": runway_result["Cash runway reason"], "cash": _money(cash),
        "market_cap": _number(event.get("market_cap")),
        "market_cap_display": _money(event.get("market_cap")),
        "poa_display": _pct(event.get("approval_probability"), probability=True),
        "short_display": _pct(event.get("short_interest")),
        "entry": entry, "exit_risk": risk, "quality": score.get("quality"),
        "criteria_facts": _criterion_facts(record, event, master, profile, funding,
                                          pvalues, ticker, clinical_url),
        "entry_status": score.get("entry_status", "Unverified"),
        "exit_status": score.get("exit_status", "Unverified"),
        "entry_coverage": score.get("entry_coverage", 0), "exit_coverage": score.get("exit_coverage", 0),
        "status": status, "status_type": status_type, "trade_status": trade_status,
        "financing_label": "Track / verify" if junior else "Two SEC closes",
        "financing_detail": _text(record.get("Still needed"), "Independent source recheck required before trading"),
        "source_review": record.get("Source review as of") or record.get("Source review date") or "",
        "financings": financings_display, "sources": sources, "profile": info,
        "entry_checks": _checks(score.get("entry_factors"), record, event, profile, junior=junior),
        "exit_checks": _checks(score.get("exit_factors"), record, event, profile, junior=junior, exit_risk=True),
        "hierarchy": _hierarchy(record, event, company, registry, pvalues), "alerts": alerts,
        "bars": [{"date": b["date"].isoformat(), "close": b["close"], "volume": b["volume"]}
                 for b in profile.get("bars", [])],
        "market_date": profile["date"].isoformat() if profile.get("date") else "",
        "fresh": bool(profile.get("fresh")), "close": profile.get("close"),
        "sma20": profile.get("sma20"), "sma50": profile.get("sma50"),
        "rsi": profile.get("rsi"), "rvol": profile.get("rvol"),
        "dollar_volume": profile.get("dollar_volume"),
        "macd": ("Bullish" if profile["macd"]["bullish"] else "Bearish") if profile.get("macd") else "—",
        "support": profile.get("base", {}).get("support"),
        "resistance": profile.get("base", {}).get("resistance"),
        "base_status": _text(profile.get("base", {}).get("status")),
    }


def build_dashboard(stage, root="data", *, as_of=None):
    if stage not in {"GEM JR", "GEM"}:
        raise ValueError("Unknown GEM stage")
    today = as_of or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    if not isinstance(today, date):
        raise TypeError("as_of must be a date")
    try:
        history = read_history(root)
    except (OSError, ValueError, TypeError):
        history = empty_history()
    qualified, historical, current = source_cleared_gems(root, as_of=today)
    if stage == "GEM JR":
        active, held = build_potential_list(root, as_of=today)
        excluded = {str(x.get("Pipeline ID") or "") for x in qualified + historical}
        active = [r for r in active if str(r.get("Pipeline ID") or "") not in excluded]
    else:
        active, held = qualified, historical
    active = enrich_stage_rows(active, "GEM_JR" if stage == "GEM JR" else "GEM", history)
    # A duplicated program cannot become an ambiguous button target.
    active_by_id = _unique(active, "Pipeline ID")
    active = [r for r in active if active_by_id.get(str(r.get("Pipeline ID") or "")) is r]
    companies = _unique(_csv(root, "company_registry.csv"), "ticker")
    finance = _unique(_csv(root, "second_financing_status.csv"), "event_key")
    runway = load_snapshots(root)
    registry = _csv(root, "all_phase_trials.csv")
    pvalues = _csv(root, "phase3_primary_pvalues.csv")
    candidates = [_candidate(stage, r, root, today, companies, finance, runway, registry, pvalues)
                  for r in _rankings(stage, active, root, today)]
    departed = departed_stage_rows(history, "GEM_JR" if stage == "GEM JR" else "GEM")
    histories = [{"date": r.get("Date Left") or "", "ticker": r.get("Ticker") or "",
                  "drug": r.get("Drug") or "", "reason": r.get("Leave Reason") or ""}
                 for r in departed]
    scans = []
    for s in scan_health(root):
        status = str(s["Published status"])
        # Match explicit published status only; PARTIAL_COMPLETE is not COMPLETE.
        kind = "pass" if status.upper() in {"COMPLETE", "COMPLETED", "SUCCEEDED", "SUCCESS"} else "review"
        scans.append({"label": s["Scan"], "date": s["Saved update"], "status": status, "type": kind})
    return {
        "stage": stage, "junior": stage == "GEM JR", "candidates": candidates,
        "history": histories, "held_count": len(held), "source_current": bool(current),
        "alerts": [a for c in candidates for a in c["alerts"]][:12], "scans": scans,
        "scan_note": "Published collector status; verify source freshness before entry.",
        "rules": [
            "Successful Phase 3 for the exact drug + indication, with primary-source results.",
            "Two distinct post-readout financing closures.",
            "Both financing closures independently confirmed through SEC evidence.",
            "Review cash-only runway and the date of the latest SEC assessment.",
            "Evaluate saved approval estimates, valuation and market liquidity separately.",
            "Resolve safety, dilution and regulatory gaps before a trading decision.",
        ],
        "empty_checks": {
            "entry": _fallback_checks({}, {}, {}, junior=stage == "GEM JR"),
            "exit": _fallback_checks({}, {}, {}, junior=stage == "GEM JR", exit_risk=True),
        },
    }


def resolve_dashboard_action(event, payload):
    """Validate component messages against the canonical current candidate IDs."""
    if not isinstance(event, dict) or not isinstance(event.get("nonce"), str):
        return None
    if not 1 <= len(event["nonce"]) <= 200:
        return None
    action = event.get("action")
    if action in {"watch", "trade"}:
        matches = [r for r in payload["candidates"] if r["id"] == event.get("id")]
        if len(matches) != 1:
            return None
        return {"action": action, "ticker": matches[0]["ticker"]}
    if action == "navigate" and event.get("tab") in {"PIPELINE", "GEM JR", "GEM", "SCANS", "WT"}:
        return {"action": action, "tab": event["tab"]}
    if action == "policy" and event.get("policy") in POLICIES:
        return {"action": action, "policy": event["policy"]}
    if action == "refresh":
        return {"action": action}
    return None


def render_reference_stage(stage, root="data"):
    # Loaded only inside an open GEM tab. Removing this tab also removes the
    # stylesheet, so the other PDUFA workspaces retain their existing theme.
    st.markdown("""<style>
      /* GEM content styling stays local; global navigation is styled by app.py. */
      .stApp{background:#e1fae9!important}
      header[data-testid="stHeader"]{display:none!important}
      .stApp .block-container{max-width:none!important;padding:0 0 12px!important}
      .stApp [data-testid="stVerticalBlock"]{gap:0.12rem!important}
      .stApp [data-testid="stCustomComponentV1"]{width:100%!important}
      .stApp [data-testid="stCustomComponentV1"] iframe{display:block;border:0}
    </style>""", unsafe_allow_html=True)
    _init_browser_selection("gem_reference_" + stage.replace(" ", "_"))
    payload = build_dashboard(stage, root)
    payload["watch"] = list(st.session_state.get("watchlist", []))
    payload["trade"] = list(st.session_state.get("trading_tickers", []))
    payload["notice"] = st.session_state.pop("_gem_reference_notice", "")
    revision = hashlib.sha256(b"".join(
        (FRONTEND / name).read_bytes()
        for name in ("index.html", "dashboard.css", "dashboard.js")
    )).hexdigest()[:12]
    raw = _dashboard(payload=payload, default=None,
                     key="reference_dashboard_" + stage.replace(" ", "_") + "_" + revision)
    event = resolve_dashboard_action(raw, payload)
    last_key = "_gem_reference_event_" + stage
    if event is None or raw["nonce"] == st.session_state.get(last_key):
        return
    st.session_state[last_key] = raw["nonce"]
    if event["action"] == "watch":
        _toggle(event["ticker"], "watch")
    elif event["action"] in {"trade", "navigate"}:
        # Tabs are already instantiated. Apply navigation BEFORE widgets on
        # the next run, using the existing trade-workspace callback.
        st.session_state["_gem_dashboard_action"] = event
    elif event["action"] == "policy":
        st.session_state["gem_pdufa_exit_policy"] = event["policy"]
        return
    elif event["action"] == "refresh":
        st.session_state["_gem_reference_notice"] = (
            "Saved source records reloaded. Start live collectors from SCANS."
        )
    st.rerun()
