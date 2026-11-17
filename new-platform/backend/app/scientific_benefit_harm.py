"""Level 9 descriptive benefit/harm alignment; not a clinical benefit-risk decision.

Comparability checks are performed ONLY after the source-review contract accepts
both exact-trial records with dated retrieval provenance. Matching arm names
and follow-up windows cannot establish treatment benefit, causality or safety.
"""
from __future__ import annotations

VERSION = "scientific-benefit-harm-alignment-v1"
_FIELDS = ("population", "treatmentArm", "comparatorArm", "timeOrigin")


def _measurement(record):
    if not isinstance(record, dict):
        return None
    item = {}
    for key in _FIELDS + ("endpoint",):
        val = record.get(key)
        if not isinstance(val, str) or not 0 < len(val.strip()) <= 400:
            return None
        item[key] = val.strip()
    days = record.get("followupDays")
    if type(days) is not int or not 0 < days <= 36525:
        return None
    item["followupDays"] = days
    return item


def align_benefit_harm(level_nine, evidence):
    """Compare reported study context only; refuse inferred benefit-risk verdicts."""
    abstain = {
        "methodVersion": VERSION,
        "status": "NOT_ASSESSED",
        "scientificValidation": "NOT_VERIFIED",
        "fdaPrediction": "ABSTAIN",
        "clinicalBenefitRiskConclusion": None,
        "score": None,
        "limitations": [
            "Matching study context does not prove efficacy or safety.",
            "Benefit and harm endpoints are not numerically pooled or weighted.",
            "No causality, clinical meaningfulness, FDA decision, probability or treatment recommendation is inferred.",
        ],
    }
    if not isinstance(level_nine, dict) or not isinstance(evidence, dict):
        return {**abstain, "reason": "A reviewed level and both source records are required."}
    accepted = level_nine.get("acceptedEvidence")
    if not isinstance(accepted, dict):
        return {**abstain, "reason": "Both source records must pass the exact-trial review contract."}
    provenance = {}
    for criterion in ("benefitEvidence", "harmEvidence"):
        receipt = accepted.get(criterion)
        if (not isinstance(receipt, dict)
                or receipt.get("sourceVerified") is not True
                or receipt.get("retrievalProvenance") != "RECORDED"):
            return {**abstain, "reason": "Both source-reviewed criteria need valid dated retrieval receipts."}
        provenance[criterion] = {
            "nctId": receipt["nctId"],
            "source": receipt["source"],
            "sourceDate": receipt["sourceDate"],
            "sourceRetrievedAt": receipt["sourceRetrievedAt"],
            "reviewedAt": receipt["reviewedAt"],
        }
    benefit = _measurement((evidence.get("9.benefitEvidence") or {}).get("measurements"))
    harm = _measurement((evidence.get("9.harmEvidence") or {}).get("measurements"))
    if benefit is None or harm is None:
        return {
            **abstain,
            "status": "REJECTED_MEASUREMENTS",
            "reason": "Explicit endpoint, study population, arms, time origin and 1–36525 follow-up days required for both reviewed records.",
        }
    checks = {}
    differences = []
    for key in (*_FIELDS, "followupDays"):
        first, second = benefit[key], harm[key]
        equal = first == second if key == "followupDays" else first.casefold() == second.casefold()
        checks[key] = {"state": "MATCH" if equal else "DIFFERENT", "benefit": first, "harm": second}
        if not equal:
            differences.append(key)
    return {
        **abstain,
        "status": "DESCRIPTIVE_CONTEXT_ALIGNMENT_ONLY" if not differences else "CONTEXT_DIFFERENCES_REQUIRE_OWNER_REVIEW",
        "reason": "Comparison of metadata only; no efficacy or safety conclusion.",
        "benefitEndpoint": benefit["endpoint"],
        "harmEndpoint": harm["endpoint"],
        "checks": checks,
        "differences": differences,
        "sourceProvenance": provenance,
        "comparability": "SAME_DECLARED_CONTEXT" if not differences else "NOT_ESTABLISHED",
    }
