#!/usr/bin/env python3
"""RAAS V2 *candidate* stage-0 readiness, not a deployed prediction model.

Generate a day-specific, issuer-deduplicated pregoal source checklist from
existing October 2026 legacy binary freezes. The legacy cases are only
public-source RESEARCH LEADS; they are not independently verified NDA/BLA
cycles, three-way probability forecasts, complete FDA cohorts, RAAS ratings,
or approved trading windows. Never convert this report to a forecast ledger.
"""
from collections import Counter, defaultdict
from datetime import date
import csv
import json
import os
from pathlib import Path

import raas_fda_decision_accuracy_audit as audit

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
VERSION="V2_RESEARCH_CANDIDATE_STAGE_0"
SCOPE="RAAS_V2_PROSPECTIVE_ORIGINAL_GOAL_SOURCE_READINESS_NOT_VALIDATED"
ARCHIVE_SCOPE="RAAS_2025_NINE_ARCHIVE_GOAL_EVIDENCE_TRIAGE_RESEARCH_ONLY"
ASOF="2026-11-03T23:59:59Z"
MISSING_FLAGS=("originalGoalConfirmed","applicationCycleVerified",
               "predecisionThreeWayProbabilitiesFrozen","independentlyVerifiedFDAOutcome")
STAGE_REQUIREMENTS=(
    ("ORIGINAL_GOAL", "Original PDUFA goal, publication date and any revisions"),
    ("EXACT_CYCLE", "Verified NDA/BLA application ID, review cycle and indication"),
    ("PREDECISION_SOURCES", "Dated public efficacy, safety, CMC, filing and review sources"),
    ("ISSUER_IDENTITY", "Independently mapped issuer-program family and complete eligible cohort"),
    ("THREE_WAY_RECEIPT", "Precommitted immutable PASS / CRL / EXTENSION probability vector"),
    ("FDA_DISPOSITION", "Independent first-original-goal FDA action or formal extension adjudication"),
    ("EXTERNAL_VALIDATION", "Issuer-disjoint holdout, baseline, calibration and coverage reviewed"),
)


def assert_safe(condition, problem):
    if not condition:
        raise ValueError("RAAS_V2_READINESS_"+problem)


def priority(days_until):
    assert_safe(type(days_until) is int, "DAYS_UNTIL_NOT_INTEGER")
    if days_until < 0:
        return "PAST_UNVERIFIED_GOAL_INVESTIGATE_OUTCOME"
    if days_until <= 7:
        return "URGENT_WITHIN_7_DAYS"
    if days_until <= 30:
        return "PRIORITY_WITHIN_30_DAYS"
    return "PENDING_MORE_THAN_30_DAYS"


def validate_archive(archive):
    assert_safe(type(archive) is dict and archive.get("schemaVersion")==1
                and archive.get("scope")==ARCHIVE_SCOPE
                and archive.get("originalArchiveUnverifiedRows")==9
                and archive.get("formalExtensionSourceLeads")==2
                and archive.get("independentlyAdjudicatedFDAThreeWayOutcomes")==0
                and archive.get("independentProspectiveForecasts")==0
                and archive.get("approvedTrainingCases")==0
                and archive.get("full2025OriginalGoalCensus") is False
                and type(archive.get("records")) is list
                and len(archive["records"])==9,
                "ARCHIVE_APPROVAL_OR_SOURCE_SCHEMA_INVALID")
    seen=set()
    for row in archive["records"]:
        assert_safe(type(row) is dict and
                    isinstance(row.get("ticker"),str) and
                    row.get("caseId")=="ARCHIVE_2025_"+row["ticker"] and
                    row["caseId"] not in seen, "ARCHIVE_DUPLICATE_OR_INVALID_TICKER")
        seen.add(row["caseId"])
        first=audit.day(row["firstCycleGoalDate"])
        archived=audit.day(row["archivedSuggestedGoalDate"])
        assert_safe(row.get("FDAOriginalGoalDispositionIndependentlyAdjudicated") is False
                    and row.get("eligibleForFDAProspectiveAccuracy") is False
                    and row.get("eligibleForRAASTradeTraining") is False
                    and row.get("originalGoalSourceIndependentlyCertified") is False,
                    "ARCHIVE_INDEPENDENT_ADJUDICATION_NOT_ESTABLISHED")
        if row.get("revision") is None:
            assert_safe(first==archived and row.get("isLaterGoalRevised") is False,
                        "ARCHIVE_UNEXPLAINED_LATE_GOAL")
        else:
            r=row["revision"]
            assert_safe(type(r) is dict and row.get("isLaterGoalRevised") is True and
                        archived==audit.day(r["newDate"]) and
                        audit.day(r["publicDate"])<first<archived and
                        row.get("observedOriginalGoalResearchLabel")=="EXTENSION_RESEARCH_LEAD",
                        "ARCHIVE_REVISION_CHRONOLOGY_INVALID")
    return archive


