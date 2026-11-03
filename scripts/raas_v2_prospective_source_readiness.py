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


def verify_near_term_cycle_sources(feed):
    """Issuer disclosures as research leads only; never independent NDA/BLA approval."""
    assert_safe(type(feed) is dict and feed.get("schemaVersion")==1
                and feed.get("scope")==
                "RAAS_V2_2026_NEAR_TERM_ISSUER_ORIGINAL_GOAL_RESEARCH_EVIDENCE"
                and feed.get("verifiedProspectiveFDADecisionForecasts")==0
                and feed.get("independentlyAdjudicatedThreeWayOutcomes")==0
                and feed.get("calibratedRAASMetrics")==0
                and type(feed.get("records")) is list
                and len(feed["records"])==3,
                "NEAR_TERM_SOURCE_SCOPE_OR_APPROVAL_INVALID")
    asof=audit.day(feed["sourceAsOf"])
    rows={}
    expected={"CYTK|MYQORZO_HCM_20261114",
              "SMMT|IVONESCIMAB_20261114",
              "CAPR|DERAMIOCEL_DMD_20261122"}
    classes={"SUPPLEMENTAL_NDA","BLA_INITIAL_ACCEPTANCE","BLA_CLASS_2_RESUBMISSION"}
    for r in feed["records"]:
        assert_safe(type(r) is dict and
                    r.get("legacyCaseKey") in expected and
                    r["legacyCaseKey"] not in rows and
                    r.get("issuerDocumentedApplicationClass") in classes and
                    r.get("independentExactApplicationCycleVerified") is False and
                    r.get("completeProspectiveCohortVerified") is False and
                    r.get("preactionThreeWayForecastVerified") is False,
                    "NEAR_TERM_UNVERIFIED_CYCLE_PROMOTION")
        legacy=audit.day(r["legacyGoalDate"])
        original=audit.day(r["firstAnnouncedGoalForThisReviewCycle"])
        observed=audit.day(r["goalFirstObservedPublicDate"])
        assert_safe(observed<=asof and observed<legacy and original<=legacy
                    and isinstance(r.get("issuerGoalSourceUrl"),str) and
                    r["issuerGoalSourceUrl"].startswith("https://")
                    and isinstance(r.get("issuerSourceNotes"),str)
                    and len(r["issuerSourceNotes"])>20,
                    "NEAR_TERM_PUBLIC_SOURCE_TIME_INVALID")
        revised=r.get("formallyRevisedGoal")
        if revised is True:
            assert_safe(r["ticker"]=="CAPR"
                        and r["issuerDocumentedApplicationClass"]=="BLA_CLASS_2_RESUBMISSION"
                        and original<legacy
                        and audit.day(r["revisionDisclosedAt"])>=original
                        and audit.day(r["revisionDisclosedAt"])<=asof
                        and isinstance(r.get("revisionSourceUrl"),str)
                        and r["revisionSourceUrl"].startswith("https://"),
                        "NEAR_TERM_REVISED_GOAL_INVALID")
        else:
            assert_safe(revised is False and legacy==original
                        and r.get("revisionDisclosedAt") is None
                        and r.get("revisionSourceUrl") is None,
                        "NEAR_TERM_UNEXPLAINED_ORIGINAL_GOAL_SHIFT")
        rows[r["legacyCaseKey"]]=r
    assert_safe(set(rows)==expected, "NEAR_TERM_SOURCE_RECORD_SET_INCOMPLETE")
    return rows


