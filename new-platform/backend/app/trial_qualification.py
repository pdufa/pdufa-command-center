"""Saved-evidence facts for Pipeline filters; no eligibility or ledger writes.

Financing stays attached to an exact regulatory event. It is never copied to
another trial because it shares an issuer. Unknown evidence stays unknown.
Historical closing attestations do not assert a fresh SEC check or trade entry.
"""
from __future__ import annotations

from datetime import date
import re
from urllib.parse import urlparse

POSITIVE = {"PRIMARY_MET_VERIFIED", "VERIFIED_SUCCESS"}
NEGATIVE = {"VERIFIED_FAILURE", "PRIMARY_FAILED_VERIFIED", "VERIFIED_NEGATIVE"}
FINANCE_PASS = "VERIFIED_SECOND_POST_PHASE3_FINANCING"


def text(value):
    return str(value or "").strip()


def day(value):
    try:
        return date.fromisoformat(text(value)[:10])
    except ValueError:
        return None


def public_url(value, *, sec=False):
    try:
        url = urlparse(text(value))
        return bool(url.scheme == "https" and url.hostname and not url.username
                    and (not sec or (url.hostname in {"sec.gov", "www.sec.gov"}
                                     and url.path.startswith("/Archives/edgar/data/"))))
    except ValueError:
        return False


def flag(value):
    value = text(value).upper()
    if value in {"YES", "TRUE", "1", "ACTIVE", "UNRESOLVED", "FLAGGED"}:
        return "FLAGGED"
    if value in {"NO", "NONE", "FALSE", "0", "CLEAR", "PASS"}:
        return "CLEAR"
    return "UNKNOWN"


def _ncts(value):
    return set(re.findall(r"\bNCT\d{8}\b", text(value).upper()))


