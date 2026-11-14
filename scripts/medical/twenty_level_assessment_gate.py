#!/usr/bin/env python3
"""Fail-closed OWNER-ONLY acceptance gate for scientific Levels 1–20.

No outside source verifier, reviewer, challenger or independent signoff is
required. The owner checks a source-cited decision and records their status.
A structurally accepted package is not FDA certification or proven accuracy.
"""
import argparse
import json
from pathlib import Path

REQUIRED = ("nct", "applicationId", "reviewCycle", "assessmentLevel",
            "evidence", "limitations", "ownerReviewStatus",
            "outcomeJudgment", "timingJudgment", "frozenAt")

def validate(package):
    errors = []
    for field in REQUIRED:
        if not package.get(field):
            errors.append("MISSING_" + field)
    if type(package.get("assessmentLevel")) is not int or package.get("assessmentLevel") not in range(1, 21):
        errors.append("INVALID_LEVEL")
    if package.get("ownerReviewStatus") not in (
        "OWNER_ACCEPTED_WITH_LIMITATIONS", "OWNER_NEEDS_EVIDENCE", "OWNER_REJECTED"
    ):
        errors.append("OWNER_DECISION_REQUIRED")
    elif package["ownerReviewStatus"] != "OWNER_ACCEPTED_WITH_LIMITATIONS":
        errors.append("OWNER_HAS_NOT_ACCEPTED")
    # Legacy independentChallenge/reviewer fields may be preserved in archived
    # packages, but have NO authority as acceptance requirements.
    probability = package.get("outcomeProbability")
    if probability is not None:
        if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not 0 <= probability <= 1:
            errors.append("INVALID_PROBABILITY")
        if not package.get("calibrationReference"):
            errors.append("UNCALIBRATED_PROBABILITY")
    if package.get("outcomeJudgment") == package.get("timingJudgment"):
        errors.append("OUTCOME_AND_TIMING_NOT_DISTINGUISHED")
    evidence = package.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("NO_EVIDENCE")
    else:
        for item in evidence:
            if not isinstance(item, dict) or not all(item.get(k) for k in ("sourceUrl", "sourceDate", "claim", "locator")):
                errors.append("EVIDENCE_PROVENANCE_INCOMPLETE")
                break
    if package.get("historicalOutcomeExposed") is True:
        errors.append("OUTCOME_EXPOSED_NOT_PROSPECTIVE")
    if package.get("prospective") is True and package.get("historicalOutcomeExposed") is not False:
        errors.append("PROSPECTIVE_BLINDING_UNVERIFIED")
    if not package.get("predictionHistoryAppendOnly", False):
        errors.append("IMMUTABLE_HISTORY_NOT_ATTESTED")
    return {"accepted": not errors, "errors": errors,
            "status": "OWNER_REVIEWED_STRUCTURE_ONLY" if not errors else "OWNER_REVIEW_REQUIRED",
            "externalReviewersRequired": 0,
            "externalSignoffsRequired": 0,
            "ownerOnly": True,
            "independentlyCertified": False,
            "scientificAccuracyVerified": False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("package", type=Path)
    args = p.parse_args()
    result = validate(json.loads(args.package.read_text()))
    print(json.dumps(result, indent=2))
    if not result["accepted"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
