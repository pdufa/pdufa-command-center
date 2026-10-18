"""Transparent GEM umbrella benchmarks and optional research checkboxes.

Only the two existing source-attested events confer GEM ranking eligibility.
Everything else is a visible advisory observation, never an automatic gate.
A partial source observation is REVIEW (not a verified PASS).
"""
from __future__ import annotations

import math
import re

from gem_master_list import PHASE3_OK, FINANCING_OK

BENCHMARKS = (
    ("phase3_verified", "1. Phase 3 RESULTS released — exact-program verified"),
    ("financing_verified", "OPTIONAL. Second financing CLOSED — distinct post-readout transactions"),
)
UMBRELLA = (
    ("phase3_data", "Phase 3 data / issuer lead observed (research umbrella)"),
    ("financing_lead", "Second financing historically attested (research umbrella)"),
)
ADVISORIES = (
    ("clinical_quality", "Phase 3 endpoints / benefit / safety fully attested"),
    ("clinical_conflict", "No clinical or regulatory conflict verified"),
    ("cash_runway", "SEC cash runway at least 12 months"),
    ("dilution", "No unresolved dilution verified"),
    ("price_base", "Post-readout base and volume evidence attested"),
    ("market_quote", "Current market price/volume evidence"),
    ("pdufa_source", "FDA / PDUFA date source verified"),
    ("pdufa_window", "Within preferred 30–90-day PDUFA window"),
    ("hedge_funds", "Specialist fund accumulation in SEC 13F"),
    ("insiders", "SEC Form 4 insider open-market purchases"),
    ("sec_fresh", "Global SEC financing source recheck current"),
    ("clinical_fresh", "Clinical / market source feed current"),
)
CHECKS = BENCHMARKS + UMBRELLA + ADVISORIES
CHECK_LABELS = dict(CHECKS)
FILTERABLE = tuple(key for key, _ in CHECKS)


def _num(value):
    try:
        if value is None or isinstance(value, bool) or str(value).strip() == "":
            return None
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _state(passed=False, detail="Not verified", *, observed=False, risk=False):
    return {
        "checked": bool(passed),
        "observed": bool(observed),
        "status": "PASS" if passed else ("RISK" if risk else "RESEARCH LEAD" if observed else "NOT VERIFIED"),
        "detail": str(detail),
    }


