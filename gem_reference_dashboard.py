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
from gem_stage_dossier import scan_diagnostics
from gem_runway_gate import load_snapshots, assess_runway
from financing_tranche_runway import load_tranches, assess_tranche_runway
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
            ("Financing #2 (OPTIONAL)", "Review SEC-funded transactions; not a GEM admission gate", None),
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



def _all_company_trials(root, *, gem, junior):
    """All *saved, ticker-linked* trial IDs, with CURRENT stage associations.

    The ClinicalTrials.gov inventory is preferred. Other sources contribute
    only exact NCT observations; they never prove sponsorship or phase on their
    own. Neither ticker-only nor drug-name-only joins confer GEM status.
    """
    inventory = _csv(root, "all_phase_trials.csv")
    pipeline = _csv(root, "phase_pipeline.csv")
    events = _csv(root, "pdufa_candidates.csv")
    rows = {}
    stage_flags = {}

    def ncts(value):
        return list(dict.fromkeys(re.findall(r"NCT\d{8}", str(value or "").upper())))

    def staged(candidates, label):
        for record in candidates:
            ticker = clean_ticker(record.get("Ticker"))
            for nct in ncts(record.get("NCT ID")):
                if ticker:
                    stage_flags.setdefault((ticker, nct), set()).add(label)

    staged(junior, "GEM JR")
    staged(gem, "GEM")

    def add(source, kind):
        ticker = clean_ticker(source.get("ticker") or source.get("Ticker"))
        if not ticker:
            return
        for nct in ncts(source.get("nct_id") or source.get("NCT ID")):
            key = (ticker, nct)
            item = rows.setdefault(key, {
                "nct": nct, "drug": "", "indication": "", "phase": "",
                "source": "", "source_type": "", "stage_labels": [],
            })
            drug = str(source.get("drug") or source.get("Drug") or "").strip()
            indication = str(source.get("indication") or source.get("Indication") or "").strip()
            # Trial registry and pipeline phase values outrank event-derived
            # phase hints; do not substitute a Phase 3 label for unknowns.
            raw_phase = str(source.get("phase") or source.get("phases")
                            or source.get("registered_phase") or "").strip()
            if raw_phase and (not item["phase"] or kind == "registry"):
                item["phase"] = raw_phase[:85]
            if drug and (not item["drug"] or kind == "registry"):
                item["drug"] = drug[:180]
            if indication and (not item["indication"] or kind == "registry"):
                item["indication"] = indication[:180]
            source_url = str(source.get("source_url") or source.get("trial_evidence_url")
                             or source.get("Clinical source") or "").strip()
            if source_url.startswith("https://") and (not item["source"] or kind == "registry"):
                item["source"] = source_url
            if kind == "registry" or not item["source_type"]:
                item["source_type"] = kind

    for row in events:
        add(row, "saved program")
    for row in pipeline:
        add(row, "pipeline")
    for row in inventory:
        add(row, "registry")
    # Independent exact-trial Phase 3 readout leads, where they exist.
    for row in _csv(root, "post_phase3_discoveries.csv"):
        add(row, "saved discovery")

    # Current GEM/GEM JR records might not yet be present in a registry export.
    for row in list(junior) + list(gem):
        add(row, "stage association")

    for (ticker, nct), flags in stage_flags.items():
        if (ticker, nct) not in rows:
            rows[(ticker, nct)] = {
                "nct": nct, "drug": "", "indication": "", "phase": "",
                "source": "", "source_type": "stage association", "stage_labels": [],
            }
        rows[(ticker, nct)]["stage_labels"] = [
            label for label in ("GEM JR", "GEM") if label in flags
        ]

    by_ticker = {}
    for (ticker, nct), row in rows.items():
        row["url"] = "https://clinicaltrials.gov/study/" + nct
        row["phase"] = row["phase"] or "Not verified in saved sources"
        row["drug"] = row["drug"] or "Drug not recorded"
        row["indication"] = row["indication"] or "Indication not recorded"
        row["selected_source"] = row["source"] or ""
        by_ticker.setdefault(ticker, []).append(row)

    for trials in by_ticker.values():
        trials.sort(key=lambda item: (
            0 if "GEM" in item["stage_labels"] else 1 if "GEM JR" in item["stage_labels"] else 2,
            item["drug"].casefold(), item["nct"],
        ))
    complete_inventory = bool(inventory)
    coverage = (
        "Saved trial registry inventory plus program references; trial-to-issuer association follows saved ticker mappings."
        if complete_inventory else
        "PARTIAL: the complete trial inventory is not available. Only source-saved ticker-linked NCT records are shown; this is not every trial run by the company."
    )
    return by_ticker, coverage