def validate_top8_source_intake(intake, old_rows, as_of):
    """Contemporaneous issuer/Securities & Exchange source references, never FDA grade.
    Date and cycle controls reject trying to use original-goal review when the
    real first goal was already formally extended.
    """
    assert_safe(type(intake) is dict and intake.get("schemaVersion")==1 and
                intake.get("scope")==
                "RAAS_V2_TOP8_2026_ISSUER_GOAL_PUBLICATION_SOURCE_RESEARCH_NOT_VALIDATED" and
                intake.get("goalSourceLeads")==8 and
                intake.get("issuerPublicationSourcesLocated")==8 and
                intake.get("caseCountIndependentlyCertified")==0 and
                intake.get("independentlyVerifiedOriginalGoalFDAOutcomeCases")==0 and
                intake.get("scoredThreeWayForecasts")==0 and
                intake.get("independentlyCalibratedRaasMetrics")==0 and
                intake.get("eligibleForPredictionFreeze")==0 and
                intake.get("activeScoringVersion")=="2026-11-02-foundation-v1" and
                type(intake.get("records")) is list and len(intake["records"])==8,
                "TOP8_SOURCE_GATES_OR_SCHEMA_INVALID")
    allowed={
        "CYTK":"SUPPLEMENTAL_NDA",
        "SMMT":"ORIGINAL_BLA_REPORTED",
        "CAPR":"REVISED_BLA_TARGET_AFTER_FORMAL_EXTENSION",
        "BBIO":"ORIGINAL_NDA_REPORTED",
        "VRTX":"ORIGINAL_BLA_REPORTED",
        "ANAB":"LICENSED_THIRD_PARTY_BLA_SPONSOR",
        "CORT":"NDA_RESUBMISSION_AFTER_PRIOR_CRL",
        "MLYS":"ORIGINAL_NDA_REPORTED",
    }
    legacy={r.get("fda_regulatory_case_id"):r for r in old_rows if
            r.get("model_version")=="FDA-DIRECTIONAL-100-V1.9"}
    assert_safe(len(legacy)==40,"TOP8_LEGACY_CASES_NOT_UNIQUE")
    cutoff=audit.utc(as_of).date()
    seen=set()
    result=[]
    for r in intake["records"]:
        assert_safe(type(r) is dict, "TOP8_CASE_NOT_OBJECT")
        ticker=r.get("ticker")
        key=r.get("legacyCaseKey")
        audit.identity(key)
        assert_safe(ticker in allowed and ticker not in seen and
                    r.get("applicationType")==allowed[ticker] and
                    key in legacy and legacy[key]["ticker"]==ticker and
                    r.get("legacyGoalDate")==legacy[key]["pdufa_date"],
                    "TOP8_LEGACY_OR_APPLICATION_IDENTITY_MISMATCH")
        seen.add(ticker)
        proposed=audit.day(r["legacyGoalDate"])
        publication=audit.day(r["sourcePublicationDate"])
        first_goal=audit.day(r["firstCycleGoalDate"])
        assert_safe(first_goal<=proposed and publication<=cutoff and
                    isinstance(r.get("issuerSourceUrl"),str) and
                    r["issuerSourceUrl"].startswith("https://") and
                    isinstance(r.get("clinicalSponsor"),str) and
                    r["clinicalSponsor"].strip() and
                    isinstance(r.get("stockExposure"),str) and
                    r["stockExposure"].strip() and
                    isinstance(r.get("notes"),str) and r["notes"].strip(),
                    "TOP8_ISSUER_PUBLICATION_OR_DATE_INVALID")
        assert_safe(r.get("sourceDocumentLocated") is True and
                    all(r.get(k) is False for k in (
                        "earliestGoalPublicationIndependentlyAttested",
                        "applicationNumberIndependentlyVerified",
                        "exactReviewCycleIndependentlyVerified",
                        "issuerSponsorRightsIndependentlyReconciled",
                        "prospectivelyFrozenThreeWayProbabilities",
                        "independentlyAdjudicatedGoalDisposition",
                        "enrolledInV2ProspectiveCohort",
                        "FDAThreeWayAccuracyQualified",
                        "approvalForTradingModel")),
                    "TOP8_UNJUSTIFIED_APPROVAL_OR_INDEPENDENCE")
        rev=r.get("formalGoalRevision")
        if ticker=="CAPR":
            assert_safe(type(rev) is dict and
                        first_goal.isoformat()=="2026-08-22" and
                        proposed.isoformat()=="2026-11-22" and
                        rev.get("revisedGoalDate")=="2026-11-22" and
                        rev.get("firstPublicDate")=="2026-08-24" and
                        audit.day(rev["firstPublicDate"])<=cutoff and
                        isinstance(rev.get("sourceUrl"),str) and
                        rev["sourceUrl"]==r["issuerSourceUrl"],
                        "TOP8_CAPR_ORIGINAL_GOAL_EXTENSION_INVALID")
        else:
            assert_safe(rev is None and first_goal==proposed,
                        "TOP8_NOT_FORMAL_EXTENSION_ORIGINAL_CYCLE")
        if ticker=="ANAB":
            assert_safe("Vanda" in r["clinicalSponsor"] and
                        "Anaptys" in r["stockExposure"] and
                        r["clinicalSponsor"]!=r["stockExposure"],
                        "TOP8_ANAB_LICENSED_SPONSOR_NOT_RECONCILED")
        if ticker=="CORT":
            assert_safe("RESUBMISSION" in r["applicationType"],
                        "TOP8_CORT_CRLS_MUST_BE_SEPARATE_CYCLES")
        result.append({
            "ticker":ticker,"researchCaseKey":key,"drug":r["drug"],
            "issuerPublishedCurrentGoalDate":proposed.isoformat(),
            "issuerGoalSourcePublicationDate":publication.isoformat(),
            "issuerGoalSourceUrl":r["issuerSourceUrl"],
            "issuerSourceLocatedAtAudit":True,
            "firstPublicGoalDateForThisCycleIndependentlyCertified":False,
            "applicationType":r["applicationType"],
            "clinicalApplicantOrSponsor":r["clinicalSponsor"],
            "publicStockExposure":r["stockExposure"],
            "firstReportedReviewCycleGoalDate":first_goal.isoformat(),
            "formalGoalRevision":rev,
            "originalGoalAlreadyPassedBeforeAudit":first_goal<cutoff,
            "stillNeedsExactCycleAdjudication":True,
            "immutableThreeClassForecastVerified":False,
            "eligibleForApprovedPredictiveAccuracy":False,
            "notes":r["notes"]
        })
    assert_safe(set(allowed)==seen,"TOP8_SOURCE_COVERAGE_NOT_COMPLETE")
    result.sort(key=lambda r:(r["issuerPublishedCurrentGoalDate"],r["ticker"]))
    return result


