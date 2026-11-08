#!/usr/bin/env python3
"""Create a GitHub-run-bound checksum manifest for RAAS SOURCE RESEARCH outputs.

This is NOT a frozen FDA PASS/CRL/EXTENSION forecast, notarized timestamp,
independent prediction validation, authorized trading signal, or calibration.
GitHub Actions retention expires: preserve an independent copy for long-term use.
"""
from __future__ import annotations

# Permanent retirement: historical functions are importable for read-only audits only.
if __name__ == "__main__":
    raise SystemExit("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.")


import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

NAME_TO_SCOPE = {
    "raas-fda-three-way-prediction-accuracy.json":
       "RAAS_FDA_THREE_WAY_DECISION_ACCURACY_AUDIT",
    "raas-v2-prospective-source-readiness.json":
       "RAAS_V2_PROSPECTIVE_ORIGINAL_GOAL_SOURCE_READINESS_NOT_VALIDATED",
}
EXPECTED_FILES = (
    "raas-fda-three-way-prediction-accuracy.json",
    "raas-fda-historical-source-review-queue.csv",
    "raas-fda-upcoming-original-goal-review-queue.csv",
    "raas-v2-prospective-source-readiness.json",
    "raas-v2-prospective-source-review.csv",
    "raas-v2-openfda-application-identity-watch.json",
    "raas-v2-sec-nov14-new-filing-review-leads.json",
    "raas-v2-issuer-news-fallback-research-leads.json",
)


def require(condition, code):
    if not condition:
        raise ValueError("RAAS_V2_SOURCE_PROVENANCE_" + code)


def timestamp(value):
    require(isinstance(value, str) and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value),
        "TIMESTAMP_FORMAT")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("RAAS_V2_SOURCE_PROVENANCE_TIMESTAMP_INVALID") from exc


def validate_research_json(fda, v2):
    require(isinstance(fda, dict) and
            fda.get("scope") == NAME_TO_SCOPE[
                "raas-fda-three-way-prediction-accuracy.json"] and
            fda.get("status") ==
                "BENCHMARK_INSTALLED_NO_VALIDATED_THREE_WAY_ACCURACY" and
            fda.get("approvedFDAOutcomeAccuracyPct") is None and
            fda.get("approvedBestPredictiveModel") is None and
            fda.get("approvedRAASMetricCalibrations") == 0,
            "FDA_REPORT_UNAPPROVED_STATE_MISSING")
    three=fda.get("threeWayProspective")
    require(type(three) is dict and three.get("approvedModel") is False
            and three.get("verifiedFDAAccuracyPct") is None
            and type(three.get("frozenThreeClassPredictions")) is int,
            "FDA_THREE_WAY_STATE_INVALID")
    require(isinstance(v2, dict) and v2.get("scope") ==
            NAME_TO_SCOPE["raas-v2-prospective-source-readiness.json"]
            and v2.get("status") == "RESEARCH_V2_CANDIDATE_NOT_AN_APPROVED_MODEL"
            and v2.get("version") == "V2_RESEARCH_CANDIDATE_STAGE_0"
            and v2.get("modelVersionStillActive") == "2026-11-02-foundation-v1"
            and v2.get("readyForThreeWayProspectiveFreeze") == 0
            and v2.get("verifiedProspectiveForecasts") == 0
            and v2.get("independentlyVerifiedThreeWayAccuracyPct") is None
            and v2.get("approvedRAASMetricCalibrations") == 0,
            "V2_SOURCE_REPORT_UNAPPROVED_STATE_MISSING")
    # Dated issuer reiteration and public-source staleness must not be
    # mistaken for an official FDA statement ruling out a later extension.
    latest=v2.get("nov14DatedIssuerGoalContinuityChecks")
    require(type(latest) is list and len(latest)==2 and
        type(v2.get("nov14DatedIssuerSourcesPublicByAsOfCount")) is int and
        v2["nov14DatedIssuerSourcesPublicByAsOfCount"]==sum(
            x.get("sourceIsPublicByAuditAsOf") is True for x in latest)
        and type(v2.get("nov14IssuerSourcesOlderThan30DaysCount")) is int
        and v2["nov14IssuerSourcesOlderThan30DaysCount"]==sum(
            x.get("issuerGoalEvidenceOlderThan30DaysAtAudit") is True
            for x in latest)
        and v2.get("nov14IndependentlyCertifiedNoLaterFdaGoalRevisions")==0
        and {x.get("researchCaseKey") for x in latest}=={
            "CYTK|MYQORZO_HCM_20261114","SMMT|IVONESCIMAB_20261114"}
        and next(x for x in latest if x.get("ticker")=="SMMT").get(
            "laterIssuerReportMainSubjectIsDifferentTrial") is True
        and next(x for x in latest if x.get("ticker")=="SMMT").get(
            "laterIssuerReportSeparateTrialId")=="NCT07765433"
        and next(x for x in latest if x.get("ticker")=="SMMT").get(
            "pendingRegulatoryApplicationPivotalTrialId")=="NCT06396065"
        and all(x.get("currentlyIndependentlyCertifiedUnrevisedFdaDeadline") is False
            and x.get("currentFDAApplicationNumberIndependentlyVerified") is False
            and x.get("prospectivelyFrozenThreeWayForecast") is False
            for x in latest),
        "ISSUER_REITERATIONS_CANNOT_VERIFY_NO_LATER_FDA_EXTENSION")
    pending=v2.get("blockedSourceItems")
    require(type(pending) is list
            and type(v2.get("sourceQueueCount")) is int
            and len(pending) == v2["sourceQueueCount"],
            "V2_SOURCE_CASE_COUNT_MISMATCH")
    revised=sum(1 for r in pending if
                r.get("knownRevisedGoalNotOriginalPrediction") is True)
    require(type(v2.get("knownRevisedDeadlineExcludedFromOriginalGoalCount")) is int
            and v2["knownRevisedDeadlineExcludedFromOriginalGoalCount"] == revised,
            "V2_REVISED_GOAL_EXCLUSION_MISMATCH")
    require(all(r.get("V2ForecastEligible") is False
                and r.get("independentlyVerifiedApplicationCycle") is False
                and r.get("immutablePreactionThreeWayProbabilityVector") is False
                for r in pending),
            "UNVERIFIED_FORECAST_MARKED_ELIGIBLE")
    return pending


