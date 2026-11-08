"""Versioned scientific review requirements, never an automatic scoring rule.

Anchors describe support for an assessment's stated scientific criterion,
not treatment success, FDA outcome probability, or reviewer authorization.
Existing events are not retroactively certified against this policy.
"""
from copy import deepcopy

_POLICY = {
    "version": "SCIENTIFIC_REVIEW_REQUIREMENTS_V1",
    "status": "DEFINED_PENDING_AUTHORIZED_CLINICAL_VALIDATION",
    "gradeMeaning": "Support for the stated scientific criterion after independent evidence examination",
    "anchors": [
        {"grade": 0, "meaning": "Examined evidence does not support the criterion; document the adverse finding and limitations"},
        {"grade": 1, "meaning": "Very weak support; major methodological limitations or unresolved contradictions"},
        {"grade": 2, "meaning": "Limited support; material uncertainty restricts the conclusion"},
        {"grade": 3, "meaning": "Moderate support; important limitations remain and are explicitly bounded"},
        {"grade": 4, "meaning": "Strong support from appropriate primary evidence and independent verification"},
        {"grade": 5, "meaning": "Robust support with corroboration and scientific challenge; no material unresolved contradiction for this criterion"},
    ],
    "requiredReviewRecord": [
        "exact NCT and current verified phase-event identity",
        "assessment and method identity with phase-specific applicability rationale",
        "original source URL, publication/version date, retrieval date and content digest",
        "examined findings with source locations and methodological limitations",
        "separate favorable, unfavorable, missing and contradictory evidence classifications",
        "independent source verification and named authorized reviewer attestation",
        "review rationale, review date and explicit superseded event for each revision",
    ],
    "evidenceClassifications": ["FAVORABLE", "UNFAVORABLE", "MISSING", "CONTRADICTORY"],
    "missingEvidencePolicy": "Missing or unexamined evidence has no numerical grade; an absent future-phase result is not a failed current-phase assessment",
    "normalization": {
        "formula": "20 * arithmetic mean of current phase-matched independently graded methods",
        "range": [0, 100],
        "provisional": "At least one graded method with applicable methods still pending",
        "complete": "Every applicable method independently reviewed; exclusions require a recorded applicability rationale",
        "allExcluded": "NOT_APPLICABLE with no numerical grade",
        "excludedFromDenominator": ["NOT_APPLICABLE"],
        "pendingNeverZeroFilled": ["UNREVIEWED", "VERIFY_PHASE", "STALE_PHASE", "RETRACTED", "MISSING"],
    },
    "revisionPolicy": "Append only; retain prior sources, phases, findings, grades and supersession links. A new phase event requires fresh review",
    "freshnessPolicy": "A retrieval date establishes receipt time only. Source changes, phase changes and new contradictory evidence require re-review; no clinical expiry threshold is validated here",
    "independencePolicy": "Multiple URLs or a sponsor publication plus its press release do not establish independent corroboration; record source provenance and conflicts",
    "automaticGradingEnabled": False,
    "historicalEventsCertifiedAgainstPolicy": False,
    "clinicalSignoff": False,
    "fdaPredictions": {"APPROVAL": "ABSTAIN", "CRL": "ABSTAIN", "REVIEW_DELAY": "ABSTAIN"},
    "certainty": "NOT_VALIDATED",
}


def grading_policy() -> dict:
    """Read-only disclosure. It neither assigns nor certifies existing grades."""
    return deepcopy(_POLICY)
