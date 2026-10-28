"""Published KEYNOTE-024 interim design vs. reported results (source only).

The 2016 journal *describes* an interim testing plan; an FDA-staff-authored
paper *corroborates* the observed OS alpha comparison. Neither independently
authenticates the protocol/SAP signed before the May 9, 2016 data cutoff.
This is an archived historical trial, not PDUFA prediction or efficacy scoring.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

NCT_ID = "NCT02142738"
ORIGINAL_NEJM = "https://www.nejm.org/doi/abs/10.1056/NEJMoa1606774"
FDA_STAFF = "https://pmc.ncbi.nlm.nih.gov/articles/PMC5679831/"
SIGNED_PROTOCOL = "https://www.nejm.org/doi/full/10.1056/nejmoa1606774"

def published_keynote024_interim_design(
    published: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    """Require a verified pilot identity and a still-blocked original SAP."""
    if (not isinstance(published, Mapping) or not isinstance(readiness, Mapping)
        or published.get("nct_id") != NCT_ID
        or readiness.get("nctId") != NCT_ID
        or readiness.get("modelVersion") != "scientific-readiness-two-grade-v1"
        or readiness.get("inputReadiness", {}).get("grade") != "FAIL"
        or readiness.get("reluctance", {}).get("grade") != "HIGH"
        or readiness.get("scientificScore") is not None
        or readiness.get("fdaApprovalProbability") is not None
        or readiness.get("readOnly") is not True
        or readiness.get("tradingActionsEnabled") is not False):
        raise ValueError("Unverified or scored KEYNOTE-024 source review")
    checks = readiness.get("checks")
    if (not isinstance(checks, list) or len(checks) != 12
        or len([c for c in checks if isinstance(c, Mapping)
                and c.get("id") == "pre_cutoff_protocol"
                and c.get("status") == "BLOCKED" and c.get("critical") is True]) != 1):
        raise ValueError("Original 2016 SAP must remain blocked")
    source = readiness.get("original2016ProtocolSource")
    if (not isinstance(source, Mapping)
        or source.get("sourceUrl") != SIGNED_PROTOCOL
        or source.get("listingVerified") is not True
        or source.get("pdfContentReviewed") is not False
        or source.get("effectiveAmendmentsVerified") is not False
        or source.get("originalSignedSapVerified") is not False
        or source.get("preInterimAlphaSpendingVerified") is not False):
        raise ValueError("Original protocol supplement remains unreviewed")
    snapshots = published.get("analysis_snapshots")
    if not isinstance(snapshots, list) or len(snapshots) != 3:
        raise ValueError("Historical trial publications required")
    first = next((x for x in snapshots if isinstance(x, Mapping)
                  and x.get("analysis_id") == "keynote024_initial_2016"), None)
    if (not isinstance(first, Mapping)
        or first.get("source_id") != "27718847"
        or first.get("nct_id") != NCT_ID
        or first.get("data_cutoff_date") != "2016-05-09"
        or first.get("arm_counts_randomized") != {
            "pembrolizumab": 154, "chemotherapy": 151,
        }
        or published.get("randomized_population") != 305
        or published.get("overall_score") is not None
        or published.get("fda_approval_probability") is not None):
        raise ValueError("Published original trial identity mismatch")
    effects = first.get("effects")
    if not isinstance(effects, Mapping):
        raise ValueError("Published interim efficacy missing")
    pfs, os = effects.get("progression_free_survival"), effects.get("overall_survival")
    if (not isinstance(pfs, Mapping) or not isinstance(os, Mapping)
        or pfs.get("analysis_role") != "prespecified_primary"
        or pfs.get("hazard_ratio") != 0.50
        or pfs.get("hazard_ratio_95pct_ci") != [0.37, 0.68]
        or pfs.get("p_value") != "<0.001"
        or os.get("hazard_ratio") != 0.60
        or os.get("hazard_ratio_95pct_ci") != [0.41, 0.89]):
        raise ValueError("PFS/OS historical reports mismatched")

    return deepcopy({
        "nctId": NCT_ID,
        "status": "published_design_not_authenticated_original_sap",
        "sourceDateContext": {
            "originalInterimDataCutoff": "2016-05-09",
            "journalSourceUrl": ORIGINAL_NEJM,
            "journalLocator": "Methods/Statistical Analysis; Discussion",
            "fdaStaffSourceUrl": FDA_STAFF,
            "fdaStaffLocator": "KEYNOTE-024 summary efficacy table, footnote b",
            "originalSupplementSourceUrl": SIGNED_PROTOCOL,
            "originalSupplementFilename": "nejmoa1606774_protocol.pdf",
            "originalSupplementRead": False,
            "contemporaneousSapAuthenticated": False,
        },
        "reportedDesign": {
            "overallOneSidedAlphaPercent": 2.5,
            "firstInterim": {
                "plannedMinimumRandomized": 191,
                "plannedMinimumFollowupMonths": 6,
                "testingEndpoint": "objective_response_rate",
                "reportedAllocatedOneSidedAlphaPercent": 0.5,
                "sourceUrl": ORIGINAL_NEJM,
                "sourceLocator": "Discussion: first interim analysis",
                "prespecificationIndependentlyConfirmed": False,
            },
            "secondInterim": {
                "plannedApproximatePfsEvents": 175,
                "testingEndpoint": "progression_free_survival",
                "reportedAllocatedOneSidedAlphaPercent": 2.0,
                "sourceUrl": ORIGINAL_NEJM,
                "sourceLocator": "Discussion: second interim analysis",
                "prespecificationIndependentlyConfirmed": False,
            },
            "osGroupSequential": {
                "plannedApproximateDeaths": [110, 170],
                "sourceUrl": ORIGINAL_NEJM,
                "sourceLocator": "Discussion: group sequential overall survival analyses",
                "prespecificationIndependentlyConfirmed": False,
            },
            "descriptionPublishedAfterCutoff": True,
            "signedOriginalPlanAuthenticated": False,
        },
        "observedInterim": {
            "reportedPfsEvents": 189,
            "reportedDeaths": 108,
            "pfsHR": 0.50,
            "pfsCi95": [0.37, 0.68],
            "reportedPfsPValue": "<0.001",
            "osHR": 0.60,
            "osCi95": [0.41, 0.89],
            "reportedOsPValue": 0.005,
            "fdaStaffReportedOsAllocatedAlpha": 0.0118,
            "comparisonStatus": "source_reported_not_recalculated",
            "fdaStaffArticleIsNotFullAgencyClinicalReview": True,
        },
        "reconciliation": {
            "historicalResultsSourceChecked": True,
            "independentOriginalSAPReviewComplete": False,
            "alphaSpendingRecomputedFromSignedSAP": False,
            "patientLevelReanalysisComplete": False,
            "scientificConclusionAuthorized": False,
            "inputReadinessGradeChanged": False,
            "reluctanceGradeChanged": False,
            "missingCriticalSources": [
                "Original effective 2016-or-earlier protocol amendments",
                "Original signed and dated statistical analysis plan",
                "Complete interim decision/alpha-spending and censoring audit",
            ],
            "nextAction": "Obtain original supplement; authenticate version/effective date, then reconcile actual sequential thresholds and event timing.",
        },
        "scientificScore": None,
        "fdaApprovalProbability": None,
        "readOnly": True,
        "tradingActionsEnabled": False,
        "fsFaModified": False,
    })