def compile_report(*, old_rows, archive, protocol, roster, forecasts, outcomes, as_of, near_term=None):
    """No acceptance of old directional calls as FDA 3-way forecasts."""
    as_of_dt=audit.utc(as_of)
    cutoff=as_of_dt.date()
    source=validate_archive(archive)
    near_term_rows=verify_near_term_cycle_sources(
        near_term if near_term is not None else
        audit.load_json(ROOT/"new-platform/frontend/data/raas-v2-upcoming-2026-cycle-source-research.json"))
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
    asof_near_term=audit.day(
        (near_term if near_term is not None else
         audit.load_json(ROOT/"new-platform/frontend/data/raas-v2-upcoming-2026-cycle-source-research.json"))["sourceAsOf"])
    source_reviewed=0
    revised_future_mislabels=0
    for entry in pending:
        finding=near_term_rows.get(entry["researchCaseKey"])
        entry["issuerCycleSourceResearchStatus"]="NOT_SOURCE_REVIEWED"
        entry["originalCycleGoalResearchDate"]=None
        entry["issuerApplicationTypeResearch"]=None
        entry["issuerOriginalGoalDocumentUrl"]=None
        entry["issuerGoalFirstObservedPublicAt"]=None
        entry["originalCycleGoalAlreadyPassed"]=False
        entry["futureOriginalGoalResearchEligible"]=False
        entry["revisedPdufaGoalMisclassifiedAsOriginal"]=False
        entry["independentlyVerifiedFDAOriginalGoalOutcome"]=False
        if finding is None:
            continue
        assert_safe(finding["legacyGoalDate"]==entry["legacyGoalDateUnverified"]
                    and finding["ticker"]==entry["ticker"],
                    "NEAR_TERM_FINDING_WRONG_CASE_OR_GOAL")
        if audit.day(finding["goalFirstObservedPublicDate"])>cutoff or asof_near_term>cutoff:
            continue
        source_reviewed+=1
        first=audit.day(finding["firstAnnouncedGoalForThisReviewCycle"])
        revised=first<audit.day(finding["legacyGoalDate"])
        entry["issuerCycleSourceResearchStatus"]=finding["sourceReviewStatus"]
        entry["originalCycleGoalResearchDate"]=first.isoformat()
        entry["issuerApplicationTypeResearch"]=finding["issuerDocumentedApplicationClass"]
        entry["issuerOriginalGoalDocumentUrl"]=finding["issuerGoalSourceUrl"]
        entry["issuerGoalFirstObservedPublicAt"]=finding["goalFirstObservedPublicDate"]
        entry["revisedPdufaGoalMisclassifiedAsOriginal"]=revised
        entry["originalCycleGoalAlreadyPassed"]=first<=cutoff
        entry["futureOriginalGoalResearchEligible"]=not revised and first>cutoff
        entry["revisionFirstPublicDisclosure"]=finding["revisionDisclosedAt"]
        entry["revisionSourceUrl"]=finding["revisionSourceUrl"]
        if revised:
            revised_future_mislabels+=1
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
        "nearTermSourceDocumentedOnlyNotIndependentlyVerified":True,
        "evaluatedAtUTC":as_of,
        "status":"RESEARCH_V2_CANDIDATE_NOT_AN_APPROVED_MODEL",
        "sourceQueueCount":len(pending),
        "nearTermIssuerGoalSourceReviewed":source_reviewed,
        "revisedGoalResearchCasesNotFutureOriginalGoals":revised_future_mislabels,
        "remainingLegacyGoalCasesWithoutIssuerSourceReview":len(pending)-source_reviewed,
        "issuerDocumentedFutureOriginalGoalCases":sum(
            int(x["futureOriginalGoalResearchEligible"]) for x in pending),
        "issuerDocumentedSupplementalFutureGoals":sum(
            int(x["issuerApplicationTypeResearch"]=="SUPPLEMENTAL_NDA"
                and x["futureOriginalGoalResearchEligible"]) for x in pending),
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
    report=compile_report(
        old_rows=audit.csv_rows(folder/"fda_directional_100pct_freezes.csv"),
        archive=audit.load_json(ROOT/"new-platform/frontend/data/raas-2025-nine-archived-goal-original-source-triage.json"),
        near_term=audit.load_json(ROOT/"new-platform/frontend/data/raas-v2-upcoming-2026-cycle-source-research.json"),
        protocol=audit.load_json(folder/"raas_fda_three_way_protocol.json"),
        roster=audit.load_json(folder/"raas_fda_three_way_eligible_cases.json"),
        forecasts=audit.load_json(folder/"raas_fda_three_way_frozen_forecasts.json"),
        outcomes=audit.load_json(folder/"raas_fda_three_way_outcomes.json"),
        as_of=asof)
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
          "independentFDAOriginalGoalOutcome","researchStatus"]
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
            "byPriority","nearTermIssuerGoalSourceReviewed",
            "revisedGoalResearchCasesNotFutureOriginalGoals",
            "readyForThreeWayProspectiveFreeze",
            "verifiedProspectiveForecasts","approvedRAASMetricCalibrations")}
    print(json.dumps(brief,sort_keys=True))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as f:
            f.write("\n### RAAS V2 prospective candidate SOURCE readiness (NO FDA model approval)\n\n"
                    +json.dumps(brief,indent=2)+"\n")


if __name__=="__main__":
    main()
