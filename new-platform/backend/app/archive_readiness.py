"""Conservative, read-only evidence inventory for ClinicalTrials.gov v2 JSON.

These flags describe the presence of usable archive fields. They do not validate
the trial's scientific methods, identify a successful treatment, establish FDA
approval, predict a regulatory outcome, or make a record eligible for trading.
No network requests, database writes, or platform-list changes occur here.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any


READINESS_DEFINITIONS = {
    "phase3_or_4": "Design explicitly lists PHASE3 or PHASE4.",
    "fda_regulated_drug_or_biological": "isFdaRegulatedDrug is JSON true and a named DRUG or BIOLOGICAL intervention exists; registry assertion, not FDA approval.",
    "completed_primary_endpoints": "Primary completion is ACTUAL with a parseable date no later than the inventory date; month/year dates count only once their whole period has elapsed. Does not establish endpoint success.",
    "reported_efficacy_results": "At least one numeric reported outcome measurement has an explicit efficacy, response, remission, survival, disease progression, symptom improvement or clinical-benefit term. Conservative text screen requiring review, not proof of efficacy.",
    "reported_safety_results": "Numeric reported outcome with an explicit safety/adverse-event/toxicity term, or structured serious/other adverse-event counts including explicitly reported zero events.",
    "statistical_analyses": "At least one reported outcome analysis contains a statistical method or numeric estimate, interval, or p-value.",
    "reported_p_values": "At least one reported outcome analysis contains a syntactically numeric p-value from zero through one, optionally qualified by <, <=, >, >=, = or ~.",
    "adverse_event_information": "Structured serious or other adverse-event entries contain numeric numAffected, numAtRisk or numEvents data; empty modules do not count.",
    "sponsor_information": "Named lead sponsor is present.",
    "trial_completion_dates": "ACTUAL study completion date has elapsed as of inventory; planned dates do not count.",
    "identifiable_drug_or_biological_products": "At least one DRUG/BIOLOGICAL intervention has a non-placeholder name; trial intervention names are not verified marketed products.",
    "verifiable_regulatory_identifiers": "Externally verified regulatory identifiers; none are asserted by this archive-only inventory. FDA references are counted separately as candidates pending verification.",
    "regulatory_identifier_candidates": "An explicit IND, NDA, BLA or ANDA identifier is present in structured secondary-ID fields; candidates have not been verified against FDA sources.",
    "scientific_ready": "Evidence-screen candidate only: phase 3/4, explicit regulated drug/biologic, completed primary and trial dates, efficacy and safety reporting, analyses and p-values, named product and sponsor. Independent SCIENCE validation is still required.",
    "regulatory_outcome_evidence": "Externally verified regulatory outcome evidence; none is inferred from ClinicalTrials.gov completion, phase, expanded access, or FDA regulation flags.",
}
INVENTORY_FLAGS = tuple(READINESS_DEFINITIONS)

_EFFICACY = re.compile(
    r"\b(?:efficacy|clinical benefit|overall survival|progression.free survival|"
    r"disease.free survival|event.free survival|objective response|response rate|"
    r"complete response|partial response|remission|disease progression|"
    r"symptom improvement|symptom reduction)\b", re.IGNORECASE,
)
_SAFETY = re.compile(r"\b(?:safety|adverse events?|toxicit(?:y|ies)|tolerability|dose.limiting)\b", re.IGNORECASE)
_REGULATORY = re.compile(r"\b(?:IND|NDA|BLA|ANDA)\s*(?:NO\.?|NUMBER|#|:|-)?\s*\d{3,8}\b", re.IGNORECASE)
_P_VALUE = re.compile(r"\s*(?:<=|>=|<|>|=|~)?\s*(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\s*\Z")
_PLACEHOLDERS = {"", "unknown", "not available", "not specified", "n/a", "na", "tbd", "none"}


def _obj(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _rows(value: Any) -> list[dict]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _named(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() not in _PLACEHOLDERS


def _numeric(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        number = float(value)
        return number == number and number not in (float("inf"), float("-inf"))
    except (TypeError, ValueError):
        return False


def _p_value(value: Any) -> bool:
    if isinstance(value, bool) or not _P_VALUE.fullmatch(str(value)):
        return False
    numeric = re.sub(r"^\s*(?:<=|>=|<|>|=|~)?\s*", "", str(value))
    return 0 <= float(numeric) <= 1


def _actual_elapsed(value: Any, today: date) -> bool:
    item = _obj(value)
    if item.get("type") != "ACTUAL" or not isinstance(item.get("date"), str):
        return False
    text = item["date"]
    try:
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
            last = date.fromisoformat(text)
        elif re.fullmatch(r"[0-9]{4}-[0-9]{2}", text):
            import calendar
            year, month = map(int, text.split("-"))
            last = date(year, month, calendar.monthrange(year, month)[1])
        elif re.fullmatch(r"[0-9]{4}", text):
            last = date(int(text), 12, 31)
        else:
            return False
        return last <= today
    except (ValueError, OverflowError):
        return False


def _has_measurements(outcome: dict) -> bool:
    return any(_numeric(measurement.get("value"))
               for cls in _rows(outcome.get("classes"))
               for category in _rows(cls.get("categories"))
               for measurement in _rows(category.get("measurements")))


def _has_adverse_events(module: dict) -> bool:
    return any(_numeric(stat.get(key))
               for kind in ("seriousEvents", "otherEvents")
               for event in _rows(module.get(kind))
               for stat in _rows(event.get("stats"))
               for key in ("numAffected", "numAtRisk", "numEvents"))


def study_readiness(study: dict, *, today: date | None = None) -> dict[str, bool]:
    """Return evidence-presence flags, accepting absent/malformed modules safely."""
    today = today or datetime.now(timezone.utc).date()
    protocol = _obj(_obj(study).get("protocolSection"))
    results = _obj(_obj(study).get("resultsSection"))
    design = _obj(protocol.get("designModule"))
    phases = design.get("phases") if isinstance(design.get("phases"), list) else []
    status = _obj(protocol.get("statusModule"))
    identification = _obj(protocol.get("identificationModule"))
    interventions = _rows(_obj(protocol.get("armsInterventionsModule")).get("interventions"))
    outcomes = _rows(_obj(results.get("outcomeMeasuresModule")).get("outcomeMeasures"))
    analyses = [analysis for outcome in outcomes for analysis in _rows(outcome.get("analyses"))]
    reported = [outcome for outcome in outcomes if _has_measurements(outcome)]
    adverse = _has_adverse_events(_obj(results.get("adverseEventsModule")))
    product = any(item.get("type") in ("DRUG", "BIOLOGICAL") and _named(item.get("name"))
                  for item in interventions)
    flags = {
        "phase3_or_4": any(phase in ("PHASE3", "PHASE4") for phase in phases),
        "fda_regulated_drug_or_biological": product and _obj(protocol.get("oversightModule")).get("isFdaRegulatedDrug") is True,
        "completed_primary_endpoints": _actual_elapsed(status.get("primaryCompletionDateStruct"), today),
        "reported_efficacy_results": any(_EFFICACY.search(str(item.get("title", "")) + " " + str(item.get("description", ""))) is not None for item in reported),
        "reported_safety_results": adverse or any(_SAFETY.search(str(item.get("title", "")) + " " + str(item.get("description", ""))) is not None for item in reported),
        "statistical_analyses": any(_named(item.get("statisticalMethod")) or any(_numeric(item.get(key)) for key in ("paramValue", "ciLowerLimit", "ciUpperLimit")) or _p_value(item.get("pValue")) for item in analyses),
        "reported_p_values": any(_p_value(item.get("pValue")) for item in analyses),
        "adverse_event_information": adverse,
        "sponsor_information": _named(_obj(_obj(protocol.get("sponsorCollaboratorsModule")).get("leadSponsor")).get("name")),
        "trial_completion_dates": _actual_elapsed(status.get("completionDateStruct"), today),
        "identifiable_drug_or_biological_products": product,
        "verifiable_regulatory_identifiers": False,
        "regulatory_identifier_candidates": any(_REGULATORY.search(" ".join(str(item.get(key, "")) for key in ("id", "type", "domain"))) is not None for item in _rows(identification.get("secondaryIdInfos"))),
        "regulatory_outcome_evidence": False,
    }
    flags["scientific_ready"] = all(flags[key] for key in (
        "phase3_or_4", "fda_regulated_drug_or_biological", "completed_primary_endpoints",
        "reported_efficacy_results", "reported_safety_results", "statistical_analyses",
        "reported_p_values", "sponsor_information", "trial_completion_dates",
        "identifiable_drug_or_biological_products",
    ))
    return {key: flags[key] for key in INVENTORY_FLAGS}
