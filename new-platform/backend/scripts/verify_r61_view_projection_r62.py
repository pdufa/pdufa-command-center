#!/usr/bin/env python3
"""MAIN R62: verify the checked-in R61 display against immutable R60 JSON.

Independent *projection equivalence* check, not an independent clinical review.
Rejects valid-looking modified p-values, primary endpoint text, safety counts,
source SHA changes, unknown extra entries and lost records, not just count drift.
Read-only verification of research/preview artifacts. Never train or predict.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

PINNED_R60_SHA256 = "65f6e06d29706e5a6d590a3afe73c37def878623d47a094dbc0b33986e9747c6"
R60_SCHEMA = "MAIN_R60_ORIGINAL_REGISTRY_PRIMARY_SAFETY_CHALLENGE"
RUN = 42709199117
ARTIFACT = 13715890359
SHA = re.compile(r"[a-f0-9]{64}\Z")
EXPECTED_ORIGINAL_SHA = {
    "r46":"7e1681399ed242d0080d8517bbe62cfb931e88e1340295fdf9839affbc0d3f92",
    "r55":"0e399209a26778f15e9b6fa1d7e626232d92f1a17ec042dbde6dc110a977729c",
    "r59":"089370a0220173935fbec5e0b79d1c07c43685e82adb1650182db30fceb7c9f1",
}

def require(value: bool, code: str) -> None:
    if not value:
        raise ValueError(code)

def load_original(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and 100 < path.stat().st_size < 1_000_000, "R60_SOURCE_FILE_INVALID")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PINNED_R60_SHA256,
            "UNPINNED_ORIGINAL_R60_ARCHIVE")
    data = json.loads(raw)
    require(isinstance(data, dict) and data.get("schema") == R60_SCHEMA
            and data.get("originalInputSha256") == EXPECTED_ORIGINAL_SHA
            and data.get("canonicalUniqueNctCount") == 29
            and data.get("provisionalApplicationCycleCount") == 23
            and data.get("sourceReportedPrimaryTables") == 16
            and data.get("sourceReportedStatisticalComparisons") == 20
            and data.get("sourceReportedSeriousAeTermRows") == 244
            and data.get("sourceReportedOtherAeTermRows") == 202
            and data.get("qualifiedClinicalOrStatisticalSignoffs") == 0
            and data.get("independentlyValidatedFdaForecasts") == 0
            and data.get("fdaApprovalProbability") is None
            and data.get("measuredPredictionAccuracy") is None
            and data.get("officialFutureFdaOutcome") == "ABSTAIN"
            and data.get("officialFutureReviewTiming") == "ABSTAIN"
            and data.get("reviewerLedgerProductionWritesOrModelTraining") is False,
            "ORIGINAL_R60_CERTIFICATION_INVARIANTS_FAILED")
    return data

def project(original: dict) -> dict:
    rows = original["uniqueTrialOriginalResultChallenges"]
    apps = original["applicationSourceReviewCrosswalk"]
    require(len(rows) == 29 and len(apps) == 23, "ORIGINAL_SOURCE_MEMBERSHIP_DRIFT")
    unique = set()
    out = []
    for row in rows:
        n = row["nct"]
        require(re.fullmatch(r"NCT[0-9]{8}",n) and n not in unique
                and SHA.fullmatch(row["sourceSha256"])
                and row.get("originalSourceComparedToR46R55R59") is True
                and row.get("independentlyQualifiedStatisticalJudgment") is None
                and row.get("independentlyQualifiedSafetyJudgment") is None
                and row.get("fdaOutcome") == "ABSTAIN"
                and row.get("fdaReviewTiming") == "ABSTAIN",
                "R60_TRIAL_SOURCE_OR_CLINICAL_GRADE_CHANGED")
        unique.add(n)
        primary = row["sourceReportedPrimaryTables"]
        arms = row["sourceReportedSafetyArms"]
        result = {
            "n":n,
            "h":row["sourceSha256"],
            "p":len(primary),
            "q":sum(len(t["analysisAsReported"]) for t in primary),
            "a":len(arms),
        }
        if row["reviewExceptionCodes"]:
            result["e"] = row["reviewExceptionCodes"]
        if primary:
            result["m"] = [[t["title"], [
                [x["pValueLiteral"], x["effectEstimateLiteral"]]
                for x in t["analysisAsReported"]
            ]] for t in primary]
        if arms:
            result["s"] = [[a["sourceGroupName"], a["seriousAffectedAndAtRisk"]]
                           for a in arms]
        out.append(result)
    require(sum(x["p"] for x in out) == 16
            and sum(x["q"] for x in out) == 20
            and sum(bool(x["p"]) for x in out) == 12
            and sum(bool(x["a"]) for x in out) == 12,
            "ORIGINAL_R60_CENSUS_CHANGED")
    return {
        "rev":60,"run":RUN,"artifact":ARTIFACT,
        "utc":original["generatedAtUtc"],
        "sourceHashes":dict(EXPECTED_ORIGINAL_SHA),
        "trials":out,
    }

def compare(original: dict, committed: dict) -> dict:
    require(isinstance(committed, dict), "UI_SNAPSHOT_NOT_JSON_OBJECT")
    expected = project(original)
    require(committed == expected, "R61_DISPLAY_DIFFERS_FROM_IMMUTABLE_R60_ORIGINAL")
    payload = json.dumps(committed,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return {
        "schema":"MAIN_R62_R61_DISPLAY_VERSUS_PINNED_R60_ORIGINAL_CONCORDANCE",
        "originalR60Sha256":PINNED_R60_SHA256,
        "canonicalViewSha256":hashlib.sha256(payload).hexdigest(),
        "uniqueNcts":len(expected["trials"]),
        "applicationGroups":23,
        "postedPrimaryTables":16,
        "reportedComparisons":20,
        "trialsWithPostedPrimary":12,
        "trialsWithCurrentSafetyArms":12,
        "sourceReportedSeriousAeTermRows":244,
        "sourceReportedOtherAeTermRows":202,
        "clinicalGrades":0,
        "validatedFdaForecasts":0,
        "fdaProbability":None,
        "accuracy":None,
        "officialFdaPrediction":"ABSTAIN",
        "liveOrReviewerWrites":False,
        "originalEvidenceMatch":True,
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-r60",required=True,type=Path)
    parser.add_argument("--r61-snapshot",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    a=parser.parse_args()
    require(a.r61_snapshot.is_file() and not a.r61_snapshot.is_symlink()
            and 100<a.r61_snapshot.stat().st_size<250_000
            and not a.output.exists() and not a.output.is_symlink()
            and a.output.parent.is_dir(),
            "UI_SOURCE_INPUT_OR_WRITE_ONCE_OUTPUT_INVALID")
    validated=compare(load_original(a.original_r60),json.loads(a.r61_snapshot.read_bytes()))
    with a.output.open("xb") as f:
        f.write((json.dumps(validated,sort_keys=True,indent=2)+"\n").encode())
    print(json.dumps(validated,sort_keys=True))

if __name__=="__main__":
    main()