def compile_report(*, old_rows, archive, protocol, roster, forecasts, outcomes, as_of):
    """No acceptance of old directional calls as FDA 3-way forecasts."""
    as_of_dt=audit.utc(as_of)
    cutoff=as_of_dt.date()
    source=validate_archive(archive)
    cases,preds,labels=audit.parse_prospective(protocol,roster,forecasts,outcomes)
    research=audit.legacy_future_source_queue(old_rows,as_of)
    seen=set()
    groups=defaultdict(list)
    pending=[]
    for row in research:
        k=row["researchCaseKey"]
        assert_safe(k not in seen and
                    row["status"]=="SOURCE_QUEUE_ONLY_NOT_THREE_WAY_FORECAST"
                    and all(row.get(field) is False for field in MISSING_FLAGS)
                    and k not in cases and k not in preds and k not in labels,
                    "LEGACY_DIRECTION_PROMOTED_OR_DUPLICATE")
        seen.add(k)
        goal=audit.day(row["legacyReportedGoalDateNotVerified"])
        assert_safe(goal>cutoff, "FUTURE_GOAL_QUEUE_HAS_MATURED_CASE")
        frozen=audit.utc(row["legacyBinaryFreezeUTC"])
        assert_safe(frozen.date()<goal, "BINARY_FREEZE_AFTER_GOAL")
        ticker=row["ticker"]
        assert_safe(isinstance(ticker,str) and ticker.strip() and len(ticker)<15,
                    "UNTRUSTED_TICKER")
        days=(goal-cutoff).days
        groups[ticker].append(k)
        pending.append({
            "researchCaseKey":k,"ticker":ticker,"drug":row["drug"],
            "legacyGoalDateUnverified":goal.isoformat(),
            "calendarDaysUntilLegacyGoal":days,"priority":priority(days),
            "historicalBinaryFreezeAtUTC":row["legacyBinaryFreezeUTC"],
            "originalGoalPrimarySourceVerified":False,
            "exactApplicationReviewCycleVerified":False,
            "publicSourceTimelineVerified":False,
            "independentCohortIssuerFamilyVerified":False,
            "immutablePreactionThreeWayProbabilityVector":False,
            "independentFDAOriginalGoalOutcome":False,
            "approvedRAASMetricGrade":False,"V2ForecastEligible":False,
            "sourceChecklist":[{"code":c,"requirement":t,"status":"NOT_YET_VERIFIED"}
                               for c,t in STAGE_REQUIREMENTS],
            "researchStatus":"SOURCE_REVIEW_ONLY_NOT_THREE_WAY_PREDICTION",
        })
    pending.sort(key=lambda r:(r["legacyGoalDateUnverified"],r["researchCaseKey"]))
    archive_summary=[]
    for x in source["records"]:
        r=x.get("revision")
        archive_summary.append({
            "ticker":x["ticker"],"caseId":x["caseId"],
            "archivedGoalDate":x["archivedSuggestedGoalDate"],
            "originalGoalDate":x["firstCycleGoalDate"],
            "revisionEvidenceDate":r["publicDate"] if r else None,
            "revisedGoalDate":r["newDate"] if r else None,
            "firstGoalSourceUrl":x.get("goalSourceUrl"),
            "revisionEvidenceUrl":r["url"] if r else None,
            "researchDisposition":x["observedOriginalGoalResearchLabel"],
            "independentlyVerifiedThreeWayOutcome":False
        })
    archive_summary.sort(key=lambda r:(r["originalGoalDate"],r["ticker"]))
    counts=Counter(r["priority"] for r in pending)
    return {
        "schemaVersion":1,"scope":SCOPE,"version":VERSION,
        "modelVersionStillActive":"2026-11-02-foundation-v1",
        "evaluatedAtUTC":as_of,
        "status":"RESEARCH_V2_CANDIDATE_NOT_AN_APPROVED_MODEL",
        "sourceQueueCount":len(pending),
        "distinctLegacyIssuerTickers":len(groups),
        "multipleLegacyEventsSameIssuer":
            {ticker:len(ids) for ticker,ids in sorted(groups.items()) if len(ids)>1},
        "readyForThreeWayProspectiveFreeze":0,
        "verifiedProspectiveForecasts":0,
        "independentlyVerifiedThreeWayAccuracyPct":None,
        "approvedRAASMetricCalibrations":0,
        "issuerDisjointHoldoutVerified":False,
        "originalGoalCensusVerified":False,
        "byPriority":{
            c:int(counts.get(c,0)) for c in
            ("URGENT_WITHIN_7_DAYS","PRIORITY_WITHIN_30_DAYS",
             "PENDING_MORE_THAN_30_DAYS","PAST_UNVERIFIED_GOAL_INVESTIGATE_OUTCOME")
        },
        "blockedSourceItems":pending,
        "archived2025OriginalGoalReviewCount":len(archive_summary),
        "archived2025FormalExtensionLeads":len([r for r in archive_summary
                                                 if r["revisedGoalDate"] is not None]),
        "archived2025GoalResearch":archive_summary,
        "nextReviewAction":
          "Verify earliest announced original PDUFA goal and exact NDA/BLA cycle "
          "for each selected upcoming case, acquire dated public evidence and "
          "independent issuer identity, then PRE-REGISTER and time-stamp a three-way "
          "forecast BEFORE FDA action. No score without independently verified input.",
        "warnings":[
          "RAAS V2 is a source-readiness CANDIDATE, not installed calibrated V2; V1 remains deployed.",
          "Past frozen 2026 binary directions never turn into three-way forecasts.",
          "Future dates and drugs are unverified issuer research leads, not a complete prospective FDA application census.",
          "Earlier 2025 archive outcome evidence is retrospective and cannot count as predecision FDA model accuracy.",
          "Ticker counts are NOT independent issuer families; same issuer may have several programs.",
          "No overnight processing by itself produces independent review, immutable forecast attestations, validated price parity, or an approved RAAS grade."
        ],
    }