def attach_trial_filter_facts(candidates, originals, funding, rechecks, runway,
                            membership, today: date):
    """Enrich the existing unique Pipeline records without changing identity/counts."""
    registry_phases = {}
    for key, source in originals.items():
        if key.startswith("TRIAL|"):
            nct = text(source.get("nct_id"))
            phase = text(source.get("registeredPhase"))
            if nct and phase and phase != "Unknown":
                registry_phases.setdefault((text(source.get("ticker")).upper(), nct), set()).add(phase)
    lists = {}
    from .legacy_gem_runway_gate import assess_runway
    cash_facts = {ticker: assess_runway(ticker, item, as_of=today)
                  for ticker, item in runway.items()}
    for stage in ("GEM_JR", "GEM"):
        for key, entry in membership.get("stages", {}).get(stage, {}).get("entries", {}).items():
            if key == entry.get("pipeline_id"):
                label = stage if entry.get("status") == "ACTIVE" else "HISTORICAL"
                lists.setdefault(key, set()).add(label)

    for candidate in candidates:
        key = candidate["id"]
        source = originals[key]
        ticker = text(source.get("ticker")).upper()
        event = text(source.get("event_key"))
        # A trial's incidental event_key is not a regulatory event identity.
        exact_event = bool(event and key == "APPLICATION|" + event
                           and event.startswith(ticker + "|"))
        finance = funding.get(event, {}) if exact_event else {}
        recheck = rechecks.get(event, {}) if exact_event else {}
        phase = text(source.get("registeredPhase"))
        if not phase or phase == "Unknown":
            phases = set()
            for nct in _ncts(source.get("nct_id")):
                phases.update(registry_phases.get((ticker, nct), set()))
            phase = next(iter(phases)) if len(phases) == 1 else "Unknown"

        status = text(source.get("phase3_status")).upper()
        # A generic REVIEW/UNKNOWN source flag is not evidence that an
        # independently verified endpoint failed. Explicit conflicts remain
        # filterable; they are never inferred from an absent clearance.
        clinical_conflict = flag(source.get("clinical_conflict_flag", source.get("conflict_flag"))) == "FLAGGED"
        readout = day(source.get("phase3_date"))
        readout_linked = bool(readout and readout <= today and
                              public_url(source.get("trial_evidence_url")))
        successful = bool(readout_linked and status in POSITIVE and not clinical_conflict
                          and _ncts(source.get("nct_id")) and phase in {"Phase 3", "Unknown"})
        primary = ("SUCCESS" if successful else "FAILED" if readout_linked and status in NEGATIVE
                   else "REVIEW" if status and status not in {"UNVERIFIED", "NOT VERIFIED"}
                   else "UNKNOWN")
        posted = day(source.get("results_posted"))
        registry_release = bool(phase == "Phase 3" and posted and posted <= today
                                and public_url(source.get("source_url")))
        release = readout if readout_linked else posted if registry_release else None
        first, second = day(finance.get("first_financing_date")), day(finance.get("second_financing_date"))
        audited = text(finance.get("second_financing_audit_status")) == FINANCE_PASS
        first_source, second_source = (text(finance.get(name)) for name in
                                      ("first_financing_source", "second_financing_source"))
        chronology = bool(readout_linked and first and second and readout <= first < second <= today)
        finance_checked = day(finance.get("verified_as_of"))
        reviewed = bool(finance_checked and finance_checked <= today)
        first_cik = re.search(r"/Archives/edgar/data/(\d+)/", first_source)
        second_cik = re.search(r"/Archives/edgar/data/(\d+)/", second_source)
        same_issuer = bool(first_cik and second_cik and int(first_cik[1]) == int(second_cik[1]))
        distinct = bool(chronology and audited and reviewed and same_issuer and public_url(first_source, sec=True)
                        and public_url(second_source, sec=True) and first_source != second_source
                        and text(finance.get("second_financing_status")).upper() in {"CLOSED", "FINISHED"}
                        and text(finance.get("second_financing_closed")).upper() == "YES")
        first_closed = bool(readout_linked and first and readout <= first <= today
                            and public_url(first_source, sec=True)
                            and ((audited and reviewed) or recheck.get("first_sec_status") == "VERIFIED"))
        # Reuse the source-checked SEC cash-only assessment. Never invent a
        # runway from a company cash headline or a conditional future raise.
        months = cash_facts.get(ticker, {}).get("Cash runway (months)")
        checked = day(source.get("checked_at") or source.get("last_checked"))
        evidence = set()
        if successful or (readout_linked and status in NEGATIVE) or distinct:
            evidence.add("VERIFIED")
        elif public_url(source.get("source_url")):
            evidence.add("SOURCE_RECORDED")
        if not public_url(source.get("source_url")) and not readout_linked:
            evidence.add("MISSING")
        if primary in {"REVIEW", "UNKNOWN"} or (finance and not distinct):
            evidence.add("REVIEW")
        if clinical_conflict:
            evidence.add("CONFLICTING")
        if (checked and (today - checked).days > 7) or (finance_checked and (today - finance_checked).days > 7):
            evidence.add("STALE")
        if not checked:
            evidence.add("MISSING")
        milestones = set(source.get("stageTags") or [])
        if day(source.get("nda_submission_date")) and day(source.get("nda_submission_date")) <= today:
            milestones.add("NDA/BLA Submission")
        if day(source.get("fda_acceptance_date")) and day(source.get("fda_acceptance_date")) <= today:
            milestones.add("FDA Acceptance")
        own_lists = {"PIPELINE", *lists.get(key, set())}
        if source.get("stage") == "Post-Decision":
            own_lists.add("HISTORICAL")
        candidate["trialFilters"] = {
            "registeredPhase": phase,
            "trialStatus": text(source.get("status")) or "UNKNOWN",
            "resultsReleased": bool((readout_linked and (phase == "Phase 3" or status in POSITIVE | NEGATIVE)) or registry_release),
            "resultsDate": release.isoformat() if release else "",
            "primaryOutcome": primary,
            "safety": flag(source.get("new_safety_flag")),
            "firstFinancingClosed": first_closed,
            "secondFinancingClosed": distinct,
            "firstClose": first.isoformat() if first_closed else "",
            "secondClose": second.isoformat() if distinct else "",
            "independentFinancings": "VERIFIED" if distinct else "REVIEW" if finance else "UNKNOWN",
            "milestones": sorted(milestones),
            "outcome": text(source.get("outcome")).upper() or "UNKNOWN",
            "runwayMonths": months,
            "dilution": flag(source.get("new_dilution_flag")),
            "evidence": sorted(evidence),
            "lists": sorted(own_lists),
        }