def _hierarchy(record, event, company, registry, pvalues, company_trials=None):
    """Company -> drug/indication -> exact NCT, including all saved phases.

    Membership is an exact ticker+NCT join to the current GEM/GEM JR queues.
    Trial registry status alone never means a successful primary endpoint.
    """
    ticker = clean_ticker(record.get("Ticker"))
    selected_ncts = set(re.findall(
        r"NCT\d{8}", str(record.get("NCT ID") or "").upper()
    ))
    by_nct = {}

    # A company-level inventory is also used by Section 4. Use it here to
    # expose Phase 1/2/3/4 siblings, not just Phase 3 observations.
    for item in company_trials or []:
        nct = str(item.get("nct") or "").strip().upper()
        if not re.fullmatch(r"NCT\d{8}", nct):
            continue
        by_nct[nct] = {
            "nct_id": nct, "drug": item.get("drug") or "",
            "indication": item.get("indication") or "",
            "phase": item.get("phase") or "",
            "source_url": item.get("selected_source") or "",
            "status": item.get("status") or "",
            "results_posted": item.get("results_posted") or "",
            "stage_labels": [x for x in ("GEM JR", "GEM")
                             if x in (item.get("stage_labels") or [])],
        }

    # Keep exact same-issuer registry rows when the company inventory is not
    # supplied by a caller, and enrich missing registry details when it is.
    for trial in registry:
        if clean_ticker(trial.get("ticker")) != ticker:
            continue
        nct = str(trial.get("nct_id") or "").strip().upper()
        if not re.fullmatch(r"NCT\d{8}", nct):
            continue
        entry = by_nct.setdefault(nct, {
            "nct_id": nct, "drug": "", "indication": "", "phase": "",
            "source_url": "", "status": "", "results_posted": "",
            "stage_labels": [],
        })
        for field in ("drug", "indication", "status", "results_posted", "source_url"):
            if not entry.get(field) and trial.get(field):
                entry[field] = trial[field]
        if (not entry.get("phase") or
                entry["phase"] == "Not verified in saved sources"):
            entry["phase"] = trial.get("phase") or trial.get("phases") or ""

    # A current research candidate can have no full clinical registry record.
    # Never backfill "Phase 3" merely because the selected card is in GEM.
    for nct in selected_ncts:
        by_nct.setdefault(nct, {
            "nct_id": nct, "drug": record.get("Drug") or "",
            "indication": record.get("Indication") or "",
            "phase": "", "source_url": "", "status": "",
            "results_posted": "", "stage_labels": [],
        })

    groups = {}
    for nct, trial in by_nct.items():
        selected = nct in selected_ncts
        drug = _text((record.get("Drug") if selected else trial.get("drug"))
                     or trial.get("drug"), "Drug not recorded")
        indication = _text((record.get("Indication") if selected
                            else trial.get("indication")) or trial.get("indication"),
                           "Indication not recorded")
        group = groups.setdefault((drug, indication), {
            "drug": drug, "indication": indication, "selected": False,
            "trials": [],
        })
        group["selected"] = group["selected"] or selected

        # Endpoint evidence must match this trial ID and issuer: no inheritance
        # across siblings or from other stocks reporting the same NCT.
        matched = [row for row in pvalues
                   if clean_ticker(row.get("ticker")) == ticker
                   and str(row.get("nct_id") or "").strip().upper() == nct]
        endpoints = "; ".join(dict.fromkeys(
            str(row.get("primary_endpoint") or "").strip() for row in matched
            if str(row.get("primary_endpoint") or "").strip()
        ))
        pvals = "; ".join(dict.fromkeys(
            str(row.get("p_value") or "").strip() for row in matched
            if str(row.get("p_value") or "").strip()
        ))
        pval_provenance = "Trial-matched saved endpoint evidence" if pvals else ""
        if not pvals and selected and len(selected_ncts) == 1:
            # This is a *program-level* value, not validated trial evidence.
            pvals = str(event.get("reported_p_values") or "").strip()
            if pvals:
                pval_provenance = "Program-level reported p-value; exact endpoint not independently checked"
        verified = (selected and len(selected_ncts) == 1
                    and str(record.get("Phase 3 status") or "") == "PRIMARY_MET_VERIFIED")
        primary_source = str(trial.get("source_url") or "").strip()
        if not primary_source and selected:
            primary_source = str(
                record.get("Phase 3 source") or record.get("Clinical source")
                or event.get("trial_evidence_url") or ""
            ).strip()
        if not primary_source.startswith("https://"):
            primary_source = ""

        stage_labels = [x for x in ("GEM JR", "GEM")
                        if x in (trial.get("stage_labels") or [])]
        group["trials"].append({
            "nct": nct,
            "phase": _text(trial.get("phase"), "Phase not verified"),
            "selected": selected,
            "url": f"https://clinicaltrials.gov/study/{nct}",
            "evidence_url": primary_source,
            "endpoint": endpoints or "Not available in saved sources",
            "p_value": pvals or "Not available in saved sources",
            "p_value_note": pval_provenance,
            "readout": ((record.get("Phase 3 date") or event.get("phase3_date") or "")
                        if selected else trial.get("results_posted") or ""),
            "patients": None,
            "result": ("Primary met — source-cleared" if verified
                       else _text(trial.get("status"), "Result not verified")),
            "result_type": "pass" if verified else "unknown",
            "stage_labels": stage_labels,
            "note": ("Source-cleared only for this exact program; does not authorize a trade."
                     if verified else
                     "Clinical trial phase and completion status do not prove endpoint success."),
        })
    for group in groups.values():
        group["trials"].sort(key=lambda t: (not t["selected"], t["nct"]))
    return sorted(groups.values(), key=lambda x: (
        not x["selected"], x["drug"].casefold(), x["indication"].casefold()
    ))


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


