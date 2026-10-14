"""Transparent GEM umbrella benchmarks and optional research checkboxes.

Only the two existing source-attested events confer GEM ranking eligibility.
Everything else is a visible advisory observation, never an automatic gate.
A partial source observation is REVIEW (not a verified PASS).
"""
from __future__ import annotations

import math

from gem_master_list import PHASE3_OK, FINANCING_OK

BENCHMARKS = (
    ("phase3_verified", "1. Phase 3 RESULTS released — exact-program verified"),
    ("financing_verified", "2. SECOND financing CLOSED — distinct post-readout transactions"),
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
    phase3_lead = (
        phase3 or
        registry_status == "POSTED_RESULTS_DISCOVERY_ONLY"
        or p3_status.startswith((
            "VERIFIED SUCCESS", "REGISTRY RESULTS POSTED",
            "ISSUER ANNOUNCEMENT", "POTENTIAL ISSUER READOUT",
        ))
    )
    clinical_score = _num(src.get("Clinical evidence /30"))
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
        "clinical_quality": _state(phase3 and clinical_score == 30,
                                   "Full source-attested clinical evidence" if phase3 and clinical_score == 30 else
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


def filter_programs(rows, checklists, selected=()):
    """Optional checkbox filters only alter the VIEW, never program eligibility."""
    keys = set(selected)
    if not keys.issubset(FILTERABLE):
        raise ValueError("Unknown GEM checkbox filter")
    return [row for row in rows
            if all(
                (checklists.get(str(row.get("Exact Program / Event") or ""), {})
                 .get(key, {}).get("checked") is True)
                or (key in dict(UMBRELLA) and
                    checklists.get(str(row.get("Exact Program / Event") or ""), {})
                    .get(key, {}).get("observed") is True)
                for key in keys
            )]


def _unique(records, field):
    """Never attach one program's sources to a repeated or missing event key."""
    mapping, duplicates = {}, set()
    for item in records or ():
        key = str(item.get(field) or "").strip()
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
    master_by_event = _unique(master_rows, "Exact Program / Event")
    sources = _unique(saved_sources, "Exact event")
    finance = _unique(financing_rechecks, "event_key")
    clinical = _unique(clinical_rechecks, "event_key")
    return {
        key: build_checklist(
            master, sources.get(key),
            finance_audit=finance.get(key),
            clinical_audit=clinical.get(key),
            sec_current=sec_current, feed_current=feed_current,
        )
        for key, master in master_by_event.items()
    }