def execute(asof=ASOF, data=DATA):
    folder=Path(data)
    old_rows=audit.csv_rows(folder/"fda_directional_100pct_freezes.csv")
    report=compile_report(
        old_rows=old_rows,
        archive=audit.load_json(ROOT/"new-platform/frontend/data/raas-2025-nine-archived-goal-original-source-triage.json"),
        protocol=audit.load_json(folder/"raas_fda_three_way_protocol.json"),
        roster=audit.load_json(folder/"raas_fda_three_way_eligible_cases.json"),
        forecasts=audit.load_json(folder/"raas_fda_three_way_frozen_forecasts.json"),
        outcomes=audit.load_json(folder/"raas_fda_three_way_outcomes.json"),
        as_of=asof)
    source=audit.load_json(ROOT/"new-platform/frontend/data/raas-v2-top8-2026-source-intake.json")
    selected=validate_top8_source_intake(source,old_rows,asof)
    # Use the EXISTING eight-source ledger, enriching the SAME nightly CSV
    # rather than adding a conflicting calendar. No independent review claim.
    findings={r["researchCaseKey"]:r for r in selected}
    reviewed=0
    revised=0
    for entry in report["blockedSourceItems"]:
        match=findings.get(entry["researchCaseKey"])
        entry["issuerSourceFound"]=False
        entry["issuerSourceLink"]=None
        entry["applicationClassIssuerReported"]=None
        entry["firstGoalForThisCycleIssuerReported"]=None
        entry["knownRevisedGoalNotOriginalPrediction"]=False
        entry["sourceResearchStatus"]="NOT_YET_SOURCE_REVIEWED"
        entry["independentlyVerifiedApplicationCycle"]=False
        if not match:
            continue
        reviewed+=1
        first=audit.day(match["firstReportedReviewCycleGoalDate"])
        listed=audit.day(entry["legacyGoalDateUnverified"])
        assert_safe(first<=listed and match["issuerPublishedCurrentGoalDate"]==
                    entry["legacyGoalDateUnverified"],
                    "ISSUER_SOURCE_MISMATCH_WITH_LEGACY_CASE_GOAL")
        is_revised=first<listed
        entry["issuerSourceFound"]=True
        entry["issuerSourceLink"]=match["issuerGoalSourceUrl"]
        entry["applicationClassIssuerReported"]=match["applicationType"]
        entry["firstGoalForThisCycleIssuerReported"]=first.isoformat()
        entry["knownRevisedGoalNotOriginalPrediction"]=is_revised
        entry["sourceResearchStatus"]=(
            "REVISED_GOAL_MUST_NOT_COUNT_AS_FUTURE_ORIGINAL_DEADLINE"
            if is_revised else "ISSUER_GOAL_LOCATED_EXACT_CYCLE_STILL_UNVERIFIED")
        revised+=int(is_revised)
    report["issuerSourceReviewedFutureDeadlineLeads"]=reviewed
    report["sourceDocumentedFirstGoalStillFuture"]=reviewed-revised
    report["knownRevisedDeadlineExcludedFromOriginalGoalCount"]=revised
    report["unreviewedLegacyDeadlineLeads"]=report["sourceQueueCount"]-reviewed
    report["unexcludedLegacyDeadlineLeadsNotIndependentlyVerified"]=(
        report["sourceQueueCount"]-revised)
    report["newSourceIntakeStage"]="EIGHT_ISSUER_PUBLISHED_GOAL_SOURCES_FOUND_NOT_INDEPENDENTLY_CERTIFIED"
    report["issuerPublishedGoalSourceLeadsCount"]=len(selected)
    report["independentlyCertifiedOriginalGoalRecords"]=0
    report["caseCycleAndSponsorSourceChecks"]=selected
    report["sourceIntakeStillExcludedFromApprovedFDAAccuracy"]=True
    report["clinicalReviewCycleRisks"]={
        "supplemental":1,"previouslyExtendedOriginalGoalAlreadyPassed":1,
        "licensedThirdPartySponsor":1,"resubmissionAfterCRL":1
    }
    # Source references are useful evidence-gathering progress; never
    # override independentlyVerified flags in the original 36-case queue.
    return report