def _junior_section8_checks(record, event, profile, runway_result, sources,
                            clinical_facts):
    """Ordered GEM JR research-readiness observations, never an entry score.

    Explicit unknown means documents still need independent review.
    No inferred 2nd-financing qualification, or evidence of risk absence.
    """
    def entry(number, label, observed, status=None, source="",
              next_step="Verify current primary-source evidence"):
        return {
            "priority": number, "label": label,
            "detail": str(observed or "Not independently verified"),
            "status": status, "points": "—",
            "url": source if str(source).startswith("https://") else "",
            "next_step": next_step,
        }

    nct_ids = re.findall(r"NCT\d{8}",
                         str(record.get("NCT ID") or "").upper())
    pipeline_id = str(record.get("Pipeline ID") or "")
    phase_status = str(record.get("Phase 3 status") or
                       event.get("phase3_status") or "NOT VERIFIED")
    clinical_url = str(record.get("Phase 3 source") or
                       record.get("Clinical source") or
                       event.get("trial_evidence_url") or "")
    phase_date = str(record.get("Phase 3 date") or
                     event.get("phase3_date") or "")
    exact_identity = (pipeline_id.startswith(("APPLICATION|", "TRIAL|"))
                      and bool(nct_ids))
    source_linked_p3 = (len(nct_ids) == 1 and bool(phase_date[:10])
                        and clinical_url.startswith("https://")
                        and phase_status == "PRIMARY_MET_VERIFIED")
    source_by_name = {row.get("label"): row for row in sources}
    sec1 = source_by_name.get("Financing #1", {})
    sec2 = source_by_name.get("Financing #2", {})
    financings_rechecked = _number(record.get("SEC documents rechecked"))
    cash_months = _number(runway_result.get("Cash runway (months)"))
    cash_source = str(runway_result.get("Cash runway source") or "")
    market_cap = _number(event.get("market_cap"))
    dilution_flag = str(event.get("new_dilution_flag") or "").strip().upper()
    has_dilution_alert = dilution_flag in {"YES", "Y", "TRUE", "FLAGGED", "HIGH"}
    pdufa_source = source_by_name.get("PDUFA target", {})
    pdufa_saved = str(record.get("PDUFA date (saved)") or
                      record.get("PDUFA saved") or event.get("pdufa_date") or "")
    pdufa_verified = bool(
        record.get("PDUFA verified") is True or
        (str(event.get("pdufa_confirmation") or "").startswith("VERIFIED")
         and str(event.get("pdufa_evidence_url") or "").startswith("https://"))
    )
    exact_endpoint = clinical_facts.get("endpoint", {})
    safety = clinical_facts.get("safety", {})
    dollar_volume = _number(profile.get("dollar_volume"))
    market_fresh = profile.get("fresh") is True
    pending = str(record.get("Still needed") or "").strip()

    return [
        entry(1, "Exact Pipeline / NCT identity",
              pipeline_id + (" · " + ", ".join(nct_ids) if nct_ids else " · trial ID missing"),
              True if exact_identity else None, clinical_url,
              "Reconcile the same ticker, drug, indication and NCT ID"),
        entry(2, "Successful Phase 3 readout",
              f"{phase_status} · {phase_date or 'readout date unavailable'}",
              True if source_linked_p3 else None, clinical_url,
              "Verify dated primary endpoints for this exact trial, not a sibling"),
        entry(3, "Primary endpoint and safety review",
              ((str(exact_endpoint.get("label")) if exact_endpoint else
                 "Trial-specific endpoint not independently scored") +
               (" · safety evidence recorded" if safety else
                " · safety evidence incomplete")),
              None, clinical_url,
              "Inspect trial-matched p-values, endpoints and adverse-event details"),
        entry(4, "First post-readout financing",
              "SEC reference saved · verify transaction and chronology"
              if sec1.get("url") else "Independent first SEC closing not confirmed",
              None, sec1.get("url", ""),
              "Verify actual closing proceeds after the Phase 3 readout"),
        entry(5, "Second separate financing",
              (f"{int(financings_rechecked)}/2 SEC documents rechecked · "
               "this alone does NOT verify two qualifying post-readout closes")
              if financings_rechecked is not None
              else "Second independent post-readout closing not confirmed",
              None, sec2.get("url", ""),
              "Verify a distinct second closing; GEM eligibility remains separate"),
        entry(6, "Cash runway ≥12 months (research guide)",
              f"{cash_months:g} months · SEC source dated "
              f"{runway_result.get('Cash runway as of') or 'unavailable'}"
              if cash_months is not None else
              str(runway_result.get("Cash runway reason") or "Cash runway unavailable"),
              (cash_months >= 12 if cash_months is not None and
               cash_source.startswith("https://") else None),
              cash_source,
              "Verify cash-only runway and dilution assumptions"),
        entry(7, "Market cap $300M–$10B",
              f"USD {market_cap:,.0f} saved · independent current cap check pending"
              if market_cap is not None else "Market cap unavailable",
              (False if market_cap is not None and not
               300_000_000 <= market_cap <= 10_000_000_000 else None),
              "", "Refresh market cap before applying the selection filter"),
        entry(8, "Dilution / warrants / convertibles",
              ("Recorded dilution warning · investigate" if has_dilution_alert
               else "No independently verified absence of financing overhang"),
              False if has_dilution_alert else None,
              sec2.get("url", "") or sec1.get("url", ""),
              "Review SEC terms, outstanding warrants and future financing risk"),
        entry(9, "Trading liquidity / technical setup",
              f"Saved dollar volume USD {dollar_volume:,.0f}"
              if dollar_volume is not None and market_fresh else
              "Current dollar volume unavailable",
              None, "", "Compare liquidity with planned order size and entry setup"),
        entry(10, "PDUFA / FDA date verification",
              pdufa_saved or "No independently verified FDA target date",
              True if pdufa_verified else None,
              pdufa_source.get("url", ""),
              "Confirm current primary FDA or issuer source and PDUFA −3 policy"),
        entry(11, "Outstanding research / trade plan",
              pending or "Stage review and position-specific risk plan remain necessary",
              None, "", "Resolve source gaps; define entry, stop and target separately"),
    ]


def _section9_date(raw):
    """Parse one saved ISO calendar date; an unknown date is not a positive gate."""
    try:
        return date.fromisoformat(str(raw or "")[:10])
    except (ValueError, TypeError):
        return None


def _section9_item(priority, label, detail, status=None, url="", next_step="",
                   group="Review"):
    """True=evidence observed, False=explicit risk or block, None=unverified."""
    return {
        "priority": priority, "label": label, "detail": str(detail or "Not verified"),
        "status": status, "url": str(url) if str(url).startswith("https://") else "",
        "next_step": str(next_step), "group": group, "points": "—",
    }


