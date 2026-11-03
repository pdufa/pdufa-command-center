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



def validate_additional_formal_extensions(intake, old_rows, as_of):
    """Issuer-reported formal extensions are SOURCE leads, never prospective forecasts.

    SVRA/PRAX legacy rows contain revised goals; EXEL's older row still
    contains the original December goal despite its public September revision.
    Either pattern is barred from an *unresolved upcoming original-goal* cohort.
    """
    items=intake.get("additionalFormalRevisionCases")
    assert_safe(intake.get("additionalFormallyExtendedLegacyReviewLeads")==3
                and type(items) is list and len(items)==3,
                "FORMAL_EXTENSION_SOURCE_SCHEMA_INVALID")
    expected={
        "SVRA":("SVRA|MOLBREEVI_PAP_20261122","2026-08-22","2026-11-22","BLA"),
        "PRAX":("RELUTRIGINE_DEE_US_20261227","2026-09-27","2026-12-27","NDA"),
        "EXEL":("ZANZALINTINIB_CRC_US_20261203","2026-12-03","2027-03-03","NDA"),
    }
    legacy={r.get("fda_regulatory_case_id"):r for r in old_rows if
            r.get("model_version")=="FDA-DIRECTIONAL-100-V1.9"}
    cutoff=audit.utc(as_of).date()
    result=[]
    seen=set()
    for r in items:
        ticker=r.get("ticker")
        assert_safe(ticker in expected and ticker not in seen,
                    "FORMAL_EXTENSION_IDENTITY_INVALID")
        seen.add(ticker)
        key,original,revised,typ=expected[ticker]
        first=audit.day(r.get("firstCycleGoalDate"))
        last=audit.day(r.get("revisedGoalDate"))
        publication=audit.day(r.get("originalGoalPublicationDate"))
        revision=audit.day(r.get("formalExtensionAnnouncementDate"))
        assert_safe(r.get("legacyCaseKey")==key and
                    key in legacy and legacy[key]["ticker"]==ticker and
                    r.get("legacyGoalDate")==legacy[key]["pdufa_date"] and
                    first.isoformat()==original and last.isoformat()==revised and
                    r.get("applicationType")==typ and
                    r.get("legacyGoalDate") in {original,revised},
                    "FORMAL_EXTENSION_GOAL_CYCLE_MISMATCH")
        assert_safe(publication<=revision<=cutoff and
                    revision<first<last and
                    r.get("sourceDocumentLocated") is True and
                    all(r.get(x) is False for x in (
                        "exactApplicationCycleIndependentlyVerified",
                        "independentFDAOriginalGoalOutcome",
                        "prospectivelyFrozenThreeWayProbabilities",
                        "eligibleForV2OriginalGoalPrediction")) and
                    all(isinstance(r.get(x),str) and
                        r[x].startswith("https://") for x in
                        ("originalGoalSourceUrl","formalExtensionSourceUrl")) and
                    isinstance(r.get("clinicalSponsor"),str) and
                    bool(r["clinicalSponsor"].strip()) and
                    isinstance(r.get("notes"),str) and bool(r["notes"].strip()),
                    "FORMAL_EXTENSION_SOURCE_CHRONOLOGY_OR_PROMOTION_INVALID")
        result.append({
            "ticker":ticker,"researchCaseKey":key,
            "firstReportedReviewCycleGoalDate":original,
            "currentIssuerReportedRevisedGoalDate":revised,
            "legacyGoalDate":r["legacyGoalDate"],
            "applicationType":"FORMALLY_EXTENDED_"+typ,
            "originalGoalSourceUrl":r["originalGoalSourceUrl"],
            "formalExtensionSourceUrl":r["formalExtensionSourceUrl"],
            "formalExtensionAnnouncementDate":revision.isoformat(),
            "issuerSourceLocatedAtAudit":True,
            "independentlyCertifiedReviewCycle":False,
            "immutableThreeClassForecastVerified":False,
            "eligibleForApprovedPredictiveAccuracy":False,
            "legacyDateIsFormerOriginalGoal":r["legacyGoalDate"]==original,
            "notes":r["notes"],
        })
    assert_safe(seen==set(expected),"FORMAL_EXTENSION_COVERAGE_INCOMPLETE")
    return result