def export(report, json_out, csv_out):
    assert_safe(report.get("scope")==SCOPE and report.get("status")==
                "RESEARCH_V2_CANDIDATE_NOT_AN_APPROVED_MODEL" and
                report.get("readyForThreeWayProspectiveFreeze")==0 and
                report.get("approvedRAASMetricCalibrations")==0,
                "EXPORT_CANNOT_APPROVE_MODEL")
    path=Path(json_out)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    path=Path(csv_out)
    path.parent.mkdir(parents=True,exist_ok=True)
    keys=["researchCaseKey","ticker","drug","legacyGoalDateUnverified",
          "calendarDaysUntilLegacyGoal","priority",
          "originalGoalPrimarySourceVerified","exactApplicationReviewCycleVerified",
          "publicSourceTimelineVerified","independentCohortIssuerFamilyVerified",
          "immutablePreactionThreeWayProbabilityVector",
          "independentFDAOriginalGoalOutcome","researchStatus",
          "issuerSourceFound","applicationClassIssuerReported",
          "firstGoalForThisCycleIssuerReported","knownRevisedGoalNotOriginalPrediction",
          "sourceResearchStatus","issuerSourceLink",
          "independentlyVerifiedApplicationCycle"]
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys,extrasaction="ignore")
        w.writeheader()
        w.writerows(report["blockedSourceItems"])


def main():
    import datetime
    asof=os.getenv("RAAS_V2_ASOF_UTC",datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    report=execute(asof)
    export(report,
           os.getenv("RAAS_V2_SOURCE_STATUS_JSON",str(ROOT/"raas-v2-prospective-source-readiness.json")),
           os.getenv("RAAS_V2_SOURCE_STATUS_CSV",str(ROOT/"raas-v2-prospective-source-review.csv")))
    brief={k:report[k] for k in
           ("status","version","sourceQueueCount","distinctLegacyIssuerTickers",
            "byPriority","issuerPublishedGoalSourceLeadsCount",
            "issuerSourceReviewedFutureDeadlineLeads",
            "knownRevisedDeadlineExcludedFromOriginalGoalCount",
            "readyForThreeWayProspectiveFreeze",
            "verifiedProspectiveForecasts","approvedRAASMetricCalibrations")}
    print(json.dumps(brief,sort_keys=True))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as f:
            f.write("\n### RAAS V2 prospective candidate SOURCE readiness (NO FDA model approval)\n\n"
                    +json.dumps(brief,indent=2)+"\n")


if __name__=="__main__":
    main()