def _junior_section9_exit_checks(record, event, profile, runway_result,
                                  today):
    """Early warning/downgrade research; never an auto-sell or exit score."""
    outcome = str(event.get("outcome") or record.get("FDA outcome") or "").upper().strip()
    resolved = outcome in {
        "APPROVED", "CRL", "REJECTED", "REFUSED", "WITHDRAWN",
        "COMPLETE_RESPONSE", "COMPLETE RESPONSE LETTER",
    }
    pdufa = _section9_date(record.get("PDUFA date (saved)") or
                           record.get("PDUFA saved") or event.get("pdufa_date"))
    days = (pdufa - today).days if pdufa else None
    phase = str(record.get("Phase 3 status") or
                event.get("phase3_status") or "").strip().upper()
    failed = phase in {
        "PRIMARY_FAILED_VERIFIED", "PHASE_3_FAILED_VERIFIED",
        "FAILED_PRIMARY_ENDPOINT", "PHASE3_FAILED",
    }
    safety = str(event.get("conflict_flag") or "").strip().upper()
    safety_flag = safety in {"YES", "TRUE", "1", "ACTIVE", "CONFLICT", "REVIEW"}
    dilution = str(event.get("new_dilution_flag") or "").strip().upper()
    dilution_flag = dilution in {"YES", "TRUE", "1", "ACTIVE", "UNRESOLVED",
                                "FLAGGED", "HIGH"}
    runway = _number(runway_result.get("Cash runway (months)"))
    runway_url = str(runway_result.get("Cash runway source") or "")
    runway_day = _section9_date(runway_result.get("Cash runway as of"))
    fresh_runway = (runway is not None and runway_url.startswith("https://")
                    and runway_day is not None and 0 <= (today - runway_day).days <= 90)
    fresh_price = bool(profile.get("fresh")) and profile.get("date") is not None
    close = _number(profile.get("close"))
    sma50 = _number(profile.get("sma50"))
    base = profile.get("base") or {}
    support = _number(base.get("support"))
    pdufa_url = str(event.get("pdufa_evidence_url") or "")
    clinical_url = str(record.get("Clinical source") or
                       record.get("Phase 3 source") or
                       event.get("trial_evidence_url") or "")
    second_sec = str(record.get("Financing SEC source") or "")
    review_date = _section9_date(record.get("Source review as of") or
                                 record.get("Source review date"))
    source_age = (today - review_date).days if review_date else None
    stale_review = source_age is not None and source_age > 7
    return [
        _section9_item(1, "Resolved or adverse FDA decision",
                       f"Saved FDA outcome: {outcome or 'unverified'}",
                       False if resolved else None, pdufa_url,
                       "Move resolved programs to prior candidates and verify the FDA outcome",
                       "Regulatory"),
        _section9_item(2, "Clinical failure or safety conflict",
                       f"Phase 3: {phase or 'not independently verified'} · "
                       f"safety conflict flag: {safety or 'unverified'}",
                       False if failed or safety_flag else None, clinical_url,
                       "Verify adverse trial findings and the exact program before any downgrade",
                       "Clinical"),
        _section9_item(3, "PDUFA / event-time exit boundary",
                       f"{days} days to saved PDUFA" if days is not None
                       else "FDA date missing or cannot be parsed",
                       False if days is not None and days <= 3 else None,
                       pdufa_url,
                       "Apply the selected PDUFA policy; a saved date alone is not FDA verification",
                       "Regulatory"),
        _section9_item(4, "Dilution / new financing overhang",
                       "Explicit dilution alert in saved ledger" if dilution_flag
                       else "Current dilution and warrant exposure not independently cleared",
                       False if dilution_flag else None, second_sec,
                       "Review new shelf, ATM, warrants and convertibles in dated SEC filings",
                       "Financing"),
        _section9_item(5, "Cash runway below 6 months",
                       f"{runway:g} months · saved SEC cash assessment"
                       if fresh_runway else
                       "No current source-backed cash-only runway assessment",
                       False if fresh_runway and runway < 6 else None,
                       runway_url, "Recheck cash burn and expected financing needs",
                       "Financing"),
        _section9_item(6, "Breakdown below closing support",
                       f"Close {_money(close)} / support {_money(support)}"
                       if fresh_price and close is not None and support is not None
                       else "Current closing-price support unavailable",
                       False if fresh_price and close is not None and
                       support is not None and close < support else None, "",
                       "Review closing support and your position-specific stop; no auto-exit",
                       "Technical"),
        _section9_item(7, "SMA50 loss and momentum deterioration",
                       f"Close {_money(close)} / SMA50 {_money(sma50)}"
                       if fresh_price and close is not None and sma50 is not None
                       else "Current price/SMA50 comparison unavailable",
                       False if fresh_price and close is not None and
                       sma50 is not None and close < sma50 else None, "",
                       "Confirm trend change using dated EOD data and independent news",
                       "Technical"),
        _section9_item(8, "Stale / unresolved clinical and financing sources",
                       f"Latest saved program review: {review_date or 'not available'}",
                       False if stale_review else None, "",
                       "Refresh clinical, regulatory and SEC sources before making an exit decision",
                       "Sources"),
        _section9_item(9, "Research list / GEM promotion review",
                       "GEM JR is research only; moving to GEM requires the exact "
                       "successful Phase 3 program; financing history optional",
                       None, "", "Check current GEM membership and qualification separately",
                       "Workflow"),
    ]


