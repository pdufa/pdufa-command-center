#!/usr/bin/env python3
"""Fail-closed acceptance gate for independent 20-level scientific assessments.

Readiness records are not clinical reviews. This gate only validates a separately
authored, source-cited, independently challenged decision package.
"""
import argparse
import json
from pathlib import Path

REQUIRED = ("nct", "applicationId", "reviewCycle", "assessmentLevel",
            "evidence", "limitations", "reviewer", "independentChallenge",
            "outcomeJudgment", "timingJudgment", "frozenAt")

def validate(package):
    errors = []
    for field in REQUIRED:
        if not package.get(field):
            errors.append("MISSING_" + field)
    if package.get("assessmentLevel") not in range(1, 21):
        errors.append("INVALID_LEVEL")
    if package.get("reviewer") == package.get("independentChallenge", {}).get("reviewer"):
        errors.append("CHALLENGER_NOT_INDEPENDENT")
    if package.get("outcomeProbability") is not None and not package.get("calibrationReference"):
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
    if not package.get("predictionHistoryAppendOnly", False):
        errors.append("IMMUTABLE_HISTORY_NOT_ATTESTED")
    return {"accepted": not errors, "errors": errors,
            "status": "VALIDATED_PACKAGE_STRUCTURE_ONLY" if not errors else "REJECTED",
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
