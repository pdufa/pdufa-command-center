#!/usr/bin/env python3
"""MAIN R60: exact-original ClinicalTrials.gov efficacy/safety research challenge.

Read original R46, R55 and R59 research receipts and reconstruct all source
reported primary tables and adverse-event arm totals from the original 29
ClinicalTrials.gov JSON bodies. This is a source concordance/reviewer-worklist
audit, NOT a statistical reanalysis, qualified independent clinical review,
validated approval forecast, model training or historical backtest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scripts.assemble_focus_clinical_review_packets_r55 import _source_rows
from scripts.refresh_focus_public_sources_r40 import ROSTER, APPS, _read_json, build_manifest

SCHEMA = "MAIN_R60_ORIGINAL_REGISTRY_PRIMARY_SAFETY_CHALLENGE"
R59_SCHEMA = "MAIN_R59_FOCUS_29_TRIAL_23_APPLICATION_PHASE_FIRST_REVIEW_QUEUE"
R55_SCHEMA = "MAIN_R55_EXACT_23_APPLICATION_SOURCE_REPORTED_EFFICACY_SAFETY_METHOD_PACKETS"
R46_SCHEMA = "MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX"
SOURCE_FIELDS = (
    "postedPrimaryOutcomeTables",
    "reportedPrimaryStatisticalComparisons",
    "postedAdverseEventArmCountsAsReported",
    "seriousAeTermRowCount",
    "otherAeTermRowCount",
    "resultsFirstPostedDateFromCurrentRecord",
    "currentRegisteredPrimaryEndpointCount",
    "historicalOriginalRegisteredHierarchyUnverified",
    "trialResultsUnavailableInCurrentRegistryNotFailure",
    "scientificBenefitRiskNotIndependentlyReviewed",
)
SHA = re.compile(r"[0-9a-f]{64}\Z")


def ensure(condition, code):
    if not condition:
        raise ValueError(code)


def safe_json(path: Path, limit=20_000_000):
    ensure(path.is_file() and not path.is_symlink() and 10 <= path.stat().st_size <= limit,
           "ORIGINAL_SOURCE_FILE_NOT_SAFE")
    data = path.read_bytes()
    parsed = json.loads(data)
    ensure(isinstance(parsed, dict), "SOURCE_JSON_OBJECT_REQUIRED")
    return parsed, hashlib.sha256(data).hexdigest()


def build(manifest, r46, r55, r59, raw_dir: Path, *, r46_sha, r55_sha, r59_sha):
    ensure(all(isinstance(x, dict) for x in (manifest, r46, r55, r59))
           and all(isinstance(s, str) and SHA.fullmatch(s)
                   for s in (r46_sha, r55_sha, r59_sha)), "SOURCE_CHAIN_INVALID")
    ensure(manifest.get("trialCount") == 29 and manifest.get("applicationCount") == 23
           and r46.get("schema") == R46_SCHEMA and r46.get("nctCount") == 29
           and r46.get("applicationGroupCount") == 23
           and r55.get("schema") == R55_SCHEMA and r55.get("nctTrials") == 29
           and r55.get("applicationGroups") == 23
           and r59.get("schema") == R59_SCHEMA
           and r59.get("canonicalUniqueNctTrials") == 29
           and r59.get("provisionalApplicationCycles") == 23
           and r59.get("inputOriginalR46Sha256") == r46_sha
           and r59.get("inputOriginalR55Sha256") == r55_sha
           and r55.get("signedScientificReviews") == 0
           and r55.get("independentlyValidatedFDAApplicationForecasts") == 0
           and r55.get("modelTrainingAuthorized") is False
           and r55.get("clinicalOrProductionWrites") is False
           and r55.get("officialPendingFDAOutcome") == "ABSTAIN"
           and r59.get("signedIndependentClinicalReviews") == 0
           and r59.get("validatedFDAApplicationPredictions") == 0
           and r59.get("noModelTrainingOrProductionWrites") is True
           and r59.get("allFutureFDAOutcomes") == "ABSTAIN",
           "RESEARCH_CHAIN_NOT_ORIGINAL_OR_ALREADY_PROMOTED")
    ensure(raw_dir.is_dir() and not raw_dir.is_symlink(), "REGISTRY_DIRECTORY_NOT_SAFE")

    trials = manifest["trialRows"]
    apps = manifest["applicationGroups"]
    ncts = [t["nct"] for t in trials]
    group_ids = [g["cycleId"] for g in apps]
    ensure(len(set(ncts)) == 29 and len(set(group_ids)) == 23,
           "CANONICAL_MEMBERSHIP_DUPLICATED")
    old_index = r46.get("records")
    packet_trials = r55.get("originalUniqueTrialEvidence")
    packet_cases = r55.get("currentSourceCasePackets")
    queue_trials = r59.get("uniqueTrialSourceTasks")
    queue_cases = r59.get("applicationReviewQueue")
    ensure(all(isinstance(a, list) for a in (
        old_index, packet_trials, packet_cases, queue_trials, queue_cases))
        and [len(a) for a in (
            old_index, packet_trials, packet_cases, queue_trials, queue_cases
        )] == [29, 29, 23, 29, 23],
        "EXACT_SOURCE_OBJECT_CENSUS_REQUIRED")

    def index_exact(rows, field, expected):
        ensure(all(isinstance(r, dict) and isinstance(r.get(field), str) for r in rows),
               "ORIGINAL_SOURCE_ITEM_MALFORMED")
        ids = [x[field] for x in rows]
        ensure(len(set(ids)) == len(ids) and set(ids) == set(expected),
               "ORIGINAL_SOURCE_MEMBERSHIP_MISMATCH")
        return {r[field]: r for r in rows}

    receipt_by_nct = index_exact(old_index, "nct", ncts)
    r55_by_nct = index_exact(packet_trials, "nct", ncts)
    r59_by_nct = index_exact(queue_trials, "nct", ncts)
    r55_by_cycle = index_exact(packet_cases, "applicationCycleId", group_ids)
    r59_by_cycle = index_exact(queue_cases, "applicationCycleId", group_ids)

    relationships = {n: [] for n in ncts}
    for app in apps:
        for n in app["ncts"]:
            ensure(n in relationships and app["cycleId"] not in relationships[n],
                   "MULTIPLIED_APPLICATION_TO_NCT_LINK")
            relationships[n].append(app["cycleId"])

    evidence = []
    for meta in trials:
        n = meta["nct"]
        original = receipt_by_nct[n]
        source = r55_by_nct[n]
        queued = r59_by_nct[n]
        expected_cycles = sorted(relationships[n])
        ensure(source.get("applicationCycleIds") == expected_cycles
               and sorted(original.get("applicationCycleIds", [])) == expected_cycles
               and queued.get("applicationCycleIds") == expected_cycles
               and source.get("independentReviewerSigned") is False
               and source.get("scientificScore") is None
               and source.get("officialFDAOutcomeForecast") == "ABSTAIN"
               and queued.get("phaseIndependentlyAdjudicated") is False
               and queued.get("signedScientificReview") is False
               and queued.get("fdaPredictionValidated") is False,
               "REVIEW_STATE_OR_EXACT_TRIAL_LINKS_CHANGED")
        p = raw_dir / (n + ".json")
        ensure(p.is_file() and not p.is_symlink()
               and p.resolve().is_relative_to(raw_dir.resolve())
               and 10 <= p.stat().st_size <= 10_000_000,
               "EXACT_ORIGINAL_REGISTRY_RESPONSE_REQUIRED")
        bytes_ = p.read_bytes()
        hash_ = hashlib.sha256(bytes_).hexdigest()
        ensure(hash_ == original.get("sourceResponseSha256") ==
               source.get("currentRegistrySourceSha256") ==
               queued.get("currentOriginalRegistrySha256")
               and len(bytes_) == original.get("sourceResponseBytes"),
               "ORIGINAL_REGISTRY_BYTES_OR_SHA_CHANGED")
        body = json.loads(bytes_)
        calculated = _source_rows(body, n)
        ensure(all(source.get(field) == calculated[field] for field in SOURCE_FIELDS),
               "REPORTED_PRIMARY_OR_SAFETY_SOURCE_DIVERGENCE")
        primary = calculated["postedPrimaryOutcomeTables"]
        arms = calculated["postedAdverseEventArmCountsAsReported"]
        ensure(queued.get("reportedPrimaryTables") == len(primary)
               and queued.get("reportedPrimaryComparisons") ==
               calculated["reportedPrimaryStatisticalComparisons"]
               and queued.get("currentAdverseEventArms") == len(arms),
               "R59_VERSUS_ORIGINAL_RESULTS_COUNT_DRIFT")
        issue_codes = []
        if not primary:
            issue_codes.append("NO_CURRENT_POSTED_PRIMARY_TABLE_CHECK_OTHER_ORIGINALS")
        if any(t["sameTitleAndTimeFrameAsCurrentRegistration"] is False for t in primary):
            issue_codes.append("CURRENT_REGISTRATION_AND_POSTED_PRIMARY_TITLE_OR_TIME_DIFFER")
        if any(not t["statisticalComparisons"] for t in primary):
            issue_codes.append("POSTED_PRIMARY_WITHOUT_STATISTICAL_COMPARISON")
        if any(q["reportedPValueLiteral"] is None
               for t in primary for q in t["statisticalComparisons"]):
            issue_codes.append("STATISTICAL_COMPARISON_WITHOUT_REPORTED_P_VALUE")
        if not arms:
            issue_codes.append("NO_CURRENT_POSTED_SAFETY_ARM_TABLE_CHECK_OTHER_ORIGINALS")
        safety = []
        for arm in arms:
            for term in ("serious", "deaths", "other"):
                affected = arm.get(term + "Affected")
                at_risk = arm.get(term + "AtRisk")
                if affected is None or at_risk is None:
                    if "INCOMPLETE_POSTED_SAFETY_ARM_DENOMINATOR" not in issue_codes:
                        issue_codes.append("INCOMPLETE_POSTED_SAFETY_ARM_DENOMINATOR")
                else:
                    ensure(type(affected) is int and type(at_risk) is int
                           and 0 <= affected <= at_risk,
                           "INVALID_SOURCE_SAFETY_DENOMINATOR")
            safety.append({
                "sourceGroupId": arm["groupId"],
                "sourceGroupName": arm["groupName"],
                "seriousAffectedAndAtRisk": [arm["seriousAffected"], arm["seriousAtRisk"]],
                "deathsAffectedAndAtRisk": [arm["deathsAffected"], arm["deathsAtRisk"]],
                "otherAffectedAndAtRisk": [arm["otherAffected"], arm["otherAtRisk"]],
                "treatmentCausalityOrCrossArmRiskNotAdjudicated": True,
            })
        comparisons = []
        for table in primary:
            comparisons.append({
                "title": table["titleAsPosted"],
                "timeFrame": table["timeFrameAsPosted"],
                "sameAsCurrentRegisteredTitleAndTime": table[
                    "sameTitleAndTimeFrameAsCurrentRegistration"],
                "analysisAsReported": [{
                    "groupIds": q["groupIds"],
                    "pValueLiteral": q["reportedPValueLiteral"],
                    "effectEstimateLiteral": q["reportedEstimateLiteral"],
                    "confidenceLevelLiteral": q["reportedConfidenceLevelLiteral"],
                    "confidenceLowerLiteral": q["reportedLowerBoundLiteral"],
                    "confidenceUpperLiteral": q["reportedUpperBoundLiteral"],
                    "statisticalMethodAsReported": q["reportedStatisticalMethod"],
                    "independentReanalysis": False,
                    "adjustedOrFamilyWiseValidityConfirmed": False,
                } for q in table["statisticalComparisons"]],
            })
        evidence.append({
            "nct": n,
            "applicationCycleIds": expected_cycles,
            "registryExactCurrentOriginalUrl": "https://clinicaltrials.gov/study/" + n,
            "sourceSha256": hash_,
            "resultsFirstPostedDateFromCurrentRecord": calculated[
                "resultsFirstPostedDateFromCurrentRecord"],
            "currentlyRegisteredPrimaryCount": calculated[
                "currentRegisteredPrimaryEndpointCount"],
            "sourceReportedPrimaryTables": comparisons,
            "sourceReportedSafetyArms": safety,
            "sourceSeriousAdverseEventTermRows": calculated["seriousAeTermRowCount"],
            "sourceOtherAdverseEventTermRows": calculated["otherAeTermRowCount"],
            "originalSourceComparedToR46R55R59": True,
            "reviewExceptionCodes": issue_codes,
            "requiresOriginalPreReadoutSAPAndProtocol": True,
            "independentlyQualifiedStatisticalJudgment": None,
            "independentlyQualifiedSafetyJudgment": None,
            "fdaOutcome": "ABSTAIN",
            "fdaReviewTiming": "ABSTAIN",
        })

    view = {x["nct"]: x for x in evidence}
    by_cycle = []
    for app in apps:
        a = r55_by_cycle[app["cycleId"]]
        queued = r59_by_cycle[app["cycleId"]]
        ensure(a.get("exactNcts") == app["ncts"]
               and queued.get("supportingExactNcts") == app["ncts"]
               and queued.get("forecastApprovalOrCRL") == "ABSTAIN"
               and queued.get("forecastReviewTiming") == "ABSTAIN"
               and queued.get("approvalProbability") is None
               and a.get("independentClinicalReviewerSignoff") is False,
               "APPLICATION_REVIEW_OR_CROSSWALK_CHANGED")
        by_cycle.append({
            "applicationCycleId": app["cycleId"],
            "ticker": app["ticker"],
            "indication": app["indication"],
            "supportingExactNcts": list(app["ncts"]),
            "uniqueLinkedTrialsWithPostedPrimary": sum(
                bool(view[n]["sourceReportedPrimaryTables"]) for n in app["ncts"]),
            "uniqueLinkedTrialsWithCurrentSafetyArms": sum(
                bool(view[n]["sourceReportedSafetyArms"]) for n in app["ncts"]),
            "perTrialSourceChallengeIds": [
                {"nct": n, "exceptionCodes": view[n]["reviewExceptionCodes"]}
                for n in app["ncts"]],
            "scientificAdjudicationComplete": False,
            "officialApprovalOrCrlForecast": "ABSTAIN",
            "officialTimingForecast": "ABSTAIN",
        })

    total_tables = sum(len(x["sourceReportedPrimaryTables"]) for x in evidence)
    total_comp = sum(len(t["analysisAsReported"])
                     for x in evidence for t in x["sourceReportedPrimaryTables"])
    total_sae = sum(x["sourceSeriousAdverseEventTermRows"] for x in evidence)
    total_other = sum(x["sourceOtherAdverseEventTermRows"] for x in evidence)
    ensure(total_tables == r55.get("postedPrimaryTables")
           and total_comp == r55.get("reportedPrimaryStatisticalComparisons")
           and total_sae == r55.get("seriousAeTermRows")
           and total_other == r55.get("otherAeTermRows")
           and sum(bool(x["sourceReportedPrimaryTables"]) for x in evidence) ==
               r59.get("currentTrialsWithPostedPrimary")
           and sum(bool(x["sourceReportedSafetyArms"]) for x in evidence) ==
               r59.get("currentTrialsWithPostedSafetyArms"),
           "WHOLE_ROSTER_ORIGINAL_STATISTICS_CENSUS_CHANGED")

    return {
        "schema": SCHEMA,
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "originalInputSha256": {
            "r46": r46_sha, "r55": r55_sha, "r59": r59_sha,
        },
        "canonicalUniqueNctCount": 29,
        "provisionalApplicationCycleCount": 23,
        "sourceVerifiedCurrentPrimaryTrialCount": sum(
            bool(x["sourceReportedPrimaryTables"]) for x in evidence),
        "sourceVerifiedCurrentSafetyArmTrialCount": sum(
            bool(x["sourceReportedSafetyArms"]) for x in evidence),
        "sourceReportedPrimaryTables": total_tables,
        "sourceReportedStatisticalComparisons": total_comp,
        "sourceReportedSeriousAeTermRows": total_sae,
        "sourceReportedOtherAeTermRows": total_other,
        "uniqueTrialOriginalResultChallenges": evidence,
        "applicationSourceReviewCrosswalk": by_cycle,
        "reportedPValueNotRecalculatedOrRegulatorAdjudicated": True,
        "noRegistryResultDoesNotProveTrialFailure": True,
        "qualifiedClinicalOrStatisticalSignoffs": 0,
        "independentlyValidatedFdaForecasts": 0,
        "fdaApprovalProbability": None,
        "measuredPredictionAccuracy": None,
        "officialFutureFdaOutcome": "ABSTAIN",
        "officialFutureReviewTiming": "ABSTAIN",
        "reviewerLedgerProductionWritesOrModelTraining": False,
    }


def summary(report):
    rows = [
        "# MAIN R60 original-primary/safety review challenge",
        "",
        "Read-only original-source concordance, not independent efficacy/safety adjudication or FDA forecasting.",
        "",
        "| NCT | Posted primary tables | Primary comparisons | Safety arms | Unresolved review exceptions |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for x in report["uniqueTrialOriginalResultChallenges"]:
        exception = ", ".join(x["reviewExceptionCodes"]) or "Independent clinical review still required"
        rows.append(
            f'| [`{x["nct"]}`]({x["registryExactCurrentOriginalUrl"]})'
            f' | {len(x["sourceReportedPrimaryTables"])}'
            f' | {sum(len(q["analysisAsReported"]) for q in x["sourceReportedPrimaryTables"])}'
            f' | {len(x["sourceReportedSafetyArms"])} | {exception} |'
        )
    rows.extend([
        "", "**No independently verified clinical signoffs, FDA forecasts or accuracy metrics.**",
        "Current registry absence is not a clinical failure or proof that alternate public evidence is absent.",
        "Original pre-readout protocol/SAP and full causal safety review remain unresolved.", "",
    ])
    return "\n".join(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("r46", "r55", "r59"):
        p.add_argument("--" + arg, required=True, type=Path)
    p.add_argument("--raw-registry-dir", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--summary", required=True, type=Path)
    args = p.parse_args()
    ensure(args.output != args.summary and
           all(not path.exists() and not path.is_symlink() and path.parent.is_dir()
               for path in (args.output, args.summary)),
           "WRITE_ONCE_OUTPUT_AND_DIFFERENT_FILES_REQUIRED")
    r46, sha46 = safe_json(args.r46)
    r55, sha55 = safe_json(args.r55)
    r59, sha59 = safe_json(args.r59)
    report = build(build_manifest(_read_json(ROSTER), _read_json(APPS)),
                   r46, r55, r59, args.raw_registry_dir,
                   r46_sha=sha46, r55_sha=sha55, r59_sha=sha59)
    with args.output.open("xb") as handle:
        handle.write((json.dumps(report, sort_keys=True, indent=2) + "\n").encode())
    with args.summary.open("xb") as handle:
        handle.write(summary(report).encode())
    print(json.dumps({
        "nct": report["canonicalUniqueNctCount"],
        "applications": report["provisionalApplicationCycleCount"],
        "sourcePrimaryTables": report["sourceReportedPrimaryTables"],
        "reportedStatisticalComparisons": report["sourceReportedStatisticalComparisons"],
        "independentFdaForecasts": report["independentlyValidatedFdaForecasts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