def _gem_section9_entry_checks(record, event, profile, runway_result,
                                today, source_current=None):
    """Prioritized exact-program entry research gates; no automatic buy.

    Successful Phase 3 is the clinical qualifier; financing evidence is optional.
    Independently verified *current* SEC coverage remains a separate hard hold.
    """
    ncts = re.findall(r"NCT\d{8}", str(record.get("NCT ID") or "").upper())
    trial_url = str(record.get("Phase 3 source") or
                    record.get("Clinical source") or
                    event.get("trial_evidence_url") or "")
    p3_day = _section9_date(record.get("Phase 3 date") or
                            event.get("phase3_date"))
    p3_status = str(record.get("Phase 3 status") or "").upper()
    phase3_observed = (len(ncts) == 1 and p3_day is not None and p3_day <= today and
                       p3_status == "PRIMARY_MET_VERIFIED" and
                       trial_url.startswith("https://"))
    first_day = _section9_date(record.get("First close"))
    second_day = _section9_date(record.get("Second close"))
    first_url = str(record.get("First SEC source") or "")
    second_url = str(record.get("Second SEC source") or "")
    two_closes = bool(
        record.get("Second financing verified") is True
        and phase3_observed and first_day is not None
        and second_day is not None and p3_day < first_day < second_day <= today
        and first_url.startswith("https://") and second_url.startswith("https://")
        and first_url != second_url
    )
    review_day = _section9_date(record.get("Source review as of") or
                                record.get("Source review date"))
    review_age = (today - review_day).days if review_day else None
    # Global current SEC source coverage remains a hard hold; its freshness
    # must not depend on whether an optional second-close review exists.
    sec_current = source_current is True
    runway = _number(runway_result.get("Cash runway (months)"))
    cash_url = str(runway_result.get("Cash runway source") or "")
    cash_day = _section9_date(runway_result.get("Cash runway as of"))
    cash_current = (runway is not None and cash_url.startswith("https://")
                    and cash_day is not None and 0 <= (today - cash_day).days <= 90)
    cap = _number(event.get("market_cap"))
    dilution = str(event.get("new_dilution_flag") or "").upper().strip()
    dilution_flag = dilution in {"YES", "TRUE", "1", "ACTIVE", "UNRESOLVED",
                                 "FLAGGED", "HIGH"}
    conflict = str(event.get("conflict_flag") or "").upper().strip()
    safety_flag = conflict in {"YES", "TRUE", "1", "ACTIVE", "CONFLICT", "REVIEW"}
    pdufa = _section9_date(record.get("PDUFA saved") or
                           record.get("PDUFA date (saved)") or
                           event.get("pdufa_date"))
    days = (pdufa - today).days if pdufa else None
    pdufa_verified = (
        (record.get("PDUFA verified") is True or
         (str(event.get("pdufa_confirmation") or "").startswith("VERIFIED")
          and str(event.get("pdufa_evidence_url") or "").startswith("https://")))
    )
    pdufa_url = str(event.get("pdufa_evidence_url") or "")
    fresh_price = bool(profile.get("fresh")) and profile.get("date") is not None
    close = _number(profile.get("close"))
    sma20 = _number(profile.get("sma20"))
    sma50 = _number(profile.get("sma50"))
    dollar_vol = _number(profile.get("dollar_volume"))
    tradable_setup = (fresh_price and close is not None and
                      sma20 is not None and sma50 is not None)
    outcome = str(event.get("outcome") or record.get("FDA outcome") or "").upper()
    resolved = outcome in {"APPROVED", "CRL", "REJECTED", "REFUSED",
                           "WITHDRAWN", "COMPLETE_RESPONSE"}
    return [
        _section9_item(1, "Exact successful Phase 3 program",
                       f"{record.get('NCT ID') or 'No NCT'} · "
                       f"{p3_status or 'not verified'} · {p3_day or 'no readout date'}",
                       True if phase3_observed else None, trial_url,
                       "Open primary results and confirm the endpoint for this NCT",
                       "Hard gate"),
        _section9_item(2, "First independent post-readout SEC close",
                       f"Saved close: {first_day or 'not recorded'}",
                       True if two_closes else None, first_url,
                       "Optional SEC funding history to inform dilution risk",
                       "Optional evidence"),
        _section9_item(3, "Second distinct post-readout SEC close",
                       f"Saved close: {second_day or 'not recorded'}",
                       True if two_closes else None, second_url,
                       "Optional second funded close; two URLs alone prove nothing",
                       "Optional evidence"),
        _section9_item(4, "Current source recheck / entry hold",
                       f"Global SEC current: {source_current is True} · "
                       f"program review age: {review_age if review_age is not None else 'unknown'} days",
                       True if sec_current else False, "",
                       "Refresh SEC source ledger and exact-program evidence before considering entry",
                       "Hard gate"),
        _section9_item(5, "FDA event timing / resolved outcome",
                       (f"{days} days to saved PDUFA" if days is not None
                        else "Current PDUFA date unverified") +
                       (f" · FDA outcome: {outcome}" if resolved else ""),
                       False if resolved or (days is not None and days <= 3) else
                       True if pdufa_verified and days is not None and days > 3 else None,
                       pdufa_url,
                       "Confirm primary date; apply PDUFA −3 policy consistently",
                       "Hard gate"),
        _section9_item(6, "Cash-only runway ≥12 months (guide)",
                       f"{runway:g} months (saved SEC)" if cash_current
                       else "Source-backed cash assessment not available",
                       (runway >= 12 if cash_current else None), cash_url,
                       "Review spending, cash burn and financing commitments",
                       "Risk"),
        _section9_item(7, "Market cap $300M–$10B",
                       f"Saved issuer cap: {_money(cap)}" if cap is not None
                       else "Current market cap not available",
                       False if cap is not None and not
                       300_000_000 <= cap <= 10_000_000_000 else None, "",
                       "Revalidate market cap independently; saved in-range is not verified current",
                       "Risk"),
        _section9_item(8, "Dilution / safety / convertible review",
                       (("Dilution alert; " if dilution_flag else "") +
                        ("Safety conflict; " if safety_flag else "")).strip("; ") or
                       "No independent clearance of dilution, safety, warrants or convertibles",
                       False if dilution_flag or safety_flag else None,
                       second_url or trial_url,
                       "Inspect SEC offering terms, adverse events and clinical conflicts",
                       "Risk"),
        _section9_item(9, "Fresh price trend and liquidity",
                       f"Close {_money(close)} · SMA20 {_money(sma20)} · "
                       f"SMA50 {_money(sma50)} · dollar volume {_money(dollar_vol)}"
                       if tradable_setup else "Current priced technical setup unavailable",
                       None if not tradable_setup else
                       False if close < sma50 else None, "",
                       "Review risk/reward, current bid/ask liquidity and relative strength",
                       "Technical"),
        _section9_item(10, "Independent trade plan and entry authorization",
                       "Chart reference levels and risk policy require explicit review; "
                       "candidate qualification is not a BUY",
                       None, "",
                       "Set entry, stop, target, position size and reward/risk; no automatic orders",
                       "Workflow"),
    ]


