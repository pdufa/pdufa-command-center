#!/usr/bin/env python3
"""R61 verify a compact dashboard copy against immutable ORIGINAL R60 evidence.

No network calls, data modification, clinical judgment, prediction or training.
Requires downloaded exact pinned R60 artifact JSON, not a rewritten source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

R60_SOURCE_SHA = "65f6e06d29706e5a6d590a3afe73c37def878623d47a094dbc0b33986e9747c6"
R60_SCHEMA = "MAIN_R60_ORIGINAL_REGISTRY_PRIMARY_SAFETY_CHALLENGE"
EXPECTED_RUN = 42709199117
EXPECTED_ARTIFACT = 13715890359
EXPECTED_UTC = "2026-11-09T22:09:29+00:00"
SOURCE_IDS = {
    "r46": "7e1681399ed242d0080d8517bbe62cfb931e88e1340295fdf9839affbc0d3f92",
    "r55": "0e399209a26778f15e9b6fa1d7e626232d92f1a17ec042dbde6dc110a977729c",
    "r59": "089370a0220173935fbec5e0b79d1c07c43685e82adb1650182db30fceb7c9f1",
}


def check(original_bytes: bytes, preview_bytes: bytes) -> dict:
    if hashlib.sha256(original_bytes).hexdigest() != R60_SOURCE_SHA:
        raise ValueError("R60_ORIGINAL_SOURCE_SHA_DRIFT")
    original = json.loads(original_bytes)
    frontend = json.loads(preview_bytes)
    if (
        original.get("schema") != R60_SCHEMA
        or original.get("generatedAtUtc") != EXPECTED_UTC
        or original.get("originalInputSha256") != SOURCE_IDS
        or original.get("canonicalUniqueNctCount") != 29
        or original.get("provisionalApplicationCycleCount") != 23
        or original.get("sourceVerifiedCurrentPrimaryTrialCount") != 12
        or original.get("sourceVerifiedCurrentSafetyArmTrialCount") != 12
        or original.get("sourceReportedPrimaryTables") != 16
        or original.get("sourceReportedStatisticalComparisons") != 20
        or original.get("sourceReportedSeriousAeTermRows") != 244
        or original.get("sourceReportedOtherAeTermRows") != 202
        or original.get("independentlyValidatedFdaForecasts") != 0
        or original.get("qualifiedClinicalOrStatisticalSignoffs") != 0
        or original.get("fdaApprovalProbability") is not None
        or original.get("measuredPredictionAccuracy") is not None
        or original.get("officialFutureFdaOutcome") != "ABSTAIN"
        or original.get("officialFutureReviewTiming") != "ABSTAIN"
        or original.get("reviewerLedgerProductionWritesOrModelTraining") is not False
    ):
        raise ValueError("ORIGINAL_R60_SCIENTIFIC_RELEASE_GATES_CHANGED")
    original_trials = original["uniqueTrialOriginalResultChallenges"]
    if len(original_trials) != 29 or len({r["nct"] for r in original_trials}) != 29:
        raise ValueError("ORIGINAL_R60_TRIAL_MEMBERSHIP_INVALID")
    expected = {
        "rev": 60,
        "run": EXPECTED_RUN,
        "artifact": EXPECTED_ARTIFACT,
        "utc": EXPECTED_UTC,
        "sourceHashes": SOURCE_IDS,
        "trials": [],
    }
    for t in original_trials:
        primary = t["sourceReportedPrimaryTables"]
        arms = t["sourceReportedSafetyArms"]
        item = {
            "n": t["nct"],
            "h": t["sourceSha256"],
            "p": len(primary),
            "q": sum(len(p["analysisAsReported"]) for p in primary),
            "a": len(arms),
        }
        if t["reviewExceptionCodes"]:
            item["e"] = t["reviewExceptionCodes"]
        if primary:
            item["m"] = [
                [
                    p["title"],
                    [[v["pValueLiteral"], v["effectEstimateLiteral"]]
                     for v in p["analysisAsReported"]],
                ]
                for p in primary
            ]
        if arms:
            item["s"] = [
                [a["sourceGroupName"], a["seriousAffectedAndAtRisk"]]
                for a in arms
            ]
        expected["trials"].append(item)
    if frontend != expected:
        raise ValueError("R61_DASHBOARD_SNAPSHOT_NOT_EXACT_DERIVATION_OF_ORIGINAL_R60")
    return {
        "ncts": len(frontend["trials"]),
        "applications": original["provisionalApplicationCycleCount"],
        "primaryTables": sum(t["p"] for t in frontend["trials"]),
        "statisticalComparisons": sum(t["q"] for t in frontend["trials"]),
        "sourceOnly": True,
        "validatedFDAForecasts": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--frontend", required=True, type=Path)
    args = parser.parse_args()
    for file in (args.original, args.frontend):
        if not file.is_file() or file.is_symlink() or file.stat().st_size > 1_000_000:
            raise ValueError("UNSAFE_ORIGINAL_OR_DASHBOARD_SOURCE")
    print(json.dumps(check(args.original.read_bytes(), args.frontend.read_bytes()),
                     sort_keys=True))


if __name__ == "__main__":
    main()