def validate_additional_original_goal_sources(intake, old_rows, as_of):
    """Locate issuer original-goal source leads; never independently certify them.

    Use the application-level case key rather than ticker because Cogent has
    separate GIST and NonAdvSM reviews. Pivotal Phase 2 is NOT equivalent to
    post-Phase-3 Pipeline qualification.
    """
    records=intake.get("additionalOriginalGoalIssuerSourceCases")
    assert_safe(intake.get("additionalOriginalGoalIssuerSourceLeads")==4 and
                type(records) is list and len(records)==4,
                "NEW_ORIGINAL_GOAL_SOURCE_SCHEMA_INVALID")
    expected={
        "COGT|BEZUCLASTINIB_GIST_20261130":
            ("COGT","2026-11-30","2026-05-28","ORIGINAL_NDA_REPORTED",
             "PHASE_3_REPORTED_PEAK"),
        "ANITOCEL_RRMM_US_20261223":
            ("GILD","2026-12-23","2026-02-23","ORIGINAL_BLA_REPORTED",
             "PIVOTAL_PHASE_2_REPORTED_IMMAGINE1"),
        "MR107A02_ACUTEPAIN_US_20261227":
            ("VTRS","2026-12-27","2026-05-18","ORIGINAL_NDA_REPORTED",
             "PHASE_NOT_INDEPENDENTLY_VERIFIED"),
        "BEZUCLASTINIB_NONADVSM_US_20261230":
            ("COGT","2026-12-30","2026-03-16","ORIGINAL_NDA_REPORTED",
             "PIVOTAL_PHASE_2_REPORTED_SUMMIT"),
    }
    legacy={r.get("fda_regulatory_case_id"):r for r in old_rows if
            r.get("model_version")=="FDA-DIRECTIONAL-100-V1.9"}
    as_of_date=audit.utc(as_of).date()
    result=[]
    seen=set()
    for row in records:
        key=row.get("legacyCaseKey")
        assert_safe(key in expected and key not in seen,
                    "NEW_ORIGINAL_GOAL_DUPLICATE_OR_WRONG_CASE")
        seen.add(key)
        ticker,goal,published,typ,phase=expected[key]
        audit.identity(key)
        publication=audit.day(row.get("sourcePublicationDate"))
        announced=audit.day(row.get("issuerReportedFirstGoalDate"))
        assert_safe(key in legacy and legacy[key]["ticker"]==ticker
                    and legacy[key]["pdufa_date"]==goal and
                    row.get("legacyGoalDate")==goal and
                    announced.isoformat()==goal and
                    publication.isoformat()==published and
                    publication<=as_of_date and publication<announced and
                    row.get("ticker")==ticker and
                    row.get("applicationType")==typ and
                    row.get("pivotalPhaseEvidence")==phase,
                    "NEW_ORIGINAL_GOAL_IDENTITY_OR_SOURCE_CLOCK_INVALID")
        assert_safe(row.get("sourceDocumentLocated") is True and
                    all(row.get(flag) is False for flag in (
                        "earliestGoalPublicationIndependentlyAttested",
                        "applicationNumberIndependentlyVerified",
                        "exactReviewCycleIndependentlyVerified",
                        "issuerSponsorRightsIndependentlyReconciled",
                        "originalDeadlineEverRevisedIndependentlyChecked",
                        "prospectivelyFrozenThreeWayProbabilities",
                        "independentlyAdjudicatedGoalDisposition",
                        "enrolledInV2ProspectiveCohort",
                        "FDAThreeWayAccuracyQualified",
                        "approvedPipelinePhase3Qualification",
                        "approvalForTradingModel")) and
                    all(isinstance(row.get(field),str) and
                        row[field].startswith("https://") and
                        len(row[field])<1200 for field in (
                            "issuerSourceUrl","phaseEvidenceSourceUrl")) and
                    isinstance(row.get("clinicalSponsor"),str) and
                    bool(row["clinicalSponsor"].strip()) and
                    isinstance(row.get("notes"),str) and bool(row["notes"].strip()),
                    "NEW_ORIGINAL_GOAL_INDEPENDENCE_OR_PROMOTION_INVALID")
        result.append({
            "ticker":ticker,"researchCaseKey":key,
            "issuerPublishedCurrentGoalDate":goal,
            "firstReportedReviewCycleGoalDate":goal,
            "issuerGoalSourcePublicationDate":publication.isoformat(),
            "issuerGoalSourceUrl":row["issuerSourceUrl"],
            "applicationType":typ,
            "pivotalPhaseEvidence":phase,
            "phaseEvidenceSourceUrl":row["phaseEvidenceSourceUrl"],
            "clinicalApplicantOrSponsor":row["clinicalSponsor"],
            "publicStockExposure":row["stockExposure"],
            "issuerSourceLocatedAtAudit":True,
            "firstPublicGoalDateForThisCycleIndependentlyCertified":False,
            "independentlyVerifiedApplicationCycle":False,
            "immutableThreeClassForecastVerified":False,
            "eligibleForApprovedPredictiveAccuracy":False,
            "approvedPipelinePhase3Qualification":False,
            "notes":row["notes"],
        })
    assert_safe(seen==set(expected),"NEW_ORIGINAL_GOAL_COVERAGE_INCOMPLETE")
    return result