def _junior_section10_history(state):
    """Timeline of scan-observed GEM JR periods; no inferred stage dates."""
    stages = state.get("stages") or {}
    junior_slot = stages.get("GEM_JR") or {}
    gem_slot = stages.get("GEM") or {}
    gem_entries = gem_slot.get("entries") or {}
    rows = []
    for pid, item in (junior_slot.get("entries") or {}).items():
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        other = gem_entries.get(pid) or {}
        for index, period in enumerate(item.get("periods") or []):
            if not isinstance(period, dict):
                continue
            found = _section9_date(period.get("found"))
            left = _section9_date(period.get("left"))
            if found is None or (left and left < found):
                continue
            reason = str(period.get("reason") or "").strip()
            first_gem = _section9_date(other.get("first_found"))
            promoted = (left and reason == "PROMOTED_TO_GEM"
                        and other.get("ticker") == ticker
                        and first_gem is not None and first_gem <= left)
            movement = ("PROMOTED TO GEM" if promoted else
                        "PROMOTION NEEDS REVIEW" if reason == "PROMOTED_TO_GEM" else
                        "LEFT GEM JR" if left else
                        "RE-ENTERED GEM JR" if index else "ACTIVE IN GEM JR")
            current = ("GEM JR" if item.get("status") == "ACTIVE" else
                       "GEM" if other.get("status") == "ACTIVE"
                       and other.get("ticker") == ticker else "PRIOR CANDIDATE")
            rows.append({
                "id": pid, "ticker": ticker, "drug": str(item.get("drug") or ""),
                "nct": str(item.get("nct_id") or ""),
                "found": found.isoformat(),
                "left": left.isoformat() if left else "",
                "duration_days": (left - found).days if left else None,
                "movement": movement, "reason": reason or
                  ("ACTIVE — NO EXIT OBSERVED" if not left else "EXIT REASON NOT RECORDED"),
                "current_stage": current,
                "gem_first_found": first_gem.isoformat() if first_gem and
                  other.get("ticker") == ticker else "",
            })
    return sorted(rows, key=lambda r: (r["left"] or r["found"],
                                          r["ticker"], r["id"]), reverse=True)


def _gem_section10_exit_checks(record, event, profile, runway_result,
                                today, source_current=None):
    """Source-dated exit risk observations, not sell instructions."""
    def check(priority, name, detail, triggered=None, source="", next_step="",
              kind="Risk"):
        return {
            "priority": priority, "label": name, "detail": str(detail),
            "triggered": triggered,
            "url": source if str(source).startswith("https://") else "",
            "next_step": next_step, "kind": kind,
        }

    outcome = str(event.get("outcome") or record.get("FDA outcome") or "").strip().upper()
    settled = outcome in {"APPROVED", "CRL", "REJECTED", "REFUSED",
                          "WITHDRAWN", "COMPLETE_RESPONSE"}
    pdufa = _section9_date(record.get("PDUFA saved") or event.get("pdufa_date"))
    days = (pdufa - today).days if pdufa else None
    adverse = str(event.get("conflict_flag") or "").strip().upper()
    dilute = str(event.get("new_dilution_flag") or "").strip().upper()
    flags = {"YES", "TRUE", "1", "ACTIVE", "UNRESOLVED", "FLAGGED", "HIGH"}
    safety = adverse in flags | {"CONFLICT", "REVIEW"}
    dilution = dilute in flags
    fda_link = str(event.get("pdufa_evidence_url") or "")
    trial_link = str(record.get("Phase 3 source") or event.get("trial_evidence_url") or "")
    sec_link = str(record.get("Second SEC source") or "")
    runway = _number(runway_result.get("Cash runway (months)"))
    cash_link = str(runway_result.get("Cash runway source") or "")
    cash_day = _section9_date(runway_result.get("Cash runway as of"))
    cash_current = (runway is not None and cash_link.startswith("https://")
                    and cash_day is not None and 0 <= (today - cash_day).days <= 90)
    last = profile.get("date")
    if isinstance(last, datetime):
        last = last.date()
    fresh = (profile.get("fresh") is True and isinstance(last, date)
             and 0 <= (today - last).days <= 5)
    close = _number(profile.get("close"))
    support = _number((profile.get("base") or {}).get("support"))
    sma50 = _number(profile.get("sma50"))
    rsi = _number(profile.get("rsi"))
    macd = profile.get("macd")
    macd_direction = macd.get("bullish") if isinstance(macd, dict) else None
    market_rows = []
    for bar in profile.get("bars") or []:
        if not isinstance(bar, dict):
            continue
        day = bar.get("date")
        if isinstance(day, datetime):
            day = day.date()
        if not isinstance(day, date):
            day = _section9_date(day)
        value = _number(bar.get("close"))
        if day is not None and value is not None:
            market_rows.append((day, value))
    market_rows.sort(key=lambda r: r[0])
    # Refuse duplicate dates rather than constructing a false two-day sequence.
    unique_dates = len({x[0] for x in market_rows}) == len(market_rows)
    two_below = None
    if fresh and unique_dates and len(market_rows) >= 21 and market_rows[-1][0] == last:
        values = [v for _, v in market_rows]
        two_below = (values[-2] < sum(values[-21:-1])/20
                     and values[-1] < sum(values[-20:])/20)
    sec_day = _section9_date(record.get("Source review as of") or
                             record.get("Source review date"))
    sec_current = (source_current is True and sec_day is not None
                   and 0 <= (today - sec_day).days <= 7)

    return [
        check(1, "FDA outcome / material decision",
              "Saved FDA outcome: " + (outcome or "unverified"),
              True if settled else None, fda_link,
              "Confirm the actual decision from dated primary sources", "Event"),
        check(2, "PDUFA event window (policy-dependent)",
              str(days) + " days to saved PDUFA" if days is not None
              else "PDUFA date unavailable",
              days <= 3 if days is not None else None, fda_link,
              "Use the separately selected PDUFA exit policy; no automatic order", "Event"),
        check(3, "Clinical safety / program risk",
              "Saved safety flag: " + (adverse or "unverified"),
              True if safety else None, trial_link,
              "Review clinical adverse events and exact-trial evidence", "Clinical"),
        check(4, "Dilution, warrants, convertibles",
              "Saved dilution flag: " + (dilute or "unverified"),
              True if dilution else None, sec_link,
              "Inspect SEC terms and financing overhang", "Financing"),
        check(5, "Cash runway below 6 months",
              f"Saved SEC cash runway {runway:g} months" if cash_current
              else "Current source-backed cash assessment unavailable",
              runway < 6 if cash_current else None, cash_link,
              "Verify cash burn, runway date and new offering risk", "Financing"),
        check(6, "Closing support lost",
              f"Close {_money(close)}; support {_money(support)}"
              if fresh and close is not None and support is not None
              else "Current closing support unavailable",
              close < support if fresh and close is not None and support is not None
              else None, "", "Review support and the manually defined hard stop", "Technical"),
        check(7, "Two closes below daily SMA20",
              "Daily SMA20 recomputed separately for prior and latest close"
              if two_below is not None else "Requires 21 distinct, current closing-price observations",
              two_below, "", "Advisory trend warning, not a hard stop", "Technical"),
        check(8, "Close below SMA50",
              f"Close {_money(close)}; SMA50 {_money(sma50)}"
              if fresh and close is not None and sma50 is not None else
              "Current SMA50 unavailable",
              close < sma50 if fresh and close is not None and sma50 is not None
              else None, "", "Review longer trend and corroborating sources", "Technical"),
        check(9, "Saved MACD bearish direction",
              "Bearish" if macd_direction is False else
              "Bullish" if macd_direction is True else "Unavailable",
              macd_direction is False if fresh and macd_direction in (True, False)
              else None, "", "Momentum indicator, not an independently proven exit", "Technical"),
        check(10, "RSI elevated / reversal context",
              f"RSI(14) {rsi:g}" if fresh and rsi is not None else "Fresh RSI unavailable",
              rsi >= 70 if fresh and rsi is not None else None, "",
              "An RSI reference of 70 is not an automatic sell", "Technical"),
        check(11, "ATR trail / intraday VWAP",
              "Not available from saved close-only price bars", None, "",
              "Requires OHLC / intraday market data; never infer", "Unavailable"),
        check(12, "Current SEC and primary-source health",
              "Source recheck current" if sec_current else "Missing, stale or partial source verification",
              False if sec_current else True, "",
              "Refresh program-specific and global SEC source checks", "Sources"),
    ]