def build_manifest(directory, repo, run_id, sha, archived_at):
    require(repo == "pdufa/pdufa-command-center"
            and isinstance(run_id, str) and re.fullmatch(r"[1-9]\d{4,18}", run_id)
            and isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha),
            "GITHUB_PROVENANCE_INVALID")
    archive_clock=timestamp(archived_at)
    root=Path(directory)
    require(root.is_dir(), "SOURCE_DIRECTORY_MISSING")
    contents={}
    for name in EXPECTED_FILES:
        path=root/name
        require(path.is_file() and not path.is_symlink(), "OUTPUT_MISSING_OR_LINK")
        data=path.read_bytes()
        require(0<len(data)<20_000_000, "OUTPUT_SIZE_INVALID")
        contents[name]={
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes":len(data)
        }
    fda=json.loads((root/EXPECTED_FILES[0]).read_text("utf-8"))
    v2=json.loads((root/EXPECTED_FILES[3]).read_text("utf-8"))
    cases=validate_research_json(fda,v2)
    watch=json.loads((root/"raas-v2-openfda-application-identity-watch.json").read_text("utf-8"))
    require(isinstance(watch,dict) and
            watch.get("scope")=="RAAS_V2_OPENFDA_NOV14_APPLICATION_IDENTITY_WATCH_NOT_VALIDATED"
            and watch.get("status")==
                "PUBLIC_DATABASE_MONITOR_ONLY_NOT_AN_FDA_CYCLE_OR_PREDICTION"
            and watch.get("openFdaSourceStatus") in {
                "AVAILABLE","HTTP_404_NO_PUBLIC_RECORD","SOURCE_UNAVAILABLE",
                "MALFORMED_RESPONSE"}
            and watch.get("independentlyCertifiedCurrentFdaReviewCycles")==0
            and watch.get("independentlyAdjudicatedNov14FdaActions")==0
            and watch.get("newImmutableThreeWayPredictions")==0
            and watch.get("approvedMetricCalibrations")==0
            and watch.get("canPromoteToFdaPredictionAccuracy") is False
            and isinstance(watch.get("cytk"),dict)
            and watch["cytk"].get("fdaApprovedFebruaryRemsS001IsNovemberMapleHcm") is False
            and watch["cytk"].get("mapleHcmCurrentSupplementNumberIndependentlyVerified") is False
            and watch["cytk"].get("newFdaMapleHcmApprovalIndependentlyAdjudicated") is False
            and isinstance(watch.get("smmt"),dict)
            and watch["smmt"].get("fdaCurrentBlaNumberIndependentlyVerified") is False
            and watch["smmt"].get("fdaPublicOpenFdaNoMatchingApprovedBlaProvesNoPendingBla") is False
            and isinstance(watch["smmt"].get("approvedProductIngredientSearch"),dict)
            and watch["smmt"]["approvedProductIngredientSearch"].get("publicSourceStatus") in {
                "NOT_QUERIED","AVAILABLE","HTTP_404_NO_PUBLIC_RECORD",
                "SOURCE_UNAVAILABLE","MALFORMED_RESPONSE"}
            and watch.get("smmtOpenFdaSourceStatus")==
                watch["smmt"]["approvedProductIngredientSearch"]["publicSourceStatus"]
            and type(watch.get("smmtPublicIndexedBlaCandidateCount")) is int
            and isinstance(watch["smmt"]["approvedProductIngredientSearch"].get(
                "matchingPublishedBlaCandidatesNeedIndependentReview"),list)
            and watch["smmtPublicIndexedBlaCandidateCount"]==len(
                watch["smmt"]["approvedProductIngredientSearch"][
                    "matchingPublishedBlaCandidatesNeedIndependentReview"])
            and watch["smmt"]["approvedProductIngredientSearch"].get(
                "fdaPendingBlaAbsentFromPublicIndexProvesNoSubmission") is False
            and watch["smmt"]["approvedProductIngredientSearch"].get(
                "fdaPublicIndexedCandidateIndependentlyMatchesSummitHARMONi") is False
            and watch["smmt"]["approvedProductIngredientSearch"].get(
                "fdaOriginalBlaCycleAndGoalVerified") is False
            and watch["smmt"]["approvedProductIngredientSearch"].get(
                "fdaApprovalCrlOrExtensionVerifiedFromIngredientSearch") is False
            and all(isinstance(c,dict) and
                c.get("pendingSMMTBlaNumberIndependentlyVerified") is False and
                c.get("sameEGFRmNSCLCHarmonIReviewCycleVerified") is False and
                c.get("fdaOutcomeFromPublicProductIndexVerified") is False
                for c in watch["smmt"]["approvedProductIngredientSearch"][
                    "matchingPublishedBlaCandidatesNeedIndependentReview"]),
            "PUBLIC_FDA_WATCH_CANNOT_PROMOTE_RESEARCH")
    sec=json.loads((root/"raas-v2-sec-nov14-new-filing-review-leads.json").read_text("utf-8"))
    require(isinstance(sec,dict) and sec.get("scope")==
        "RAAS_V2_SEC_NOV14_ISSUER_RECENT_FILINGS_LEADS_NOT_FDA_DECISIONS"
        and sec.get("status")==
        "ISSUER_FILING_LEADS_ONLY_NO_PDUFA_EXTENSION_VERIFICATION"
        and sec.get("monitoredIssuerFamilies")==2
        and sec.get("independentlyVerifiedNoFurtherFDAExtensions")==0
        and sec.get("independentlyVerifiedCurrentFDAApplicationCycles")==0
        and sec.get("newThreeWayForecastsFromFilings")==0
        and sec.get("approvedRAASMetricCalibrations")==0
        and type(sec.get("rows")) is list and len(sec["rows"])==2
        and {x.get("ticker") for x in sec["rows"]}=={"CYTK","SMMT"}
        and type(sec.get("sourceAvailableCount")) is int
        and sec["sourceAvailableCount"]==sum(x.get("sourceStatus")=="AVAILABLE"
            for x in sec["rows"])
        and sec.get("sourceCoverageStatus")==(
            "TWO_ISSUER_SOURCES_AVAILABLE" if sec["sourceAvailableCount"]==2
            else "PARTIAL_ISSUER_SOURCE_ACCESS" if sec["sourceAvailableCount"]==1
            else "ISSUER_SOURCES_UNAVAILABLE_NOT_ZERO_NEW_FILINGS")
        and type(sec.get("potentialNewFilingReviewCandidates")) is int
        and sec["potentialNewFilingReviewCandidates"]==sum(
            x.get("newerRelevantFormFilingCount",0) for x in sec["rows"])
        and all(
            x.get("sourceStatus") in {
                "AVAILABLE","HTTP_404_NO_PUBLIC_RECORD",
                "SOURCE_UNAVAILABLE","MALFORMED_RESPONSE"}
            and x.get("newFilingAutomaticallyMeansPdufaChange") is False
            and x.get("absenceOfNewFilingProvesNoFDAExtension") is False
            and x.get("independentlyVerifiedCurrentFDAApplicationCycle") is False
            and x.get("certifiedFDADeadlineRevision") is False
            and x.get("newThreeWayPredictionFrozen") is False
            and type(x.get("newerFilingReviewCandidates")) is list
            and x.get("newerRelevantFormFilingCount",0)>=len(
                x["newerFilingReviewCandidates"])
            and all(
                z.get("newerThanLastSelectedIssuerGoalSource") is True
                and z.get("documentReviewedForPdufaGoal") is False
                and z.get("fdaDeadlineRevisionConfirmed") is False
                and z.get("pendingFdaApplicationNumberConfirmed") is False
                and z.get("fdaActionOrPredictionConfirmed") is False
                for z in x["newerFilingReviewCandidates"])
            for x in sec["rows"]),
        "SEC_FILINGS_CANNOT_CERTIFY_FDA_REVIEW_OR_PREDICTIONS")
    require(
        type(sec.get("alternativeOfficialSecAtomAvailableCount")) is int
        and sec["alternativeOfficialSecAtomAvailableCount"]==sum(
            r.get("alternativeOfficialSecAtomFeed",{}).get("sourceStatus")
                =="AVAILABLE" for r in sec["rows"])
        and type(sec.get("effectiveOfficialSecFilingSourceCoverageCount")) is int
        and sec["effectiveOfficialSecFilingSourceCoverageCount"]==sum(
            r.get("sourceStatus")=="AVAILABLE" or
            r.get("alternativeOfficialSecAtomFeed",{}).get("sourceStatus")
                =="AVAILABLE" for r in sec["rows"])
        and type(sec.get("officialSecAtomResearchFilingCandidateCount")) is int
        and sec["officialSecAtomResearchFilingCandidateCount"]==sum(
            r.get("alternativeOfficialSecAtomFeed",{}).get(
                "newerRelevantFormFilingCount",0) for r in sec["rows"])
        and all(isinstance(r.get("alternativeOfficialSecAtomFeed"),dict)
            and r["alternativeOfficialSecAtomFeed"].get("sourceStatus") in {
                "NOT_QUERIED","AVAILABLE","SOURCE_UNAVAILABLE",
                "HTTP_404_NO_PUBLIC_RECORD","MALFORMED_RESPONSE"}
            and r["alternativeOfficialSecAtomFeed"].get(
                "atomFeedAloneVerifiesCompleteIssuerSECFileHistory") is False
            and r["alternativeOfficialSecAtomFeed"].get(
                "absenceFromAtomFeedProvesNoFdaDeadlineChange") is False
            and r["alternativeOfficialSecAtomFeed"].get(
                "aFilingLinkIdentifiesCurrentPendingBlaOrSNda") is False
            and r["alternativeOfficialSecAtomFeed"].get(
                "atomFeedAccessNotTheSameAsRestApiAccess") is True
            and type(r["alternativeOfficialSecAtomFeed"].get(
                "newerRelevantFormFilingCount")) is int
            and type(r["alternativeOfficialSecAtomFeed"].get(
                "newerFilingReviewCandidates")) is list
            and r["alternativeOfficialSecAtomFeed"]["newerRelevantFormFilingCount"]
                >=len(r["alternativeOfficialSecAtomFeed"][
                    "newerFilingReviewCandidates"])
            and all(c.get("documentReviewedForPdufaGoal") is False
                and c.get("fdaDeadlineRevisionConfirmed") is False
                and c.get("pendingFdaApplicationNumberConfirmed") is False
                and c.get("fdaActionOrPredictionConfirmed") is False
                for c in r["alternativeOfficialSecAtomFeed"][
                    "newerFilingReviewCandidates"])
            for r in sec["rows"]),
        "SEC_ATOM_CANNOT_CERTIFY_FDA_OR_RESTORE_REST_ACCESS")

    news=json.loads((root/"raas-v2-issuer-news-fallback-research-leads.json").read_text("utf-8"))
    require(isinstance(news,dict) and news.get("scope")==
        "RAAS_V2_OFFICIAL_ISSUER_NEWS_FALLBACK_SOURCE_LEADS_NOT_FDA_OR_SEC_CENSUS"
        and news.get("status")==
        "ISSUER_NEWS_FALLBACK_RESEARCH_ONLY_NOT_SEC_OR_FDA_COVERAGE"
        and news.get("officialIssuerNewsPagesChecked")==2
        and news.get("secOfficialFilingsAccessRestoredByFallback") is False
        and news.get("newCurrentPendingApplicationNumbersIndependentlyVerified")==0
        and news.get("independentlyVerifiedFdaDeadlineRevisions")==0
        and news.get("newThreeWayPredictionsFromIssuerNews")==0
        and news.get("approvedRAASMetricCalibrations")==0
        and type(news.get("rows")) is list
        and len(news["rows"])==2
        and {x.get("ticker") for x in news["rows"]}=={"CYTK","SMMT"}
        and type(news.get("officialIssuerNewsPagesAccessible")) is int
        and news["officialIssuerNewsPagesAccessible"]==sum(
            x.get("pageAccessible") is True for x in news["rows"])
        and type(news.get("issuerNewsResearchLinkCandidatesFound")) is int
        and news["issuerNewsResearchLinkCandidatesFound"]==sum(
            x.get("issuerArticleLinksFound",0) for x in news["rows"])
        and all(x.get("sourceStatus") in {
            "AVAILABLE","SOURCE_UNAVAILABLE","HTTP_404_NO_PUBLIC_RECORD",
            "MALFORMED_RESPONSE"}
            and x.get("pageAccessible") is (x.get("sourceStatus")=="AVAILABLE")
            and x.get("issuerNewsPageAccessibleButNoArticlesParsedIsNoNews") is False
            and x.get("issuerNewsIsComprehensiveSECDisclosureFeed") is False
            and x.get("issuerArticleLinkCertifiesFdaDeadlineOrApplicationNumber") is False
            and x.get("sec403FixedByThisIssuerNewsSource") is False
            and type(x.get("listedResearchLinkCandidates")) is list
            and type(x.get("issuerArticleLinksFound")) is int
            and x["issuerArticleLinksFound"]>=len(x["listedResearchLinkCandidates"])
            and all(z.get("verifiedPublishedAfterLastReviewedGoalSource") is False
                and z.get("articleContentReviewedForPdufaChange") is False
                and z.get("pendingFdaApplicationNumberVerified") is False
                and z.get("officialFdaActionOrExtensionVerified") is False
                for z in x["listedResearchLinkCandidates"])
            for x in news["rows"]),
        "ISSUER_NEWS_CANNOT_CERTIFY_SEC_FDA_OR_FORECAST")
    t_fda=timestamp(fda["asOfUTC"])
    t_v2=timestamp(v2["evaluatedAtUTC"])
    t_watch=timestamp(watch["checkedAtUTC"])
    t_sec=timestamp(sec["checkedAtUTC"])
    t_news=timestamp(news["checkedAtUTC"])
    require(t_fda <= archive_clock and t_v2 <= archive_clock and
            t_watch <= archive_clock and t_sec <= archive_clock and
            t_news <= archive_clock and
            abs((t_fda-t_v2).total_seconds()) <= 600
            and abs((t_watch-t_v2).total_seconds()) <= 3600
            and (archive_clock-t_fda).total_seconds() <= 3600
            and (archive_clock-t_v2).total_seconds() <= 3600
            and (archive_clock-t_watch).total_seconds() <= 3600
            and (archive_clock-t_sec).total_seconds() <= 3600
            and abs((t_sec-t_v2).total_seconds()) <= 3600
            and (archive_clock-t_news).total_seconds() <= 3600
            and abs((t_news-t_v2).total_seconds()) <= 3600,
            "OUTPUT_CLOCK_OR_ORDER_INCONSISTENT")
    with (root/"raas-v2-prospective-source-review.csv").open(newline="",encoding="utf-8") as f:
        csv_rows=list(csv.DictReader(f))
    require(len(csv_rows)==len(cases) and
            {r.get("researchCaseKey") for r in csv_rows} ==
            {r.get("researchCaseKey") for r in cases},
            "V2_CSV_JSON_CASE_ID_DISAGREEMENT")
    require(sum(r["knownRevisedGoalNotOriginalPrediction"]=="True"
                for r in csv_rows) ==
            v2["knownRevisedDeadlineExcludedFromOriginalGoalCount"],
            "V2_CSV_REVISED_GOAL_COUNT_DISAGREEMENT")
    return {
        "schemaVersion":1,
        "scope":"RAAS_V2_GITHUB_SOURCE_RESEARCH_PROVENANCE_NOT_PREDICTION_RECEIPT",
        "status":"RESEARCH_SOURCE_BYTES_CHECKSUMMED_NOT_INDEPENDENTLY_VALIDATED",
        "archivedAtUTC":archived_at,
        "sourceCommitSHA":sha,
        "githubRepository":repo,
        "githubWorkflowRunId":run_id,
        "githubWorkflowRunURL":f"https://github.com/{repo}/actions/runs/{run_id}",
        "activeFoundationVersion":"2026-11-02-foundation-v1",
        "v2Status":"V2_RESEARCH_CANDIDATE_STAGE_0",
        "sourceResearchCases":len(cases),
        "revisedPdufaTargetsExcludedFromOriginalGoalResearchCount":
            v2["knownRevisedDeadlineExcludedFromOriginalGoalCount"],
        "independentlyCertifiedThreeWayForecasts":0,
        "independentlyValidatedFDAAccuracyPct":None,
        "approvedRAASMetricCalibrations":0,
        "publicFdaWatchSourceStatus":watch["openFdaSourceStatus"],
        "secNewIssuerFilingSourceAvailabilityCount":sec["sourceAvailableCount"],
        "secNewIssuerFilingReviewCandidatesCount":sec["potentialNewFilingReviewCandidates"],
        "secNewIssuerFilingsConfirmFDARevision":False,
        "alternativeOfficialSecAtomAvailableCount":
            sec["alternativeOfficialSecAtomAvailableCount"],
        "effectiveOfficialSecFilingSourceCoverageCount":
            sec["effectiveOfficialSecFilingSourceCoverageCount"],
        "officialSecAtomResearchFilingCandidateCount":
            sec["officialSecAtomResearchFilingCandidateCount"],
        "atomFilingLinksDoNotVerifyFdaDecisions":True,
        "officialIssuerNewsPagesAccessible":news["officialIssuerNewsPagesAccessible"],
        "officialIssuerNewsLinksNotFDAOrSECCensus":news["issuerNewsResearchLinkCandidatesFound"],
        "officialIssuerNewsRestoresSECAccess":False,
        "publicFdaWatchCurrentMapleSupplementIndependentlyVerified":False,
        "publicFdaWatchCurrentSummitBlaIndependentlyVerified":False,
        "fileDigests":contents,
        "warning":"This checksum detects post-upload changes to the eight output files, but the GitHub Actions artifact can expire or be deleted. It does not independently attest source authenticity, freeze a predicted class, establish FDA outcomes or authorize RAAS V2.",
    }