def validate_nov14_trial_registry_triangulation(dossier, intake, old_rows, as_of):
    """NLM independent *trial* phase evidence; never independent FDA cycle proof.

    CYTK's FDA NDA approval letter refers to the *2025 original* application,
    NOT the November 2026 MAPLE-HCM supplemental FDA action. Both November
    goals continue to lack an independently certified numbered current cycle.
    """
    assert_safe(type(dossier) is dict and dossier.get("schemaVersion")==1 and
                dossier.get("scope")==
                "RAAS_V2_NOV14_2026_ISSUER_FDA_AND_REGISTRY_TRIANGULATION_RESEARCH_ONLY"
                and dossier.get("researchAsOf")=="2026-11-03" and
                dossier.get("casesCrossChecked")==2 and
                dossier.get("independentlyVerifiedCurrentApplicationCycleCount")==0
                and dossier.get("independentlyVerifiedFrozenThreeWayForecastCount")==0
                and dossier.get("approvedMetricCalibrations")==0 and
                type(dossier.get("records")) is list and len(dossier["records"])==2,
                "NOV14_REGISTRY_TRIANGULATION_SCHEMA_INVALID")
    cutoff=audit.utc(as_of).date()
    assert_safe(audit.day(dossier["researchAsOf"])<=cutoff,
                "NOV14_REGISTRY_TRIANGULATION_FUTURE_RESEARCH")
    expected={
        "CYTK|MYQORZO_HCM_20261114":
            ("CYTK","2026-05-05","NCT05767346","MAPLE-HCM","2026-06-09",
             "SUPPLEMENTAL_NDA","Cytokinetics"),
        "SMMT|IVONESCIMAB_20261114":
            ("SMMT","2026-01-29","NCT06396065","HARMONi","2026-07-28",
             "ORIGINAL_BLA_REPORTED","Summit Therapeutics")
    }
    originals={x["legacyCaseKey"]:x for x in intake["records"]}
    legacy={r.get("fda_regulatory_case_id"):r for r in old_rows if
            r.get("model_version")=="FDA-DIRECTIONAL-100-V1.9"}
    checked=[]
    seen=set()
    for row in dossier["records"]:
        key=row.get("researchCaseKey")
        assert_safe(key in expected and key not in seen,
                    "NOV14_REGISTRY_DUPLICATE_OR_WRONG_APPLICATION")
        seen.add(key)
        ticker,published,nct,study,registry_date,typ,sponsor=expected[key]
        original=originals[key]
        assert_safe(key in legacy and legacy[key]["ticker"]==ticker and
                    legacy[key]["pdufa_date"]=="2026-11-14" and
                    original["ticker"]==ticker and
                    original["applicationType"]==typ and
                    original["clinicalSponsor"]==sponsor and
                    row.get("ticker")==ticker and
                    row.get("applicationClass")==typ and
                    row.get("issuerReportedFirstGoalDate")==
                    original["firstCycleGoalDate"]=="2026-11-14" and
                    row.get("issuerGoalSourceUrl")==original["issuerSourceUrl"] and
                    row.get("issuerSourcePublicationDate")==
                    original["sourcePublicationDate"]==published and
                    row.get("clinicalTrialsGovId")==nct and
                    row.get("clinicalTrialsGovStudyName")==study and
                    row.get("clinicalTrialsGovRecordLastUpdatePosted")==registry_date
                    and row.get("clinicalTrialsGovPhase")=="PHASE_3" and
                    row.get("clinicalTrialsGovSponsor")==sponsor and
                    row.get("clinicalTrialsGovUrl")==
                    "https://clinicaltrials.gov/study/"+nct and
                    row.get("clinicalTrialsGovPhaseAndSponsorCrossChecked") is True,
                    "NOV14_REGISTRY_WRONG_TRIAL_OR_REVIEW_CYCLE")
        assert_safe(audit.day(published)<audit.day("2026-11-14") and
                    audit.day(registry_date)<=cutoff and
                    all(row.get(x) is False for x in (
                        "exactCurrentFDAReviewCycleIndependentlyCertified",
                        "independentlyVerifiedThreeWayForecast",
                        "approvedPipelineMarketCapAndPhase3Qualification",
                        "approvedRAASAccuracyMetric")) and
                    isinstance(row.get("notes"),str) and bool(row["notes"].strip()) and
                    isinstance(row.get("underReview"),str) and bool(row["underReview"].strip()),
                    "NOV14_REGISTRY_CHRONOLOGY_OR_FORECAST_PROMOTION_INVALID")
        if ticker=="CYTK":
            assert_safe(row.get("usFDAParentOriginalNdaNumber")=="219083" and
                        row.get("usFDAParentOriginalNdaApprovalDate")=="2025-12-19" and
                        row.get("usFDAParentOriginalApprovalLetterUrl")==
                        "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/219083Orig1s000Approv.pdf"
                        and row.get("usFDAParentOriginalNdaNumberCrossChecked") is True
                        and row.get("currentSupplementSequenceNumber") is None and
                        row.get("currentSupplementSequenceIndependentlyVerified") is False and
                        row.get("firstPublicGoalForSpecificSupplementIndependentlyAttested") is False and
                        row.get("anyPostAcceptanceFDAExtensionIndependentlyRuledOut") is False,
                        "NOV14_PARENT_NDA_NOT_CURRENT_SUPPLEMENT")
            # An FDA-approved unrelated safety-REMS supplement is NOT evidence
            # for the upcoming efficacy/data MAPLE-HCM review cycle.
            assert_safe(
                row.get("fdaPreviouslyApprovedUnrelatedSupplementNumber")=="S-001"
                and row.get("fdaPreviouslyApprovedUnrelatedSupplementApprovalDate")=="2026-02-05"
                and row.get("fdaPreviouslyApprovedUnrelatedSupplementPurpose")==
                    "REMS_MODIFICATION_NOT_MAPLE_HCM"
                and row.get("fdaPreviouslyApprovedUnrelatedSupplementSourceUrl")==
                    "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/219083Orig1s001ltr.pdf"
                and row.get("fdaPreviouslyApprovedS001IsNov14PendingMapleHcmSupplement") is False
                and row.get("fdaPreviouslyApprovedS001EstablishesNov14FDAOutcome") is False
                and row.get("specificPendingMAPLESupplementNumberIndependentlyVerified") is False
                and row.get("mapleHcmSubmissionPubliclyDisclosedAt")=="2026-02-24"
                and row.get("mapleHcmSubmissionPublicSourceUrl")==
                    "https://www.sec.gov/Archives/edgar/data/1061983/000119312526067012/cytk-ex99_1.htm"
                and row.get("mapleHcmFDAAcceptanceAndGoalFirstLocatedAt")=="2026-05-05"
                and row.get("mapleHcmFDAAcceptanceAndGoalSourceUrl")==
                    "https://www.sec.gov/Archives/edgar/data/1061983/000119312526206360/cytk-ex99_1.htm"
                and audit.day(row["fdaPreviouslyApprovedUnrelatedSupplementApprovalDate"])<
                    audit.day(row["mapleHcmSubmissionPubliclyDisclosedAt"])<
                    audit.day(row["mapleHcmFDAAcceptanceAndGoalFirstLocatedAt"])<
                    audit.day("2026-11-14"),
                "NOV14_FDA_S001_REMS_NOT_MAPLE_NEGATIVE_CONTROL")
        else:
            assert_safe(row.get("usFDAParentOriginalNdaNumber") is None and
                        row.get("usFDAParentOriginalNdaApprovalDate") is None and
                        row.get("usFDAParentOriginalApprovalLetterUrl") is None and
                        row.get("usFDAParentOriginalNdaNumberCrossChecked") is False
                        and row.get("currentBlaNumber") is None and
                        row.get("currentBlaNumberIndependentlyVerified") is False and
                        row.get("firstPublicGoalForSpecificBlaIndependentlyAttested") is False
                        and row.get("anyPostAcceptanceFDAExtensionIndependentlyRuledOut") is False,
                        "NOV14_BLA_NUMBER_OR_CYCLE_NOT_VERIFIED")
            assert_safe(
                row.get("fdaOSStatisticalSignificanceRequirementReportedBySponsor") is True
                and row.get("fdaOSStatisticalSignificanceRequirementPublicSourceUrl")==
                    "https://www.sec.gov/Archives/edgar/data/1599298/000159929826000068/smmt-20260630.htm"
                and row.get("pivotalPrimaryOverallSurvivalStatisticallySignificantAtPrimaryAnalysis") is False
                and type(row.get("pivotalPrimaryOverallSurvivalReportedPValue")) is float
                and row["pivotalPrimaryOverallSurvivalReportedPValue"]==0.057
                and row.get("pivotalPrimaryOverallSurvivalSourceUrl")==
                    "https://www.sec.gov/Archives/edgar/data/1599298/000159929826000058/a2026_prx0722xharmonidat.htm"
                and row.get("laterOverallSurvivalFollowUpSourceDate")=="2026-09-15"
                and row.get("laterOverallSurvivalFollowUpSourceUrl")==
                    "https://www.sec.gov/Archives/edgar/data/1599298/000159929826000081/a2026_prx0915xharmoniltf.htm"
                and audit.day(row["laterOverallSurvivalFollowUpSourceDate"])<=cutoff
                and row.get("laterOverallSurvivalFollowUpEstablishesFDAApprovalOrExtension") is False
                and row.get("fdaOSRequirementAndStudyDataAutomaticallyEstablishCRL") is False,
                "NOV14_SMMT_OS_EVIDENCE_NOT_FDA_OUTCOME_OR_PREDICTION")
        checked.append({
            "ticker":ticker,"researchCaseKey":key,
            "issuerReportedFirstGoalDate":"2026-11-14",
            "applicationClass":typ,
            "clinicalTrialsGovId":nct,
            "clinicalTrialsGovPhase":"PHASE_3",
            "clinicalTrialsGovRegistryEvidenceUrl":row["clinicalTrialsGovUrl"],
            "trialPhaseAndSponsorCrossChecked":True,
            "fdaApprovedParentNdaNumber":row["usFDAParentOriginalNdaNumber"],
            "fdaParentOriginalNdaEvidenceUrl":row["usFDAParentOriginalApprovalLetterUrl"],
            "fdaPriorUnrelatedSupplementS001RemsNotMaple":ticker=="CYTK",
            "fdaPriorUnrelatedSupplementEvidenceUrl":(
                row.get("fdaPreviouslyApprovedUnrelatedSupplementSourceUrl")),
            "sponsorReportedOSRequirementWithoutSignificantPrimaryOS":ticker=="SMMT",
            "sponsorReportedOSRequirementEvidenceUrl":(
                row.get("fdaOSStatisticalSignificanceRequirementPublicSourceUrl")),
            "fdaCurrentCycleApplicationOrSupplementNumberVerified":False,
            "fdaOriginalGoalAndExtensionsIndependentlyCertified":False,
            "currentFdaReviewCycleIndependentlyCertified":False,
            "independentPreDecisionThreeWayForecastExists":False,
            "qualifiesForStrictPhase3MarketCapPipeline":False,
            "notes":row["notes"],
        })
    assert_safe(seen==set(expected),"NOV14_REGISTRY_COVERAGE_INCOMPLETE")
    return sorted(checked,key=lambda r:r["ticker"])


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
    extended=validate_additional_formal_extensions(source,old_rows,asof)
    original=validate_additional_original_goal_sources(source,old_rows,asof)
    nov14=validate_nov14_trial_registry_triangulation(
        audit.load_json(ROOT/"new-platform/frontend/data/raas-v2-nov14-review-cycle-triangulation.json"),
        source,old_rows,asof)
    # Use the EXISTING eight-source ledger, enriching the SAME nightly CSV
    # rather than adding a conflicting calendar. No independent review claim.
    findings={r["researchCaseKey"]:r for r in [*selected,*original]}
    extended_findings={r["researchCaseKey"]:r for r in extended}
    assert_safe(len(findings)==len(selected)+len(original) and
                not (findings.keys() & extended_findings.keys()),
                "FORMAL_EXTENSION_OR_ORIGINAL_DUPLICATE_SOURCE")
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
        entry["currentIssuerReportedRevisedGoalDate"]=None
        entry["independentlyVerifiedApplicationCycle"]=False
        entry["pivotalPhaseIssuerResearch"]=None
        entry["approvedPipelinePhase3Qualification"]=False
        if not match:
            revised_match=extended_findings.get(entry["researchCaseKey"])
            if not revised_match:
                continue
            reviewed+=1
            revised+=1
            entry["issuerSourceFound"]=True
            entry["issuerSourceLink"]=revised_match["formalExtensionSourceUrl"]
            entry["applicationClassIssuerReported"]=revised_match["applicationType"]
            entry["firstGoalForThisCycleIssuerReported"]=revised_match[
                "firstReportedReviewCycleGoalDate"]
            entry["currentIssuerReportedRevisedGoalDate"]=revised_match[
                "currentIssuerReportedRevisedGoalDate"]
            entry["knownRevisedGoalNotOriginalPrediction"]=True
            entry["sourceResearchStatus"]=(
                "FORMAL_EXTENSION_KNOWN_ORIGINAL_DATE_NO_LONGER_UNRESOLVED"
                if revised_match["legacyDateIsFormerOriginalGoal"]
                else "REVISED_GOAL_MUST_NOT_COUNT_AS_FUTURE_ORIGINAL_DEADLINE")
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
        entry["pivotalPhaseIssuerResearch"]=match.get("pivotalPhaseEvidence")
        entry["firstGoalForThisCycleIssuerReported"]=first.isoformat()
        entry["knownRevisedGoalNotOriginalPrediction"]=is_revised
        entry["currentIssuerReportedRevisedGoalDate"]=(
            match["issuerPublishedCurrentGoalDate"] if is_revised else None)
        entry["sourceResearchStatus"]=(
            "REVISED_GOAL_MUST_NOT_COUNT_AS_FUTURE_ORIGINAL_DEADLINE"
            if is_revised else "ISSUER_GOAL_LOCATED_EXACT_CYCLE_STILL_UNVERIFIED")
        revised+=int(is_revised)
    by_case={x["researchCaseKey"]:x for x in nov14}
    near_term_in_live_queue=0
    for entry in report["blockedSourceItems"]:
        item=by_case.get(entry["researchCaseKey"])
        entry["clinicalTrialsGovNctId"]=None
        entry["thirdPartyClinicalTrialPhase3CrossChecked"]=False
        entry["FDAApprovedParentOriginalNdaNumber"]=None
        entry["priorFDAApprovedS001RemsNotCurrentMapleHcm"]=False
        entry["sponsorOSSignificanceRequirementEvidenceFound"]=False
        entry["fdaCurrentReviewApplicationOrSupplementNumberVerified"]=False
        if not item:
            continue
        assert_safe(entry["issuerSourceFound"] is True and
                    entry["firstGoalForThisCycleIssuerReported"]=="2026-11-14" and
                    entry["applicationClassIssuerReported"]==item["applicationClass"] and
                    not entry["V2ForecastEligible"],
                    "NOV14_REGISTRY_NOT_ORIGINAL_SOURCE_LINKED")
        near_term_in_live_queue+=1
        entry["clinicalTrialsGovNctId"]=item["clinicalTrialsGovId"]
        entry["thirdPartyClinicalTrialPhase3CrossChecked"]=True
        entry["FDAApprovedParentOriginalNdaNumber"]=item["fdaApprovedParentNdaNumber"]
        entry["priorFDAApprovedS001RemsNotCurrentMapleHcm"]=(
            item["fdaPriorUnrelatedSupplementS001RemsNotMaple"])
        entry["sponsorOSSignificanceRequirementEvidenceFound"]=(
            item["sponsorReportedOSRequirementWithoutSignificantPrimaryOS"])
    report["nov14KnownUnrelatedAlreadyApprovedFdaSupplementS001Count"]=1
    report["nov14SponsorDisclosedOSRequirementWithNonsignificantPrimaryCount"]=1
    report["nov14IssuerGoalAndThirdPartyTrialRecordsCrossChecked"]=nov14
    report["nov14ThirdPartyRegistryPhase3CrossCheckedCount"]=len(nov14)
    report["nov14ThirdPartyRegistryUpcomingCaseCount"]=near_term_in_live_queue
    report["nov14ExactCurrentFDAReviewCyclesIndependentlyCertified"]=0
    report["nov14FrozenThreeWayPredictionsIndependentlyVerified"]=0
    report["issuerSourceReviewedFutureDeadlineLeads"]=reviewed
    report["sourceDocumentedFirstGoalStillFuture"]=reviewed-revised
    report["knownRevisedDeadlineExcludedFromOriginalGoalCount"]=revised
    report["unreviewedLegacyDeadlineLeads"]=report["sourceQueueCount"]-reviewed
    report["unexcludedLegacyDeadlineLeadsNotIndependentlyVerified"]=(
        report["sourceQueueCount"]-revised)
    report["newSourceIntakeStage"]="FIFTEEN_ISSUER_GOAL_OR_REVISION_SOURCE_LEADS_FOUND_NOT_INDEPENDENTLY_CERTIFIED"
    report["issuerPublishedGoalSourceLeadsCount"]=len(selected)+len(extended)+len(original)
    report["additionalOriginalGoalIssuerSourcesCount"]=len(original)
    report["additionalOriginalGoalCycleAndPhaseChecks"]=original
    report["additionalFormallyExtendedSourceLeadsCount"]=len(extended)
    report["additionalFormalRevisionCycleChecks"]=extended
    report["independentlyCertifiedOriginalGoalRecords"]=0
    report["caseCycleAndSponsorSourceChecks"]=selected
    report["issuerDocumentedGistAndNonAdvSMRemainSeparate"]=True
    report["phase2PivotalOriginalGoalSourceCases"]=[
        r["researchCaseKey"] for r in original if
        r["pivotalPhaseEvidence"].startswith("PIVOTAL_PHASE_2_")]
    report["sourceIntakeStillExcludedFromApprovedFDAAccuracy"]=True
    report["clinicalReviewCycleRisks"]={
        "supplemental":1,"previouslyExtendedOriginalGoalAlreadyPassed":1,
        "licensedThirdPartySponsor":1,"resubmissionAfterCRL":1,
        "additionalFormalExtensionSources":len(extended)
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
          "currentIssuerReportedRevisedGoalDate","pivotalPhaseIssuerResearch",
          "approvedPipelinePhase3Qualification",
          "clinicalTrialsGovNctId","thirdPartyClinicalTrialPhase3CrossChecked",
          "FDAApprovedParentOriginalNdaNumber",
          "priorFDAApprovedS001RemsNotCurrentMapleHcm",
          "sponsorOSSignificanceRequirementEvidenceFound",
          "fdaCurrentReviewApplicationOrSupplementNumberVerified",
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