def build_checklist(master, source=None, *, finance_audit=None,
                    clinical_audit=None, sec_current=False, feed_current=False):
    """Return exactly 16 immutable-source check states for an exact program.

    The caller must link source and audits by UNIQUE exact event identity.
    Verified benchmark states originate ONLY from gem_two_benchmark.
    """
    src = source or {}
    fin = finance_audit or {}
    clinical = clinical_audit or {}
    phase3 = master.get("Phase 3 Verified") == PHASE3_OK
    finance = master.get("Second Financing Closed") == FINANCING_OK
    historical_finance = bool(
        master.get("Second Financing Close Date")
        or fin.get("historical_audit_status") == "VERIFIED_SECOND_POST_PHASE3_FINANCING"
    )
    p3_status = str(src.get("Phase 3 evidence") or "")
    registry_status = str(clinical.get("source_recheck_status") or "")
    known_non_phase3 = str(clinical.get("saved_phase3_status") or "").upper() == "PHASE_1_2_NOT_PHASE_3"
    phase3_lead = not known_non_phase3 and (
        phase3 or
        registry_status == "POSTED_RESULTS_DISCOVERY_ONLY"
        or p3_status.startswith((
            "VERIFIED SUCCESS", "REGISTRY RESULTS POSTED",
            "ISSUER ANNOUNCEMENT", "POTENTIAL ISSUER READOUT",
        ))
    )
    clinical_score = _num(src.get("Clinical evidence /30"))
    positive_phase3 = str(src.get("GEM clinical readout status") or "").strip().upper() in {
        "VERIFIED_SUCCESS", "PRIMARY_MET_VERIFIED"
    }
    conflict = str(src.get("GEM clinical conflict flag") or "").strip().upper()
    dilution = str(src.get("GEM financing dilution flag") or "").strip().upper()
    cash = _num(src.get("Cash runway (months)"))
    cash_gate = str(src.get("Cash runway gate") or "")
    setup = _num(src.get("Trading setup /20"))
    activity = _num(src.get("Market activity /10"))
    days = master.get("Days to PDUFA")
    days_ok = type(days) is int
    pdufa = str(src.get("PDUFA verification") or "") == "VERIFIED — SOURCE LINKED"
    hedge = (src.get("Hedge-fund signal") ==
             "SOURCE-VERIFIED QUARTERLY 13F HOLDINGS")
    insiders = (src.get("Insider Form 4 signal") ==
                "SOURCE-VERIFIED SEC FORM 4 OBSERVATIONS")
    hedge_adds = _num(src.get("Hedge-fund managers adding"))
    insider_buys = _num(src.get("Insider open-market purchases"))
    safe_flags = {"NO", "NONE", "FALSE", "0", "PASS"}
    danger_flags = {"YES", "TRUE", "1", "ACTIVE", "UNRESOLVED", "CONFLICT"}
    out = {
        "phase3_verified": _state(phase3, "Verified source-linked exact-program results" if phase3 else "Readout result / trial identity has not passed independent verification"),
        "financing_verified": _state(finance, "Distinct second post-readout financing close attested" if finance else "Fresh exact-event financing #2 attestation not established"),
        "phase3_data": _state(phase3, "Verified results" if phase3 else (
            "Registry/issuer observation — NOT a verified efficacy result" if phase3_lead else
            "No exact-program results observation yet"), observed=phase3_lead and not phase3),
        "financing_lead": _state(finance, "Verified second close" if finance else (
            "Historical two-close attestation; current verification remains separate" if historical_finance else
            "No historical second-close attestation for this program"), observed=historical_finance and not finance),
        "clinical_quality": _state(phase3 and positive_phase3 and clinical_score == 30,
                                   "Full source-attested successful clinical evidence" if phase3 and positive_phase3 and clinical_score == 30 else
                                   "Endpoint, clinical benefit or safety assessment not fully attested"),
        "clinical_conflict": _state(conflict in safe_flags, "Explicit no-conflict flag" if conflict in safe_flags
                                    else "Clinical / regulatory source conflict not cleared", risk=conflict in danger_flags),
        "cash_runway": _state(cash is not None and cash >= 12 and cash_gate.startswith("PASS"),
                              f"{cash:g} months, SEC verified" if cash is not None and cash >= 12 and cash_gate.startswith("PASS")
                              else (f"{cash:g} months (below preference / source gate)" if cash is not None else
                                    "SEC cash-only runway missing or stale"),
                              risk=cash is not None and cash < 12),
        "dilution": _state(dilution in safe_flags, "Source reported no current dilution" if dilution in safe_flags
                            else "Dilution unclear or unresolved", risk=dilution in danger_flags),
        "price_base": _state(feed_current and setup == 20,
                              "Fully attested price-base and normalized-volume evidence" if feed_current and setup == 20
                              else "Post-readout base / normalized volume not fully source-attested"),
        "market_quote": _state(feed_current and activity is not None and activity >= 4,
                                "Current provider quote / market activity" if feed_current and activity is not None and activity >= 4
                                else "No fresh source-attested quote/volume"),
        "pdufa_source": _state(pdufa, "Verified FDA/issuer action date" if pdufa else
                               "PDUFA date awaits source verification"),
        "pdufa_window": _state(pdufa and days_ok and 30 <= days <= 90,
                               f"{days} days to PDUFA" if pdufa and days_ok else
                               "Preferred 30–90d window not established; outside window is not disqualification"),
        "hedge_funds": _state(hedge and hedge_adds is not None and hedge_adds > 0,
                              "Quarterly 13F accumulation; not real-time buying" if hedge and hedge_adds and hedge_adds > 0 else
                              "Fund accumulation not established in sourced 13F"),
        "insiders": _state(insiders and insider_buys is not None and insider_buys > 0,
                           "SEC Form 4 open-market purchase(s) verified" if insiders and insider_buys and insider_buys > 0 else
                           "Open-market purchases not source verified"),
        "sec_fresh": _state(sec_current, "Current SEC source health" if sec_current
                             else "SEC global collector partial / stale / blocked"),
        "clinical_fresh": _state(feed_current, "Source feed current" if feed_current
                                  else "Clinical/market source feed stale"),
    }
    assert set(out) == set(FILTERABLE)
    return out


def program_key(row):
    """Exact regulatory event if available; otherwise unique ticker+NCT trial.

    NCT fallback can display Phase 3 research observations, but does not
    manufacture a regulatory link or financing closure.
    """
    exact = str(row.get("Exact Program / Event") or row.get("Exact event") or "").strip()
    if exact:
        return "EVENT|" + exact
    ticker = str(row.get("Ticker") or "").strip().upper()
    nct = str(row.get("NCT ID") or "").strip().upper()
    if (re.fullmatch(r"[A-Z0-9.-]{1,15}", ticker)
            and re.fullmatch(r"NCT\d{8}", nct)):
        return "TRIAL|" + ticker + "|" + nct
    return ""


def filter_programs(rows, checklists, selected=()):
    """Optional checkbox filters only alter the VIEW, never program eligibility."""
    keys = set(selected)
    if not keys.issubset(FILTERABLE):
        raise ValueError("Unknown GEM checkbox filter")
    return [row for row in rows
            if all(
                (checklists.get(program_key(row), {})
                 .get(key, {}).get("checked") is True)
                or (key in dict(UMBRELLA) and
                    checklists.get(program_key(row), {})
                    .get(key, {}).get("observed") is True)
                for key in keys
            )]