def _candidate(stage, ranked, root, today, companies, financings, runway, registry, pvalues, company_trials=None, trial_coverage="Trial source coverage not independently verified", source_current=None, tranche_ledger=None):
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
                                 second_close=second if record.get("Second financing verified") is True else None)
    runway_months = runway_result["Cash runway (months)"]
    # Independent research overlay: actual net funded tranches only. Never
    # promotes the strict Step 4 runway gate or proves financing safety.
    tranche_runway = assess_tranche_runway(
        ticker, runway.get(ticker), (tranche_ledger or {}).get(ticker, []),
        as_of=today, event_key=str(event.get("event_key") or funding.get("event_key") or ""),
    )
    entry, risk = score.get("entry"), score.get("exit_risk")
    status = "Research" if junior else "Qualified · Hold"
    status_type = "review" if junior else "pass"
    trade_status = _text(record.get("Trade status") or record.get("Still needed"))
    if "NO NEW ENTRY" in trade_status:
        status, status_type = "Entry hold", "hold"
    # A date + an SEC URL alone is not a verified funded close. Do not
    # paint either transaction green without exact-event closing clearance.
    verified_closes = bool(record.get("Second financing verified") is True and not junior)
    financings_display = [{"date": d, "url": u, "amount": "—", "price": "—", "warrants": "—",
                           "status": "Confirmed" if verified_closes and d and u else "Review",
                           "type": "pass" if verified_closes and d and u else "review"}
                          for d, u in ((first, first_url), (second, second_url))]
    sources = [
        _source("Phase 3 results", "Primary clinical evidence", clinical_url, p3_date,
                not junior and bool(clinical_url)),
        _source("Financing #1", "SEC closing evidence (optional)", first_url, first, verified_closes and bool(first_url)),
        _source("Financing #2", "SEC closing evidence (optional)", second_url, second, verified_closes and bool(second_url)),
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
    junior_research_checks = (
        _junior_section8_checks(
            record, event, profile, runway_result, sources,
            _criterion_facts(record, event, master, profile, funding,
                             pvalues, ticker, clinical_url),
        ) if junior else []
    )
    section9_checks = (
        _junior_section9_exit_checks(record, event, profile, runway_result, today)
        if junior else
        _gem_section9_entry_checks(record, event, profile, runway_result, today,
                                   source_current=source_current)
    )
    section10_checks = (_gem_section10_exit_checks(
        record, event, profile, runway_result, today, source_current=source_current)
        if not junior else [])
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
        "company_trials": (company_trials or {}).get(ticker, []),
        "company_trial_coverage": trial_coverage,
        "drug": _text(record.get("Drug")), "indication": _text(record.get("Indication")),
        "nct": _text(record.get("NCT ID")), "readout": p3_date, "pdufa": pdufa,
        "pdufa_verified": pdufa_verified, "runway": runway_months,
        "runway_reason": runway_result["Cash runway reason"], "cash": _money(cash),
        "tranche_runway": tranche_runway,
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
        "financing_label": "OPTIONAL · SEC financing review",
        "financing_detail": _text(record.get("Still needed"), "Independent source recheck required before trading"),
        "source_review": record.get("Source review as of") or record.get("Source review date") or "",
        "financings": financings_display, "sources": sources, "profile": info,
        "entry_checks": _checks(score.get("entry_factors"), record, event, profile, junior=junior),
        "junior_research_checks": junior_research_checks,
        "section9_checks": section9_checks,
        "section10_checks": section10_checks,
        "exit_checks": _checks(score.get("exit_factors"), record, event, profile, junior=junior, exit_risk=True),
        "hierarchy": _hierarchy(record, event, company, registry, pvalues,
                                (company_trials or {}).get(ticker, [])), "alerts": alerts,
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


def _gem_history_timeline(state):
    """Exact Pipeline ID GEM membership periods; only scan-observed dates."""
    slot = ((state.get("stages") or {}).get("GEM") or {})
    results = []
    for pid, item in (slot.get("entries") or {}).items():
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker") or "").strip().upper()
        if not ticker or not pid.startswith(("TRIAL|", "APPLICATION|")):
            continue
        for index, period in enumerate(item.get("periods") or []):
            if not isinstance(period, dict):
                continue
            found = _section9_date(period.get("found"))
            left = _section9_date(period.get("left"))
            if found is None or (left is not None and left < found):
                continue
            results.append({
                "id": pid, "ticker": ticker,
                "drug": str(item.get("drug") or ""),
                "nct": str(item.get("nct_id") or ""),
                "found": found.isoformat(),
                "left": left.isoformat() if left else "",
                "movement": ("LEFT GEM" if left else
                             "RE-ENTERED GEM" if index else "ACTIVE IN GEM"),
                "reason": str(period.get("reason") or
                              ("OPEN OBSERVED MEMBERSHIP" if not left else
                               "EXIT REASON UNAVAILABLE")),
                "current_stage": ("GEM" if item.get("status") == "ACTIVE"
                                  else "PRIOR CANDIDATE"),
                "duration_days": (left - found).days if left else None,
            })
    return sorted(results, key=lambda r: (
        r["left"] or r["found"], r["ticker"], r["id"]
    ), reverse=True)


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
    junior_active, junior_held = build_potential_list(root, as_of=today)
    excluded = {str(x.get("Pipeline ID") or "") for x in qualified + historical}
    junior_active = [r for r in junior_active
                     if str(r.get("Pipeline ID") or "") not in excluded]
    # Build cross-stage trial flags from exact active program identities; no
    # archived GEM status is inherited by the current research listing.
    company_trials, trial_coverage = _all_company_trials(
        root, gem=qualified, junior=junior_active
    )
    if stage == "GEM JR":
        active, held = junior_active, junior_held
    else:
        active, held = qualified, historical
    active = enrich_stage_rows(active, "GEM_JR" if stage == "GEM JR" else "GEM", history)
    # A duplicated program cannot become an ambiguous button target.
    active_by_id = _unique(active, "Pipeline ID")
    active = [r for r in active if active_by_id.get(str(r.get("Pipeline ID") or "")) is r]
    companies = _unique(_csv(root, "company_registry.csv"), "ticker")
    finance = _unique(_csv(root, "second_financing_status.csv"), "event_key")
    runway = load_snapshots(root)
    tranche_ledger = load_tranches(root)
    registry = _csv(root, "all_phase_trials.csv")
    pvalues = _csv(root, "phase3_primary_pvalues.csv")
    candidates = [_candidate(stage, r, root, today, companies, finance, runway,
                             registry, pvalues, company_trials, trial_coverage,
                             source_current=current, tranche_ledger=tranche_ledger)
                  for r in _rankings(stage, active, root, today)]
    junior_timeline = _junior_section10_history(history) if stage == "GEM JR" else []
    gem_timeline = _gem_history_timeline(history) if stage == "GEM" else []
    departed = departed_stage_rows(history, "GEM_JR" if stage == "GEM JR" else "GEM")
    histories = [{"date": r.get("Date Left") or "", "ticker": r.get("Ticker") or "",
                  "drug": r.get("Drug") or "", "reason": r.get("Leave Reason") or ""}
                 for r in departed]
    # Section 12 is a saved-report diagnostic view, not a live execution feed.
    # Collector COMPLETED never upgrades missing FDA/SEC/source coverage.
    scans = scan_diagnostics(root)
    return {
        "stage": stage, "junior": stage == "GEM JR", "candidates": candidates,
        "history": histories, "junior_timeline": junior_timeline,
        "gem_timeline": gem_timeline,
        "gem_history_snapshot": str((history.get("stages") or {}).get("GEM", {}).get("last_complete_snapshot") or ""),
        "history_snapshot": str((history.get("stages") or {}).get("GEM_JR", {}).get("last_complete_snapshot") or ""),
        "held_count": len(held), "source_current": bool(current),
        "alerts": [a for c in candidates for a in c["alerts"]][:12], "scans": scans,
        "scan_note": "Saved reports only; collector completion is not full-source verification. Open SCANS for live job status.",
        "rules": [
            "Successful Phase 3 for the exact drug + indication, with primary-source results.",
            "Second financing is OPTIONAL clinical-qualification context; record SEC closes if verified.",
            "Clear current dilution risk and independently verify available cash runway before entry."
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
    # Source-isolated, operator-triggered Alpaca technical observations.
    # Never promotes an unverified trial to GEM trade eligibility.
    from alpaca_gem_provider import render_provider_panel
    render_provider_panel(stage, root)
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