def write_manifest(data, path):
    require(data.get("scope") ==
            "RAAS_V2_GITHUB_SOURCE_RESEARCH_PROVENANCE_NOT_PREDICTION_RECEIPT"
            and data.get("independentlyCertifiedThreeWayForecasts")==0
            and data.get("independentlyValidatedFDAAccuracyPct") is None,
            "MANIFEST_CANNOT_PROMOTE_FORECAST")
    p=Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n","utf-8")


def main():
    from datetime import datetime
    root=os.environ.get("RAAS_SOURCE_REPORTS_DIRECTORY")
    output=os.environ.get("RAAS_V2_SOURCE_PROVENANCE_JSON")
    require(bool(root) and bool(output), "SOURCE_DESTINATION_REQUIRED")
    stamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    m=build_manifest(root, os.environ.get("GITHUB_REPOSITORY",""),
                     os.environ.get("GITHUB_RUN_ID",""),
                     os.environ.get("GITHUB_SHA",""), stamp)
    write_manifest(m,output)
    print(json.dumps({"status":m["status"],"sourceResearchCases":m["sourceResearchCases"],
                      "filesHashed":len(m["fileDigests"]),
                      "approvedMetricCalibrations":0},sort_keys=True))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as f:
            f.write("\n### RAAS V2 daily research source checksums (NOT frozen forecasts)\n\n"
                    +f"Archived at {stamp} from commit {m['sourceCommitSHA']}.\n\n"
                    +"8 source files hashed. These are NOT signed prediction receipts.\n")


if __name__=="__main__":
    main()
