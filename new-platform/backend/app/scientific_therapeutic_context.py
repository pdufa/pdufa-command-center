"""Level 11 descriptive population burden and alternatives context.

Only source-reviewed counts with exact population denominators are converted to
a descriptive rate per 100,000. The rate does not establish prevalence in the
wider population, market size, unmet need, clinical efficacy or FDA approval.
"""
from __future__ import annotations
from datetime import date
import re

VERSION = "scientific-therapeutic-context-v1"
_MAX = 2 ** 53 - 1
_CONTEXT = ("disease", "subtype", "region", "population", "measurementPeriod")


def _context(value):
    if not isinstance(value, dict):
        return None
    record = {}
    for key in _CONTEXT:
        field = value.get(key)
        if not isinstance(field, str) or not 0 < len(field.strip()) <= 400:
            return None
        record[key] = field.strip()
    return record


def therapeutic_context(level_eleven, evidence, assessment_cutoff):
    base = {
        "methodVersion": VERSION,
        "status": "NOT_ASSESSED",
        "scientificValidation": "NOT_VERIFIED",
        "fdaPrediction": "ABSTAIN",
        "score": None,
        "unmetNeedJudgment": None,
        "populationRepresentativeness": "NOT_ESTABLISHED",
        "limitations": [
            "A descriptive denominator-based rate is not a population prevalence estimate without sampling verification.",
            "Lack of reviewed alternatives is not proof that no treatment exists.",
            "No market-size inference, treatment recommendation, benefit-risk finding or FDA prediction.",
        ],
    }
    if not isinstance(level_eleven, dict) or not isinstance(evidence, dict):
        return {**base, "reason": "Review contract and dated evidence required."}
    accepted = level_eleven.get("acceptedEvidence")
    if not isinstance(accepted, dict):
        return {**base, "reason": "No accepted source-review records."}
    burden_receipt = accepted.get("populationBurden")
    if (not isinstance(burden_receipt, dict)
            or burden_receipt.get("sourceVerified") is not True
            or burden_receipt.get("retrievalProvenance") != "RECORDED"):
        return {**base, "reason": "Reviewed population burden source with retrieval receipt required."}
    record = evidence.get("11.populationBurden") or {}
    values = record.get("measurements") if isinstance(record, dict) else None
    context = _context(values)
    if context is None:
        return {**base, "status": "REJECTED_MEASUREMENTS",
                "reason": "Explicit disease, subtype, region, population and period required."}
    cases = values.get("cases")
    denominator = values.get("populationDenominator")
    if (type(cases) is not int or type(denominator) is not int
            or not 0 <= cases <= denominator <= _MAX or denominator == 0):
        return {**base, "status": "REJECTED_MEASUREMENTS",
                "reason": "Exact finite integer cases and positive population denominator required; booleans rejected."}
    raw_day = values.get("measurementAsOf")
    if not isinstance(raw_day, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", raw_day) is None:
        return {**base, "status": "REJECTED_MEASUREMENTS", "reason": "Strict measurement date required."}
    try:
        measurement_day = date.fromisoformat(raw_day)
        cutoff_day = date.fromisoformat(assessment_cutoff)
    except (ValueError, TypeError):
        return {**base, "status": "REJECTED_MEASUREMENTS", "reason": "Invalid measurement date or cutoff."}
    if measurement_day > cutoff_day:
        return {**base, "status": "REJECTED_MEASUREMENTS", "reason": "Population measurement postdates assessment."}
    burden = {
        "count": cases,
        "denominator": denominator,
        "reportedRatePer100k": round(cases * 100000 / denominator, 6),
        "measurementAsOf": raw_day,
        "population": context,
        "measurementType": "DESCRIPTIVE_CASES_PER_DECLARED_POPULATION",
        "sourceProvenance": {
            "nctId": burden_receipt["nctId"],
            "source": burden_receipt["source"],
            "sourceDate": burden_receipt["sourceDate"],
            "sourceRetrievedAt": burden_receipt["sourceRetrievedAt"],
            "reviewedAt": burden_receipt["reviewedAt"],
        },
    }
    result = {**base, "status": "DESCRIPTIVE_BURDEN_ONLY", "burden": burden,
              "alternativesContext": "NOT_ASSESSED"}
    alternative_receipt = accepted.get("availableAlternatives")
    if (not isinstance(alternative_receipt, dict)
            or alternative_receipt.get("sourceVerified") is not True
            or alternative_receipt.get("retrievalProvenance") != "RECORDED"):
        return result
    other = evidence.get("11.availableAlternatives") or {}
    alt = other.get("measurements") if isinstance(other, dict) else None
    alt_context = _context(alt)
    if alt_context is None or not isinstance(alt.get("namedAlternatives"), list):
        return {**result, "alternativesContext": "INVALID_CONTEXT_REQUIRES_REVIEW"}
    alternatives = alt["namedAlternatives"]
    if (len(alternatives) > 100 or any(not isinstance(a, str)
            or not 0 < len(a.strip()) <= 400 for a in alternatives)
            or len({a.strip().casefold() for a in alternatives}) != len(alternatives)):
        return {**result, "alternativesContext": "INVALID_ALTERNATIVES_REQUIRES_REVIEW"}
    differences = [key for key in _CONTEXT
                   if context[key].casefold() != alt_context[key].casefold()]
    return {
        **result,
        "status": "DESCRIPTIVE_BURDEN_AND_ALTERNATIVE_INVENTORY",
        "alternativesContext": "DECLARED_CONTEXT_MATCH" if not differences else "CONTEXT_MISMATCH_REQUIRES_REVIEW",
        "contextDifferences": differences,
        "reportedNamedAlternatives": [x.strip() for x in alternatives],
        "alternativesSource": alternative_receipt["source"],
        "note": "The treatment list is reviewed-source content only; even an empty list is not proof of no alternatives.",
    }
