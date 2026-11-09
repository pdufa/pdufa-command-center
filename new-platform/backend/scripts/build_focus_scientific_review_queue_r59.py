#!/usr/bin/env python3
"""MAIN R59: build phase-first, source-linked FOCUS scientific review queue.

Uses the exact existing R55 original current-registry research packet and the
canonical independent FOCUS 29-NCT / 23 provisional application crosswalk.
Source availability/absence never implies efficacy success/failure. Trial rows
remain unique when linked to two application cycles. Read-only research outputs:
no patient-level calculations, clinical grades, FDA forecast, automatic model
training, retrospective outcome leakage, production or reviewer-ledger writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scripts.refresh_focus_public_sources_r40 import APPS, ROSTER, _read_json, build_manifest

SCHEMA = "MAIN_R59_FOCUS_29_TRIAL_23_APPLICATION_PHASE_FIRST_REVIEW_QUEUE"
INPUT_SCHEMA = "MAIN_R55_EXACT_23_APPLICATION_SOURCE_REPORTED_EFFICACY_SAFETY_METHOD_PACKETS"
SHA = re.compile(r"[0-9a-f]{64}\Z")
NCT = re.compile(r"NCT[0-9]{8}\Z")
STAGES = frozenset({
    "PLANNED", "PRIOR_CRL_RESUBMISSION_PLANNED", "SUBMITTED_PENDING_ACCEPTANCE",
    "UNDER_REVIEW", "SUPPLEMENT_UNDER_REVIEW", "APPROVED_ALREADY",
})


def _integrity(condition, code):
    if not condition:
        raise ValueError(code)


def _read_guarded(path: Path) -> tuple[dict, str]:
    _integrity(path.is_file() and not path.is_symlink() and path.stat().st_size < 20_000_000,
               "UNSAFE_R55_ORIGINAL_SOURCE")
    raw = path.read_bytes()
    payload = json.loads(raw)
    _integrity(isinstance(payload, dict), "INVALID_R55_JSON_OBJECT")
    return payload, hashlib.sha256(raw).hexdigest()


def build(manifest: dict, r55: dict, *, r55_sha256: str) -> dict:
    _integrity(isinstance(manifest, dict) and isinstance(r55, dict)
               and isinstance(r55_sha256, str) and SHA.fullmatch(r55_sha256),
               "SOURCE_OR_RECEIPT_INVALID")
    _integrity(manifest.get("trialCount") == 29 and manifest.get("applicationCount") == 23
               and r55.get("schema") == INPUT_SCHEMA
               and r55.get("nctTrials") == 29 and r55.get("applicationGroups") == 23
               and r55.get("sourceVerifiedCurrentProtocolSAPDocuments") == 23
               and r55.get("signedScientificReviews") == 0
               and r55.get("independentlyValidatedFDAApplicationForecasts") == 0
               and r55.get("historicalLockedSAPsIndependentlyVerified") == 0
               and r55.get("measuredAccuracy") is None
               and r55.get("modelTrainingAuthorized") is False
               and r55.get("clinicalOrProductionWrites") is False
               and r55.get("officialPendingFDAOutcome") == "ABSTAIN",
               "INVALID_OR_CERTIFIED_R55_RESEARCH_SOURCE")

    trials = manifest["trialRows"]
    groups = manifest["applicationGroups"]
    source_trials = r55.get("originalUniqueTrialEvidence")
    source_cases = r55.get("currentSourceCasePackets")
    _integrity(isinstance(source_trials, list) and len(source_trials) == 29
               and isinstance(source_cases, list) and len(source_cases) == 23
               and len({t["nct"] for t in source_trials if isinstance(t, dict)}) == 29
               and len({a["applicationCycleId"] for a in source_cases if isinstance(a, dict)}) == 23,
               "DUPLICATE_OR_MISSING_SOURCE_MEMBERS")
    expected_ncts = [t["nct"] for t in trials]
    expected_groups = [g["cycleId"] for g in groups]
    _integrity(set(expected_ncts) == {t["nct"] for t in source_trials}
               and set(expected_groups) == {a["applicationCycleId"] for a in source_cases},
               "ROSTER_MEMBERSHIP_CHANGED")

    trial_map = {x["nct"]: x for x in source_trials}
    app_map = {x["applicationCycleId"]: x for x in source_cases}
    relationships = {n: [] for n in expected_ncts}
    for g in groups:
        for n in g["ncts"]:
            _integrity(n in relationships and g["cycleId"] not in relationships[n],
                       "APP_TRIAL_CROSSWALK_INVALID")
            relationships[n].append(g["cycleId"])

    trial_out = []
    for meta in trials:
        n = meta["nct"]
        x = trial_map[n]
        _integrity(isinstance(n, str) and NCT.fullmatch(n)
                   and x.get("applicationCycleIds") == sorted(relationships[n])
                   and x.get("currentRegistryOriginalUrl") == "https://clinicaltrials.gov/study/" + n
                   and isinstance(x.get("currentRegistrySourceSha256"), str)
                   and SHA.fullmatch(x["currentRegistrySourceSha256"])
                   and x.get("independentReviewerSigned") is False
                   and x.get("scientificScore") is None
                   and x.get("officialFDAOutcomeForecast") == "ABSTAIN",
                   "TRIAL_SOURCE_IDENTITY_OR_REVIEW_STATE_INVALID")
        tables = x.get("postedPrimaryOutcomeTables")
        arms = x.get("postedAdverseEventArmCountsAsReported")
        docs = x.get("sourceMethodsPageReferences")
        _integrity(isinstance(tables, list) and isinstance(arms, list) and isinstance(docs, list)
                   and len(tables) <= 100 and len(arms) <= 100 and len(docs) <= 10,
                   "SOURCE_ROWS_NOT_VALID_LISTS")
        comparisons = 0
        for t in tables:
            q = t.get("statisticalComparisons")
            _integrity(isinstance(q, list) and len(q) <= 100 and
                       all(a.get("nominalOrAdjustedStatusIndependentlyVerified") is False and
                           a.get("independentStatisticalRecalculationComplete") is False
                           for a in q), "SOURCE_COMPARISONS_ALREADY_GRADED")
            comparisons += len(q)
        _integrity(x.get("reportedPrimaryStatisticalComparisons") == comparisons,
                   "SOURCE_PRIMARY_COMPARISON_CENSUS_CHANGED")
        seen_doc = set()
        for d in docs:
            key = (d.get("filename"), d.get("sha256"))
            _integrity(key not in seen_doc and isinstance(key[1], str) and SHA.fullmatch(key[1])
                       and isinstance(d.get("sourceUrl"), str)
                       and d["sourceUrl"].startswith(
                           "https://cdn.clinicaltrials.gov/large-docs/" + n[-2:] + "/" + n + "/")
                       and isinstance(d.get("eightScientificMethodPageLeads"), dict),
                       "ORIGINAL_SOURCE_DOCUMENT_REFERENCE_INVALID")
            seen_doc.add(key)
        for arm in arms:
            _integrity(isinstance(arm.get("groupId"), str)
                       and isinstance(arm.get("groupName"), str)
                       and arm.get("noCrossArmCausalComparisonAuthorized") is True,
                       "SOURCE_SAFETY_ARM_INVALID")

        tasks = ["VERIFY_CURRENT_PHASE_AND_ORIGINAL_PHASE_LINEAGE"]
        tasks.append("INDEPENDENTLY_RECONCILE_PRIMARY_RESULTS_AND_SAP"
                     if tables else "FIND_PRIMARY_EFFICACY_IN_SPONSOR_JOURNAL_REGULATORY_ORIGINALS")
        tasks.append("AUTHENTICATE_PREUNBLINDING_PROTOCOL_SAP_AND_AMENDMENTS"
                     if docs else "RECOVER_ORIGINAL_PROTOCOL_SAP_OUTSIDE_CURRENT_REGISTRY")
        tasks.append("REVIEW_REPORTED_SAFETY_ARMS_AND_EXPOSURE_WINDOWS"
                     if arms else "RECOVER_ORIGINAL_SAFETY_DATA_OUTSIDE_CURRENT_REGISTRY")
        tasks.append("VERIFY_APPLICATION_CYCLE_FDA_STATUS_AND_CMC_SOURCES")
        trial_out.append({
            "nct": n, "applicationCycleIds": sorted(relationships[n]),
            "currentOriginalRegistryUrl": x["currentRegistryOriginalUrl"],
            "currentOriginalRegistrySha256": x["currentRegistrySourceSha256"],
            "reportedPrimaryTables": len(tables),
            "reportedPrimaryComparisons": comparisons,
            "currentAdverseEventArms": len(arms),
            "currentAttachedProtocolSapDocuments": len(docs),
            "currentAttachedSourceDocumentLinks": [
                {"url": d["sourceUrl"], "sha256": d["sha256"],
                 "pageLinkedMethodLeadCount": sum(len(p) for p in d["eightScientificMethodPageLeads"].values())}
                for d in docs
            ],
            "reviewTasks": tasks,
            "currentRegistryMissingDoesNotMeanOtherSourceMissingOrTrialFailed": True,
            "phaseIndependentlyAdjudicated": False,
            "signedScientificReview": False,
            "fdaPredictionValidated": False,
        })

    by_n = {t["nct"]: t for t in trial_out}
    applications = []
    for original in groups:
        app_id = original["cycleId"]
        source = app_map[app_id]
        linked = original["ncts"]
        _integrity(source.get("exactNcts") == linked
                   and source.get("ticker") == original["ticker"]
                   and source.get("drug") == original["drug"]
                   and source.get("indication") == original["indication"]
                   and source.get("reportedApplicationStageFromSnapshot") == original["stage"]
                   and original["stage"] in STAGES
                   and source.get("officialFDAOutcomePrediction") == "ABSTAIN"
                   and source.get("officialDelayPrediction") == "ABSTAIN"
                   and source.get("scientificGrade") is None
                   and source.get("fdaProbability") is None
                   and source.get("independentClinicalReviewerSignoff") is False,
                   "APPLICATION_STATUS_OR_FORECAST_SOURCE_CHANGED")
        _integrity(source.get("postedPrimaryTablesAcrossLinkedTrials") ==
                   sum(by_n[n]["reportedPrimaryTables"] for n in linked)
                   and source.get("postedStatisticalComparisonsAcrossLinkedTrials") ==
                   sum(by_n[n]["reportedPrimaryComparisons"] for n in linked)
                   and source.get("linkedCurrentProtocolSAPDocs") ==
                   sum(by_n[n]["currentAttachedProtocolSapDocuments"] for n in linked)
                   and source.get("linkedTrialsWithCurrentAEArms") ==
                   sum(bool(by_n[n]["currentAdverseEventArms"]) for n in linked),
                   "APP_SOURCE_TOTALS_DIFFER_FROM_UNIQUE_TRIALS")
        posted = sum(by_n[n]["reportedPrimaryTables"] for n in linked)
        pdfs = sum(by_n[n]["currentAttachedProtocolSapDocuments"] for n in linked)
        bucket = ("CURRENT_PRIMARY_AND_PDF_SOURCE_PRESENT" if posted and pdfs
                  else "CURRENT_PRIMARY_SOURCE_ONLY" if posted
                  else "CURRENT_PDF_SOURCE_ONLY" if pdfs
                  else "ALTERNATIVE_ORIGINAL_SOURCE_RECOVERY_REQUIRED")
        status = original["stage"]
        priority = ("VERIFY_OBSERVED_ACTION_NOT_FUTURE_FORECAST" if status == "APPROVED_ALREADY"
                    else "VERIFY_ACTIVE_REGULATORY_REVIEW_AND_EVIDENCE" if status in
                    ("UNDER_REVIEW", "SUPPLEMENT_UNDER_REVIEW")
                    else "VERIFY_SOURCE_STAGE_AND_MISSING_EVIDENCE")
        applications.append({
            "applicationCycleId": app_id,
            "ticker": original["ticker"],
            "drug": original["drug"],
            "indication": original["indication"],
            "sourceReportedStageUnverified": status,
            "applicationStageVerificationRequired": True,
            "supportingExactNcts": list(linked),
            "linkedTrialCount": len(linked),
            "currentPrimaryTables": posted,
            "currentProtocolSapDocuments": pdfs,
            "currentSafetyArmTrials": sum(bool(by_n[n]["currentAdverseEventArms"]) for n in linked),
            "sourceCoverageBucketNotClinicalGrade": bucket,
            "nextReviewPriority": priority,
            "missingOriginalSourceTasksByTrial": [
                {"nct": n, "reviewTasks": by_n[n]["reviewTasks"]} for n in linked
            ],
            "forecastApprovalOrCRL": "ABSTAIN",
            "forecastReviewTiming": "ABSTAIN",
            "approvalProbability": None,
            "independentClinicalReviewerSigned": False,
            "observedStageNotForwardPrediction": status == "APPROVED_ALREADY",
        })

    _integrity(sum(len(t["currentAttachedSourceDocumentLinks"]) for t in trial_out) == 23
               and sum(t["reportedPrimaryTables"] for t in trial_out) == r55.get("postedPrimaryTables")
               and sum(t["reportedPrimaryComparisons"] for t in trial_out) ==
                   r55.get("reportedPrimaryStatisticalComparisons")
               and sum(bool(t["reportedPrimaryTables"]) for t in trial_out) ==
                   r55.get("uniqueTrialsWithPostedPrimary")
               and sum(bool(t["currentAdverseEventArms"]) for t in trial_out) ==
                   r55.get("uniqueTrialsWithPostedAdverseEvents"),
               "UNIQUE_TRIAL_SOURCE_CENSUS_DRIFT")

    return {
        "schema": SCHEMA,
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inputOriginalR55Sha256": r55_sha256,
        "canonicalUniqueNctTrials": 29,
        "provisionalApplicationCycles": 23,
        "currentTrialsWithPostedPrimary": r55["uniqueTrialsWithPostedPrimary"],
        "currentTrialsWithPostedSafetyArms": r55["uniqueTrialsWithPostedAdverseEvents"],
        "attachedOriginalProtocolSapDocuments": 23,
        "applicationReviewQueue": applications,
        "uniqueTrialSourceTasks": trial_out,
        "allCurrentEfficacySafetyResultsAreUnadjudicated": True,
        "noRegistryPostingsIsNotEvidenceOfTrialFailure": True,
        "originalProtocolAndSapPreunblindingSignoffsValidated": 0,
        "signedIndependentClinicalReviews": 0,
        "validatedFDAApplicationPredictions": 0,
        "calibratedFDAProbability": None,
        "measuredHistoricalAccuracy": None,
        "allFutureFDAOutcomes": "ABSTAIN",
        "noModelTrainingOrProductionWrites": True,
    }


def markdown_report(doc: dict) -> str:
    lines = [
        "# FOCUS R59 — 23 source-linked application review queues",
        "",
        "Research-only. Application-stage labels are unverified snapshot entries, not adjudicated FDA actions.",
        "No numerical probability, clinical grade or validated outcome forecast.",
        "",
        "| Application | NCTs | Primary tables | Current PDFs | Next review |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for a in doc["applicationReviewQueue"]:
        lines.append(
            f'| {a["ticker"]} / `{a["applicationCycleId"]}`'
            f' | {a["linkedTrialCount"]} | {a["currentPrimaryTables"]}'
            f' | {a["currentProtocolSapDocuments"]}'
            f' | {a["nextReviewPriority"]} |'
        )
    lines.extend([
        "", "## Source and independent-science restrictions",
        "",
        "- Each application row links to exact-NCT research tasks in the matching JSON artifact.",
        "- Multiple application groups can share the same source trial; the 29-trial evidence count remains unique.",
        "- A missing current ClinicalTrials.gov result/PDF is a request to find alternate original sources, not a trial failure.",
        "- Unverified preliminary application stages, CMC, FDA decisions and amendment dates must not be used as validated predictions.",
        "- FDA outcome/timing: **ABSTAIN**; independently validated forecasts **0/23**; clinical signoffs **0**.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r55", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()
    _integrity(args.output != args.summary and
               all(not p.exists() and not p.is_symlink() and p.parent.is_dir()
                   for p in (args.output, args.summary)), "WRITE_ONCE_RESEARCH_OUTPUT_REQUIRED")
    r55, sha = _read_guarded(args.r55)
    manifest = build_manifest(_read_json(ROSTER), _read_json(APPS))
    output = build(manifest, r55, r55_sha256=sha)
    with args.output.open("xb") as file:
        file.write((json.dumps(output, indent=2, sort_keys=True) + "\n").encode())
    with args.summary.open("xb") as file:
        file.write(markdown_report(output).encode())
    print(json.dumps({
        "nctTrials": output["canonicalUniqueNctTrials"],
        "applicationCycles": output["provisionalApplicationCycles"],
        "currentTrialsWithPrimary": output["currentTrialsWithPostedPrimary"],
        "signedIndependentClinicalReviews": output["signedIndependentClinicalReviews"],
        "validatedFDAApplicationPredictions": output["validatedFDAApplicationPredictions"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
