#!/usr/bin/env python3
"""Authoritative owner-only assessment governance from Levels 1 to 20.

This validates policies and produces requirements, NOT a clinical assessment.
No external source verifier, clinician, statistician, challenger, or
independent signature is required for the owner's own assessment. Automated
checks and owner review remain useful. No auth bypass or deployment happens.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "infra/assessment/sole-owner-levels1-20.json"
KIND = "PDUFA_OWNER_ONLY_ASSESSMENTS_LEVELS_1_TO_20"
OWNER_STATUSES = (
    "OWNER_NOT_REVIEWED", "OWNER_REVIEW_IN_PROGRESS",
    "OWNER_ACCEPTED_WITH_LIMITATIONS", "OWNER_REJECTED",
    "OWNER_NEEDS_EVIDENCE", "NOT_APPLICABLE_AT_THIS_PHASE",
)
OUTSIDE_GATES = (
    "externalMedicalReviewer", "externalStatisticalReviewer",
    "externalRegulatoryReviewer", "outsideSourceAttestor",
    "independentChallenger", "multiPersonAdjudication",
    "outsideReviewerCredentials", "externalSignoffBeforeAssessment",
    "externalSignoffBeforeScoring", "externalSignoffBeforePrediction",
    "externalSignoffBeforeOwnerPublication", "outsideClinicalCertification",
)
RETAINED_CHECKS = (
    "automatedSourceCitationAndExactNctChecks",
    "ownerMayManuallyCheckOriginalSources", "versionAndCutoffHistory",
    "phaseAndIndicationApplicability", "statisticalConsistencyChecks",
    "missingEvidenceAndContradictionsDisplayed",
    "outcomeExposureAndBacktestLeakageProtection",
    "dataSecurityOwnerSignInAndMfa", "regressionTestsAndReproducibility",
    "noFabricatedIndependentVerification",
    "noUncalibratedOrGuaranteedFdaProbabilities",
    "noClaimOfFdaOrExternalCertification",
    "existingProductionMergeAndDeployAuthorizationSeparate",
)
KEYS = {
    "schemaVersion", "kind", "ownerDirectiveDate", "activeMode",
    "scope", "humanRequirements", "retainedControls",
    "ownerStatusVocabulary", "legacyExternalWorkflow", "technicalStatus",
    "ownerOnlyReleaseRule", "historicalAccuracyRule", "note",
}


def validate(policy):
    if not isinstance(policy, dict) or set(policy) != KEYS:
        raise ValueError("Invalid owner-only Levels 1–20 governance schema")
    if (type(policy["schemaVersion"]) is not int or policy["schemaVersion"] != 1
            or policy["kind"] != KIND
            or policy["ownerDirectiveDate"] != "2026-11-13"
            or policy["activeMode"] != "SOLE_OWNER_AI_ASSISTED_ASSESSMENT"):
        raise ValueError("Owner-only policy identity, date or active mode changed")
    scope = policy["scope"]
    if not isinstance(scope, dict) or set(scope) != {
        "fromLevel", "toLevel", "activeTrialPopulations", "ownerHumanSeats",
        "levels1To6ImplementedResearchFramework",
        "levels7To20EngineeringComplete",
    }:
        raise ValueError("All 20 Levels must be within sole-owner policy")
    if (type(scope["fromLevel"]) is not int or scope["fromLevel"] != 1
            or type(scope["toLevel"]) is not int or scope["toLevel"] != 20
            or scope["activeTrialPopulations"] != ["POOL", "FOCUS"]
            or type(scope["ownerHumanSeats"]) is not int
            or scope["ownerHumanSeats"] != 1
            or scope["levels1To6ImplementedResearchFramework"] is not True
            or scope["levels7To20EngineeringComplete"] is not False):
        raise ValueError("Invalid sole-owner level scope or fabricated engineering status")
    human = policy["humanRequirements"]
    if not isinstance(human, dict) or set(human) != (
        set(OUTSIDE_GATES) | {"requiredHumanOperators", "ownerMayCheckAllEvidenceAndLevels"}
    ):
        raise ValueError("All external approval gates must be explicitly defined")
    if (any(human[k] is not False for k in OUTSIDE_GATES)
            or type(human["requiredHumanOperators"]) is not int
            or human["requiredHumanOperators"] != 1
            or human["ownerMayCheckAllEvidenceAndLevels"] is not True):
        raise ValueError("Owner alone may assess Levels 1–20, no outside approval")
    checks = policy["retainedControls"]
    if (not isinstance(checks, dict) or set(checks) != set(RETAINED_CHECKS)
            or any(checks[k] is not True for k in RETAINED_CHECKS)):
        raise ValueError("Removing external reviewers must not suppress internal evidence/security checks")
    statuses = policy["ownerStatusVocabulary"]
    if (not isinstance(statuses, dict)
            or set(statuses) != {
                "notReviewed", "inProgress", "acceptedWithLimitations",
                "ownerRejected", "needsEvidence", "notApplicable", "notIndependent"
            }
            or tuple(statuses[k] for k in (
                "notReviewed", "inProgress", "acceptedWithLimitations",
                "ownerRejected", "needsEvidence", "notApplicable",
            )) != OWNER_STATUSES
            or statuses["notIndependent"] != "OWNER_SELF_REVIEW_NO_EXTERNAL_CERTIFICATION"):
        raise ValueError("Owner self-review cannot be labeled independently approved")
    tech = policy["technicalStatus"]
    if (not isinstance(tech, dict)
            or set(tech) != {"levels1To6", "levels7To20", "externalReviewerGateCount",
                            "externallySignedAssessmentsRequired",
                            "ownerReviewsCompletedClaimed", "siteDeploymentAuthorized"}
            or tech["levels1To6"] != "PRELIMINARY_RESEARCH_WORKSHEETS_AVAILABLE_OWNER_REVIEW_NOT_AUTOMATICALLY_COMPLETE"
            or tech["levels7To20"] != "POLICY_APPLIES_NO_CLAIM_OF_COMPLETED_ENGINEERING"
            or any(type(tech[key]) is not int or tech[key] != 0 for key in (
                "externalReviewerGateCount", "externallySignedAssessmentsRequired",
                "ownerReviewsCompletedClaimed",
            ))
            or tech["siteDeploymentAuthorized"] is not False):
        raise ValueError("No fabricated reviewer approvals or completed implementation")
    if policy["legacyExternalWorkflow"] != (
        "RETIRED_FROM_ACTIVE_GATES_PRESERVED_ONLY_AS_DISABLED_HISTORICAL_ENGINEERING"
    ):
        raise ValueError("Legacy five-person review workflow cannot gate owner work")
    for k in ("ownerOnlyReleaseRule", "historicalAccuracyRule", "note"):
        if not isinstance(policy[k], str) or len(policy[k]) < 60:
            raise ValueError("Owner-release limits, outcome leakage and audit disclaimers required")
    return True


def requirements_for_level(policy, level):
    validate(policy)
    if type(level) is not int or not 1 <= level <= 20:
        raise ValueError("Owner-only requirements apply exactly to Levels 1–20")
    return {
        "level": level,
        "ownerCheckOnly": True,
        "outsidePeopleRequired": 0,
        "externalSignoffsRequired": 0,
        "independentCertificationRequired": False,
        "sourceChecks": "OWNER_AND_AUTOMATED_INTERNAL_ONLY",
        "assessmentMode": "OWNER_SELF_RESEARCH_NOT_INDEPENDENT",
        "reviewStatus": "OWNER_NOT_REVIEWED",
        "engineeringImplementedByThisPolicy": level <= 6,
        "noClaimOfCompletion": True,
        "note": "This removes outside review gates; it does not validate missing evidence or grant site access.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", type=int)
    args = parser.parse_args()
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    validate(policy)
    if args.level is not None:
        print(json.dumps(requirements_for_level(policy, args.level), indent=2))
    else:
        print(json.dumps({
            "kind": KIND, "activeMode": policy["activeMode"],
            "outsideReviewerOrSignoffGates": 0,
            "ownerOnly": True,
            "policyLevels": [requirements_for_level(policy, i) for i in range(1, 21)],
        }, indent=2))


if __name__ == "__main__":
    main()
