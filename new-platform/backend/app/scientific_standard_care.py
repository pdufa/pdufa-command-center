"""Level 10 dated disease/standard-of-care context comparison, not a care guideline.

Source review must already have passed the scientific evidence contract. This
check only compares declared disease, subtype, treatment setting, and geography
against an as-of guideline date. It does not establish treatment appropriateness.
"""
from __future__ import annotations

from datetime import date
import re

VERSION = "scientific-standard-care-context-v1"
_KEYS = ("disease", "subtype", "setting", "region")


def _context(record, kind, cutoff):
    if not isinstance(record, dict):
        return None, "MISSING_MEASUREMENTS"
    result = {}
    for key in _KEYS:
        value = record.get(key)
        if not isinstance(value, str) or not 0 < len(value.strip()) <= 400:
            return None, "INVALID_CONTEXT"
        result[key] = value.strip()
    if kind == "guideline":
        label = record.get("guidelineName")
        raw_date = record.get("guidelineEffectiveDate")
        if not isinstance(label, str) or not 0 < len(label.strip()) <= 400:
            return None, "MISSING_GUIDELINE_NAME"
        if not isinstance(raw_date, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", raw_date) is None:
            return None, "INVALID_GUIDELINE_EFFECTIVE_DATE"
        try:
            effective = date.fromisoformat(raw_date)
            upper = date.fromisoformat(cutoff)
        except (ValueError, TypeError):
            return None, "INVALID_GUIDELINE_EFFECTIVE_DATE"
        if effective > upper:
            return None, "GUIDELINE_POSTDATES_ASSESSMENT"
        result["guidelineName"] = label.strip()
        result["guidelineEffectiveDate"] = raw_date
    else:
        comparator = record.get("comparatorName")
        if not isinstance(comparator, str) or not 0 < len(comparator.strip()) <= 400:
            return None, "MISSING_COMPARATOR_NAME"
        result["comparatorName"] = comparator.strip()
    return result, None


def compare_standard_care(level_ten, evidence, assessment_cutoff):
    result = {
        "methodVersion": VERSION,
        "status": "NOT_ASSESSED",
        "score": None,
        "fdaPrediction": "ABSTAIN",
        "scientificValidation": "NOT_VERIFIED",
        "comparatorClinicallyAppropriate": None,
        "guidelineCurrent": None,
        "limitations": [
            "Context matching does not establish that a guideline is authoritative, current or applicable.",
            "Source dates and review receipts are not a substitute for indication-specific clinical interpretation.",
            "No guideline-derived clinical outcome, FDA decision, approval probability or composite rating is inferred.",
        ],
    }
    if not isinstance(level_ten, dict) or not isinstance(evidence, dict):
        return {**result, "reason": "Reviewed guideline and comparator evidence required."}
    accepted = level_ten.get("acceptedEvidence")
    if not isinstance(accepted, dict):
        return {**result, "reason": "Source-review contract unavailable."}
    receipts = {}
    for name in ("datedGuidelines", "standardOfCare"):
        record = accepted.get(name)
        if (not isinstance(record, dict) or record.get("sourceVerified") is not True
                or record.get("retrievalProvenance") != "RECORDED"):
            return {**result, "reason": "Dated guideline and standard-of-care sources require accepted retrieval provenance."}
        receipts[name] = {
            "nctId": record["nctId"], "source": record["source"],
            "sourceDate": record["sourceDate"],
            "sourceRetrievedAt": record["sourceRetrievedAt"],
            "reviewedAt": record["reviewedAt"],
        }
    guideline, err1 = _context((evidence.get("10.datedGuidelines") or {}).get("measurements"), "guideline", assessment_cutoff)
    standard, err2 = _context((evidence.get("10.standardOfCare") or {}).get("measurements"), "standard", assessment_cutoff)
    if err1 or err2:
        return {**result, "status": "REJECTED_MEASUREMENTS",
                "reason": err1 or err2}
    matches = {}
    mismatches = []
    for key in _KEYS:
        same = guideline[key].casefold() == standard[key].casefold()
        matches[key] = {
            "state": "MATCH" if same else "DIFFERENT",
            "guideline": guideline[key], "standardOfCare": standard[key],
        }
        if not same:
            mismatches.append(key)
    applicability = accepted.get("comparatorApplicability")
    applicability_reviewed = (
        isinstance(applicability, dict)
        and applicability.get("sourceVerified") is True
        and applicability.get("retrievalProvenance") == "RECORDED")
    return {
        **result,
        "status": ("CONTEXT_DIFFERENCE_REQUIRES_REVIEW" if mismatches
                   else "CONTEXT_MATCH_REQUIRES_CLINICAL_REVIEW"),
        "reason": "Structural context comparison only; source-based suitability is unresolved.",
        "guidelineName": guideline["guidelineName"],
        "guidelineEffectiveDate": guideline["guidelineEffectiveDate"],
        "comparatorName": standard["comparatorName"],
        "contextChecks": matches,
        "contextDifferences": mismatches,
        "applicabilityEvidenceReviewed": applicability_reviewed,
        "sourceProvenance": receipts,
    }
