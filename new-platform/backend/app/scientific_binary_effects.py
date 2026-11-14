"""Transparent binary event contrasts from source-reviewed, exact-trial counts.

Rates and differences are descriptive arithmetic, not clinical judgments or FDA
probabilities. No confidence interval, pooled effect, continuity correction or
statistical independence assumption is manufactured.
"""
from __future__ import annotations

VERSION = "reviewed-binary-event-contrast-v1"


def binary_effect(record):
    measurements = record.get("measurements")
    unavailable = {"status": "NOT_ASSESSED", "methodVersion": VERSION,
                   "reason": "Requires reviewed binary counts, population, endpoint, time frame and retrieval provenance."}
    if (record.get("retrievalProvenance") != "RECORDED" or not isinstance(measurements, dict)
            or measurements.get("outcomeType") != "BINARY_EVENT"):
        return unavailable
    for key in ("endpoint", "population", "timeFrame"):
        if not isinstance(measurements.get(key), str) or not measurements[key].strip():
            return unavailable
    arms = []
    for key in ("treatment", "comparator"):
        arm = measurements.get(key)
        if not isinstance(arm, dict) or not isinstance(arm.get("label"), str) or not arm["label"].strip():
            return unavailable
        events, total = arm.get("events"), arm.get("total")
        if type(events) is not int or type(total) is not int or not 0 <= events <= total or total <= 0:
            return {**unavailable, "status": "REJECTED_MEASUREMENTS", "reason": "Invalid binary event numerator or denominator."}
        arms.append({"label": arm["label"], "events": events, "total": total, "eventRate": events / total})
    treatment, comparator = arms
    if treatment["label"] == comparator["label"]:
        return {**unavailable, "status": "REJECTED_MEASUREMENTS", "reason": "Distinct comparison groups required."}
    control_rate = comparator["eventRate"]
    return {
        "status": "DESCRIPTIVE_CALCULATION_NOT_VALIDATED_ASSESSMENT", "methodVersion": VERSION,
        **{key: measurements[key] for key in ("endpoint", "population", "timeFrame")},
        "treatment": treatment, "comparator": comparator,
        "absoluteRiskDifference": treatment["eventRate"] - control_rate,
        "riskRatio": treatment["eventRate"] / control_rate if control_rate else None,
        "riskRatioStatus": "DEFINED" if control_rate else "UNDEFINED_ZERO_COMPARATOR_EVENTS",
        "confidenceInterval": None, "clinicalSignificance": "NOT_ASSESSED",
        "scientificValidation": "NOT_VERIFIED", "fdaPrediction": "ABSTAIN",
        "provenance": {key: record[key] for key in (
            "nctId", "source", "sourceDate", "sourceRetrievedAt", "sourceVerifiedAt",
            "sourceVerifiedBy", "sourceVerificationMethod", "reviewerId", "reviewedAt",
            "rationale", "evidenceExcerpt", "documentType")},
        "limitations": ["Counts require owner source review; this calculation does not authenticate the source.",
                        "Same endpoint, analysis population and observation window must apply to both arms.",
                        "No multiplicity, missing-data, causal, exposure-adjusted or benefit-risk conclusion inferred.",
                        "A numerical event contrast is not an FDA outcome probability."],
    }
