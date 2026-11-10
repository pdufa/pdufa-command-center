#!/usr/bin/env python3
"""MAIN R65: immutable-source independent scientific adjudication intake worklist.

R63 PDF machine search hits are only reviewer leads, not clinical grades or
prespecified/statistically valid findings. This script creates NO actual
reviewer attestations, scores, signed outcomes, FDA forecasts or ledger writes.
It never opens historical Track B outcomes. Review events remain governed by
the separate disabled-by-default, two-role authenticated pilot reviewer API.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

R63_SHA = "b39028e972c45949147d405c447af45ef8ceab7089d8e89247cacd1d2cef6a18"
SCHEMA = "MAIN_R65_ORIGINAL_SOURCE_HUMAN_ADJUDICATION_INTAKE_ONLY"
ORIGINAL_SCHEMA = "MAIN_R63_EIGHT_DOMAIN_ORIGINAL_METHOD_REVIEW_LADDER"
HEX = re.compile(r"[a-f0-9]{64}\Z")
NCT = re.compile(r"NCT[0-9]{8}\Z")
PDF = re.compile(r"(?:Prot|SAP|Prot_SAP)_[0-9]{3}\.pdf\Z")

CHECKS = {
    "PRIMARY_ENDPOINT": (
        "Verify phase, indication, patient-relevant original endpoint, unit, threshold and follow-up",
        "Reconcile registry and protocol/SAP primary hierarchy to final reported results",
        "Check endpoint change chronology and outcome-adjudication blinding"),
    "ESTIMAND_ANALYSIS_POPULATION": (
        "Verify original estimand, treatment policy and intercurrent-event handling",
        "Check randomized versus analyzed denominators, exclusions and analysis sets",
        "Identify deviations from the original locked estimand or analysis population"),
    "STATISTICAL_MODEL": (
        "Verify prospectively selected statistical model, effect scale and assumptions",
        "Independently examine uncertainty intervals, multiplicity-adjusted significance and model fit",
        "Record whether patient-level reanalysis is unavailable rather than infer correctness"),
    "MULTIPLICITY_CONTROL": (
        "Verify original family-wise hypothesis structure, alpha budget and test ordering",
        "Reconcile every published p-value to the original locked testing hierarchy",
        "Disallow nominal p-values from being labeled multiplicity-adjusted without evidence"),
    "MISSING_DATA_INTERCURRENT_EVENTS": (
        "Verify prespecified missing data treatment, protocol deviations and censoring",
        "Examine differential attrition and sensitivity to unobserved outcomes",
        "Do not convert missing evidence into a numerical failure score"),
    "SENSITIVITY_ANALYSIS": (
        "Verify prospective versus exploratory sensitivity analysis design",
        "Review robustness to alternative estimands and reasonable missingness assumptions",
        "Record contrary results and negative findings, not only positive corroboration"),
    "ADVERSE_EVENTS_SAFETY": (
        "Verify actual treatment exposure, treatment-emergent definitions and follow-up",
        "Review independent arm denominators, serious adverse events, deaths and imbalances",
        "Do not infer causal risks or aggregate incompatible arms without verification"),
    "PROTOCOL_SAP_VERSION_CHANGES": (
        "Obtain original, signed protocol and SAP versions and amendment chronology",
        "Independently verify first-public and pre-unblinding version timestamps",
        "Disclose post-hoc changes, source conflicts and unavailable original documents"),
}
DOMAINS = tuple(CHECKS)
REQUIRED_RECORD_FIELDS = (
    "verifiedPhaseEventId",
    "reviewerPrincipal",
    "reviewerAuthorizedRole",
    "originalDocumentContentSha256",
    "originalDocumentVersionAndDate",
    "firstPublicDateEvidence",
    "unblindingOrReadoutDateEvidence",
    "examinationDateUtc",
    "sourcePageLocation",
    "favorableEvidence",
    "unfavorableEvidence",
    "contradictoryEvidence",
    "missingEvidence",
    "clinicalRationale",
    "applicabilityJustification",
    "secondIndependentVerifier",
    "reviewEventId",
)
SOURCE_STATUS = {
    "LITERAL_PAGE_REFERENCE_REVIEW_REQUIRED",
    "NO_CURRENT_ATTACHED_DOCUMENT_SEARCH_OTHER_ORIGINALS",
    "NO_LITERAL_PAGE_REFERENCE_NOT_PROOF_OF_ABSENCE",
}


def require(condition: bool, code: str):
    if not condition:
        raise ValueError(code)


def _valid_lead(lead: dict, nct: str):
    require(type(lead) is dict, "MALFORMED_MACHINE_PDF_PAGE_LEAD")
    name = lead.get("filename")
    page = lead.get("pdfPageOneBased")
    sha = lead.get("documentSha256")
    url = lead.get("originalUrl")
    require(type(name) is str and PDF.fullmatch(name)
            and type(page) is int and 1 <= page <= 1800
            and type(sha) is str and HEX.fullmatch(sha)
            and type(url) is str and
            url == f"https://cdn.clinicaltrials.gov/large-docs/{nct[-2:]}/{nct}/{name}"
            and type(lead.get("machineMatchedTerm")) is str
            and len(lead["machineMatchedTerm"]) <= 120
            and type(lead.get("possibleTableOfContentsOrIntro")) is bool
            and type(lead.get("unverifiedSourceExcerpt")) is str
            and len(lead["unverifiedSourceExcerpt"]) <= 225,
            "UNTRUSTED_ORIGINAL_PDF_PAGE_OR_SOURCE_IDENTITY")
    return {
        "sourceSha256": sha,
        "originalUrl": url,
        "pdfPageOneBased": page,
        "matchedPhraseNotClinicalJudgment": lead["machineMatchedTerm"],
        "possibleContentsOrIntroPage": lead["possibleTableOfContentsOrIntro"],
    }


def build(source: dict, *, source_sha256: str) -> dict:
    require(type(source) is dict
            and type(source_sha256) is str and HEX.fullmatch(source_sha256)
            and source.get("schema") == ORIGINAL_SCHEMA
            and source.get("uniqueTrials") == 29
            and source.get("provisionalApplicationGroups") == 23
            and source.get("sourceReviewDomains") == list(DOMAINS)
            and source.get("domainTrialReviewSlots") == 232
            and source.get("publicOriginalProtocolSapDocuments") == 23
            and source.get("trialsWithOriginalAttachedMethodsDocuments") == 12
            and source.get("machinePageLinkedSourceLeadCount") == 466
            and source.get("independentlySignedScientificAssessments") == 0
            and source.get("scientificScoresCalculated") == 0
            and source.get("validatedFDAForecasts") == 0
            and source.get("independentHistoricalBacktests") == 0
            and source.get("measuredPredictionAccuracy") is None
            and source.get("officialFutureFDAOutcome") == "ABSTAIN"
            and source.get("officialReviewDelayPrediction") == "ABSTAIN"
            and source.get("productionOrClinicalLedgerWrites") is False
            and source.get("modelTrainingAuthorized") is False
            and source.get("machinePageLeadsAreNeither800CompletedTestsNorClinicalValidation") is True,
            "R63_UNREVIEWED_ORIGINAL_RESEARCH_REQUIRED")

    trial_rows = source.get("trialMethodReviewerQueue")
    app_rows = source.get("applicationMethodReviewerQueue")
    require(type(trial_rows) is list and len(trial_rows) == 29
            and type(app_rows) is list and len(app_rows) == 23,
            "EXACT_29_23_UNIQUE_REVIEW_QUEUE_REQUIRED")
    trial_ids = [t.get("nct") for t in trial_rows]
    app_ids = [a.get("applicationCycleId") for a in app_rows]
    require(len(set(trial_ids)) == 29 and
            all(type(n) is str and NCT.fullmatch(n) for n in trial_ids)
            and len(set(app_ids)) == 23 and
            all(type(a) is str and 3 <= len(a) <= 120 for a in app_ids),
            "SOURCE_TRIAL_APPLICATION_IDENTITY_UNTRUSTED")
    source_apps = {a["applicationCycleId"]:a for a in app_rows}
    source_trials = {t["nct"]:t for t in trial_rows}
    exact_edges = set()
    for app in app_rows:
        ncts = app.get("linkedNcts")
        require(type(ncts) is list and ncts
                and len(set(ncts)) == len(ncts)
                and all(n in source_trials for n in ncts)
                and app.get("signedScienceReviews") == 0
                and app.get("officialFdaPrediction") == "ABSTAIN"
                and app.get("independentClinicalMethodGrade") is None
                and app.get("measuredAccuracy") is None,
                "PROVISIONAL_APPLICATION_HAS_FALSE_REVIEW")
        for n in ncts:
            exact_edges.add((app["applicationCycleId"], n))

    trial_tasks = []
    all_documents = set()
    lead_count = 0
    trials_with_page_leads = 0
    for trial in trial_rows:
        nct = trial["nct"]
        linked = trial.get("applicationCycleIds")
        require(type(linked) is list and linked
                and linked == sorted(set(linked))
                and all((app, nct) in exact_edges for app in linked)
                and {a for a,n in exact_edges if n == nct} == set(linked)
                and type(trial.get("originalRegistrySha256")) is str
                and HEX.fullmatch(trial["originalRegistrySha256"])
                and trial.get("originalCurrentProtocolSapCount") in (0, 1, 2, 3, 4)
                and trial.get("independentlyCompletedAssessmentLevel") is None
                and trial.get("clinicalMethodScore") is None
                and trial.get("qualifiedReviewerSigned") is False
                and trial.get("officialFutureFdaDecision") == "ABSTAIN"
                and trial.get("sourceOnlyAssessmentStage") == "STAGE_4_SOURCE_EVIDENCE_COLLECTION",
                "UNTRUSTED_ORIGIN_OR_PREMATURE_CLINICAL_REVIEW")

        flags = trial.get("unresolvedProtocolVersionFlags")
        dims = trial.get("machineSourceReviewDimensions")
        require(type(flags) is list and
                all(type(f) is str and len(f) < 160 for f in flags)
                and "ORIGINAL_PRE_UNBLINDING_SAP_LOCK_NOT_VERIFIED" in flags
                and type(dims) is list and len(dims) == 8
                and [d.get("domain") for d in dims] == list(DOMAINS),
                "PHASE_FIRST_OR_VERSION_REVIEW_INCOMPLETE")
        checklist = []
        has_any = False
        for domain in dims:
            key = domain["domain"]
            refs = domain.get("sourceLeads")
            require(type(refs) is list and len(refs) <= 24
                    and domain.get("assessmentLevel") == "UNASSESSED_SOURCE_ONLY"
                    and domain.get("independentScientificJudgment") is None
                    and domain.get("scientificScore") is None
                    and domain.get("sourceVersionAndPreunblindingVerified") is False
                    and domain.get("qualifiedReviewerSignoff") is False
                    and domain.get("sourceLeadStateNotScientificGrade") in SOURCE_STATUS,
                    "MACHINE_LEADS_NOT_SCIENTIFIC_GRADES")
            prepared = [_valid_lead(lead,nct) for lead in refs]
            if refs:
                require(domain["sourceLeadStateNotScientificGrade"] ==
                        "LITERAL_PAGE_REFERENCE_REVIEW_REQUIRED",
                        "ORIGINAL_SOURCE_LEAD_STATUS_MISMATCH")
            elif trial["originalCurrentProtocolSapCount"] == 0:
                require(domain["sourceLeadStateNotScientificGrade"] ==
                        "NO_CURRENT_ATTACHED_DOCUMENT_SEARCH_OTHER_ORIGINALS",
                        "SOURCE_FREE_TRIAL_WRONGLY_MARKED_AS_GRADED")
            else:
                require(domain["sourceLeadStateNotScientificGrade"] ==
                        "NO_LITERAL_PAGE_REFERENCE_NOT_PROOF_OF_ABSENCE",
                        "NO_MACHINE_HIT_WRONGLY_MARKED_AS_FAILURE")
            if prepared:
                has_any = True
            lead_count += len(prepared)
            all_documents.update((nct,lead["originalUrl"],lead["sourceSha256"])
                                 for lead in prepared)
            checklist.append({
                "domain":key,
                "intakeId":f"{nct}:{key}",
                "phaseVerification":"REQUIRED_NOT_ATTESTED",
                "sourceReviewStatus":domain["sourceLeadStateNotScientificGrade"],
                "exactOriginalPageLeads":prepared,
                "requiredIndependentReviewQuestions":list(CHECKS[key]),
                "requiredEvidenceAndSignoffFields":list(REQUIRED_RECORD_FIELDS),
                "grade":None,
                "reviewerId":None,
                "reviewerAttestation":None,
                "secondIndependentVerifier":None,
                "finalDisposition":"PENDING_QUALIFIED_HUMAN_ADJUDICATION",
                "studySuccessOrFailure":"UNDETERMINED",
                "readyToRecordClinicalMethodGrade":False,
            })
        if has_any:
            trials_with_page_leads += 1
        trial_tasks.append({
            "nct":nct,
            "applicationCycleIds":linked,
            "originalCurrentRegistrySha256":trial["originalRegistrySha256"],
            "originalCurrentProtocolSapDocumentCount":trial["originalCurrentProtocolSapCount"],
            "currentPostedPrimaryTables":trial["currentPostedPrimaryTables"],
            "currentReportedSafetyArmCount":trial["currentReportedSafetyArmCount"],
            "protocolSapVersionAndChronologyFlags":flags,
            "mustVerifyTrialPhaseFirst":True,
            "phaseVerifiedByIndependentReviewer":False,
            "trialReviewSlots":checklist,
            "clinicalAssessmentLevel":"UNASSESSED_SOURCE_ONLY",
            "completedClinicalMethodScores":0,
            "validatedFDAOutcome":"ABSTAIN",
        })

    require(len(trial_tasks)==29
            and sum(t["originalCurrentProtocolSapDocumentCount"] for t in trial_tasks)==23
            and len(all_documents)==22
            and lead_count==466
            and trials_with_page_leads==12
            and sum(len(t["trialReviewSlots"]) for t in trial_tasks)==232,
            "ORIGINAL_R63_PAGE_COVERAGE_OR_TASK_CENSUS_CHANGED")
    return {
        "schema":SCHEMA,
        "generatedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sourceResearchRunId":42713443428,
        "sourceResearchArtifactId":13717655352,
        "originalR63Sha256":source_sha256,
        "exactNctCount":29,
        "provisionalApplicationCount":23,
        "sourceReviewDimensions":list(DOMAINS),
        "scientificReviewerTasks":232,
        "originalMachinePdfPageLeads":466,
        "originalPdfFilesWithLeads":22,
        "sourceTrialsWithCurrentPdfLeads":12,
        "sourceTrialsMissingCurrentPdfLeads":17,
        "reviewerRecordRequiredFields":list(REQUIRED_RECORD_FIELDS),
        "trialIndependentReviewPackets":trial_tasks,
        "qualifiedReviewerAttestationsRecorded":0,
        "independentVerifiedPhaseEventsRecorded":0,
        "independentlyCompletedMethodGrades":0,
        "independentStatisticalOrSafetySignoffs":0,
        "independentlyValidatedFDAApplicationPredictions":0,
        "measuredOutOfTimeForecastAccuracy":None,
        "officialFDAOutcome":"ABSTAIN",
        "fdaReviewTiming":"ABSTAIN",
        "gradeOrProbabilityReleasePermitted":False,
        "reviewWritesEnabled":False,
        "productionOrLedgerWrites":False,
        "historicalOutcomeDataAccessed":False,
        "reviewNote":"This is an original-source adjudication *intake* packet. Neither a named reviewer identity nor their independent examination can be synthesized by the engine. A separate authenticated human workflow and dated original evidence must be verified before any grade or FDA outcome is promoted."
    }


def summary(out):
    rows=[
        "# MAIN R65 — independent scientific adjudication intake, not signoff",
        "",
        "**232 evidence review tasks, 0 signed clinical assessments, 0 numerical grades, 0 validated FDA predictions.**",
        "",
        "| Exact NCT | Eight slots | Machine PDF leads | Current PDF document count | Version/chronology review |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for trial in out["trialIndependentReviewPackets"]:
        refs=sum(len(t["exactOriginalPageLeads"]) for t in trial["trialReviewSlots"])
        flags=trial["protocolSapVersionAndChronologyFlags"]
        rows.append(
            f'| {trial["nct"]} | 8 | {refs} | {trial["originalCurrentProtocolSapDocumentCount"]}'
            f' | {"; ".join(flags)} |'
        )
    rows.extend([
        "", "Phase must be independently verified first; review signed original pre-unblinding documents before assigning any scientific method scores.",
        "Earlier document excerpts can be contents-page leads, not method proof.",
        "Missing current registry sources are retrieval tasks, not failed trials.",
        "Historical FDA outcomes are not read for predictions. Approval/CRL/delay remain **ABSTAIN**.",
        "",
    ])
    return "\n".join(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-r63",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--summary",required=True,type=Path)
    args=p.parse_args()
    require(args.original_r63.is_file() and not args.original_r63.is_symlink()
            and args.original_r63.stat().st_size<5_000_000,
            "EXACT_ARCHIVED_R63_RESEARCH_REQUIRED")
    raw=args.original_r63.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    require(digest==R63_SHA,"ARCHIVED_R63_ORIGINAL_HASH_CHANGED")
    require(args.output!=args.summary
            and all(not f.exists() and not f.is_symlink() and f.parent.is_dir()
                    for f in (args.output,args.summary)),
            "WRITE_ONCE_RESEARCH_OUTPUT_REQUIRED")
    out=build(json.loads(raw),source_sha256=digest)
    with args.output.open("xb") as f:
        f.write((json.dumps(out,indent=2,sort_keys=True)+"\n").encode())
    with args.summary.open("xb") as f:
        f.write(summary(out).encode())
    print(json.dumps({
        "exactNctCount":out["exactNctCount"],
        "provisionalApplicationCount":out["provisionalApplicationCount"],
        "unscoredReviewerTasks":out["scientificReviewerTasks"],
        "originalPageLeads":out["originalMachinePdfPageLeads"],
        "qualifiedReviewerAttestationsRecorded":0,
        "validatedFDAApplicationPredictions":0,
    },sort_keys=True))


if __name__=="__main__":
    main()