def _unique(records, field):
    """Never attach one program's sources to a repeated or missing event key."""
    mapping, duplicates = {}, set()
    for item in records or ():
        key = (str(item.get(field) or "").strip() if field else program_key(item))
        if not key:
            continue
        if key in mapping:
            duplicates.add(key)
        else:
            mapping[key] = item
    for key in duplicates:
        mapping.pop(key, None)
    return mapping


def build_checklist_map(master_rows, saved_sources=(), financing_rechecks=(),
                        clinical_rechecks=(), *, sec_current=False,
                        feed_current=False):
    """Link only unique event keys; watch records remain present but unrated."""
    # Unique exact event when established, or unique ticker+NCT research identity
    # for registry leads. Never use issuer ticker alone to transfer SEC evidence.
    master_by_event = _unique(master_rows, None)
    sources = _unique(saved_sources, None)
    finance = _unique(
        ({"Exact event": r.get("event_key"), **r} for r in financing_rechecks),
        None,
    )
    clinical = _unique(
        ({"Exact event": r.get("event_key"), **r} for r in clinical_rechecks),
        None,
    )
    return {
        key: build_checklist(
            master, sources.get(key),
            finance_audit=finance.get(key),
            clinical_audit=clinical.get(key),
            sec_current=sec_current, feed_current=feed_current,
        )
        for key, master in master_by_event.items()
    }

def research_candidate_rows(master_rows, checklist_map, *, clinical_rechecks=(),
                            financing_rechecks=()):
    """Research-only shortlist from exact-event or unique NCT source observations.

    No new qualification or investment rank is assigned. Records with two
    independently verified transactions still require exact Phase 3 and
    financing-sequence adjudication. Duplicate audit IDs never cross-link.
    """
    clinical = _unique(
        ({"Exact event": r.get("event_key"), **r} for r in clinical_rechecks), None
    )
    finance = _unique(
        ({"Exact event": r.get("event_key"), **r} for r in financing_rechecks), None
    )
    result = []
    for row in master_rows:
        key = program_key(row)
        if not key:
            continue
        checks = checklist_map.get(key, {})
        p3 = checks.get("phase3_data", {})
        fin = checks.get("financing_lead", {})
        p3_lead = p3.get("checked") is True or p3.get("observed") is True
        fin_lead = fin.get("checked") is True or fin.get("observed") is True
        if not (p3_lead or fin_lead):
            continue
        c = clinical.get(key, {})
        f = finance.get(key, {})
        secs = sum(f.get(column) == "VERIFIED" for column in (
            "first_sec_status", "second_sec_status"
        ))
        group = ("Both research leads" if p3_lead and fin_lead else
                 "Financing lead — Phase 3 review" if fin_lead else
                 "Phase 3 lead — financing review")
        state = (
            "PHASE 3 VERIFIED — FINANCING OPTIONAL" if row.get("_eligible") is True else
            "RESEARCH ONLY — NOT GEM ELIGIBLE"
        )
        result.append({
            "Ticker": row.get("Ticker"),
            "Drug": row.get("Drug"),
            "Indication": row.get("Indication"),
            "GEM research group": group,
            "Phase 3 data observed": bool(p3_lead),
            "Financing lead observed": bool(fin_lead),
            "Fresh SEC transactions verified": secs,
            "Phase 3 benchmark verified": checks.get("phase3_verified", {}).get("checked") is True,
            "Second financing benchmark verified": checks.get("financing_verified", {}).get("checked") is True,
            "Status": state,
            "Phase 3 missing": checks.get("phase3_verified", {}).get("detail", "Not verified"),
            "Financing missing": checks.get("financing_verified", {}).get("detail", "Not verified"),
            "Latest clinical review": c.get("source_recheck_status", "NOT RUN / NO MATCH"),
            "Latest SEC review": f.get("recheck_status", "NOT RUN / NO MATCH"),
            "NCT ID": row.get("NCT ID"),
            "PDUFA Date": row.get("PDUFA Date"),
            "Phase 3 Source": row.get("Phase 3 Source"),
            "Financing Source": row.get("Financing Source") or f.get("second_sec_url"),
            "Exact Program / Event": row.get("Exact Program / Event"),
            "_event_id": key,
            "_sort": (
                0 if p3_lead and fin_lead else 1 if fin_lead else 2,
                -secs,
                str(row.get("Ticker") or ""),
                str(row.get("Exact Program / Event") or ""),
            ),
        })
    result.sort(key=lambda item: item["_sort"])
    for item in result:
        item.pop("_sort", None)
    return result
