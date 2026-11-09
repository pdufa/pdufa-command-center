#!/usr/bin/env python3
"""MAIN R63: original-page-linked, eight-domain source-review matrix for FOCUS.

This is NOT an 800-method clinical assessment, an independent reviewer signoff,
a calibrated FDA outcome forecast, or a retrospective FDA backtest. The current
public protocol/SAP PDFs are not proof of pre-unblinding prespecification.
All scores and outcomes remain withheld pending independent adjudication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scripts.refresh_focus_public_sources_r40 import APPS, ROSTER, _read_json, build_manifest

SCHEMA = "MAIN_R63_EIGHT_DOMAIN_ORIGINAL_METHOD_REVIEW_LADDER"
DOMAINS = (
    "PRIMARY_ENDPOINT",
    "ESTIMAND_ANALYSIS_POPULATION",
    "STATISTICAL_MODEL",
    "MULTIPLICITY_CONTROL",
    "MISSING_DATA_INTERCURRENT_EVENTS",
    "SENSITIVITY_ANALYSIS",
    "ADVERSE_EVENTS_SAFETY",
    "PROTOCOL_SAP_VERSION_CHANGES",
)
SHA = re.compile(r"[0-9a-f]{64}\Z")
URL = re.compile(r"https://cdn\.clinicaltrials\.gov/large-docs/\d{2}/NCT\d{8}/[A-Za-z0-9_.-]+\.pdf\Z")


def require(ok, code):
    if not ok:
        raise ValueError(code)


def original(path: Path):
    require(path.is_file() and not path.is_symlink()
            and 50 < path.stat().st_size < 25_000_000, "ORIGINAL_RESEARCH_REPORT_UNSAFE")
    raw = path.read_bytes()
    val = json.loads(raw)
    require(type(val) is dict, "ORIGINAL_RESEARCH_REPORT_NOT_AN_OBJECT")
    return val, hashlib.sha256(raw).hexdigest()


def by_id(rows, field, expected, label):
    require(type(rows) is list and len(rows) == len(expected)
            and all(type(r) is dict and type(r.get(field)) is str for r in rows),
            "INVALID_" + label + "_ROWS")
    ids = [r[field] for r in rows]
    require(set(ids) == set(expected) and len(set(ids)) == len(ids),
            "INVALID_" + label + "_MEMBERSHIP")
    return {r[field]: r for r in rows}


def build(manifest, r54, r55, r60, *, hashes):
    require(type(manifest) is dict and type(r54) is dict
            and type(r55) is dict and type(r60) is dict
            and type(hashes) is dict
            and set(hashes) == {"r54","r55","r60"}
            and all(type(x) is str and SHA.fullmatch(x) for x in hashes.values()),
            "UNTRUSTED_ORIGINAL_INPUT")
    require(manifest.get("trialCount") == 29 and manifest.get("applicationCount") == 23
            and r54.get("schema") == "MAIN_R54_EIGHT_DOMAIN_PAGE_CITED_METHODS_EVIDENCE_MATRIX"
            and r54.get("canonicalTrials") == 29 and r54.get("applicationGroups") == 23
            and r54.get("eightMethodsReviewDomains") == list(DOMAINS)
            and r54.get("currentPdfDocumentsSourceVerified") == 23
            and r54.get("trialsWithCurrentSourcePdfDocuments") == 12
            and r54.get("trialsWithoutCurrentAttachedProtocolSap") == 17
            and r54.get("machineReadEvidenceNotHumanScientificAssessment") is True
            and r54.get("historicalLockedSapVersionsIndependentlyVerified") == 0
            and r54.get("independentlySignedClinicalMethodGrades") == 0
            and r54.get("independentlyValidatedApplicationFdaPredictions") == 0
            and r54.get("independentHistoricalFDAOutcomeBacktests") == 0
            and r54.get("modelTrainingAuthorized") is False
            and r54.get("clinicalOrProductionWrites") is False
            and r54.get("officialPendingFDAOutcomePrediction") == "ABSTAIN"
            and r55.get("schema") == "MAIN_R55_EXACT_23_APPLICATION_SOURCE_REPORTED_EFFICACY_SAFETY_METHOD_PACKETS"
            and r55.get("nctTrials") == 29 and r55.get("applicationGroups") == 23
            and r55.get("sourceVerifiedCurrentProtocolSAPDocuments") == 23
            and r55.get("historicalLockedSAPsIndependentlyVerified") == 0
            and r55.get("signedScientificReviews") == 0
            and r55.get("independentlyValidatedFDAApplicationForecasts") == 0
            and r55.get("modelTrainingAuthorized") is False
            and r55.get("clinicalOrProductionWrites") is False
            and r55.get("officialPendingFDAOutcome") == "ABSTAIN"
            and r60.get("schema") == "MAIN_R60_ORIGINAL_REGISTRY_PRIMARY_SAFETY_CHALLENGE"
            and r60.get("canonicalUniqueNctCount") == 29
            and r60.get("provisionalApplicationCycleCount") == 23
            and r60.get("qualifiedClinicalOrStatisticalSignoffs") == 0
            and r60.get("independentlyValidatedFdaForecasts") == 0
            and r60.get("officialFutureFdaOutcome") == "ABSTAIN"
            and r60.get("officialFutureReviewTiming") == "ABSTAIN"
            and r60.get("fdaApprovalProbability") is None
            and r60.get("measuredPredictionAccuracy") is None
            and r60.get("reviewerLedgerProductionWritesOrModelTraining") is False,
            "UNVERIFIED_METHODOLOGY_OR_FALSE_PREDICTION_CERTIFICATION")

    ids = [t["nct"] for t in manifest["trialRows"]]
    apps = [a["cycleId"] for a in manifest["applicationGroups"]]
    require(len(set(ids)) == 29 and len(set(apps)) == 23, "CANONICAL_ROSTER_DUPLICATE")
    old = by_id(r54.get("trialMethodsReview"), "nct", ids, "R54_METHOD")
    efficacy = by_id(r55.get("originalUniqueTrialEvidence"), "nct", ids, "R55_TRIAL")
    challenged = by_id(r60.get("uniqueTrialOriginalResultChallenges"), "nct", ids, "R60_CHALLENGE")
    old_apps = by_id(r54.get("applicationMethodsReview"), "applicationCycleId", apps, "R54_APP")
    eff_apps = by_id(r55.get("currentSourceCasePackets"), "applicationCycleId", apps, "R55_APP")
    challenged_apps = by_id(r60.get("applicationSourceReviewCrosswalk"), "applicationCycleId", apps, "R60_APP")

    relationships = {n: [] for n in ids}
    for app in manifest["applicationGroups"]:
        for n in app["ncts"]:
            require(n in relationships and app["cycleId"] not in relationships[n],
                    "ORIGINAL_NCT_APPLICATION_MEMBERSHIP_CHANGED")
            relationships[n].append(app["cycleId"])

    output_trials = []
    total_attached = 0
    found_domains = set()
    domain_leads = 0
    for n in ids:
        methods = old[n]
        packet = efficacy[n]
        original_result = challenged[n]
        expected = sorted(relationships[n])
        require(methods.get("applicationCycleIds") == expected
                and packet.get("applicationCycleIds") == expected
                and original_result.get("applicationCycleIds") == expected
                and original_result.get("sourceSha256") == packet.get("currentRegistrySourceSha256")
                and methods.get("currentRegistrySourceSha256") in
                    (None,original_result.get("sourceSha256"))
                and methods.get("independentStatisticalReviewComplete") is False
                and methods.get("originalPreReadoutVersionCrosswalkVerified") is False
                and methods.get("verifiedFDAForecast") == "ABSTAIN"
                and packet.get("independentReviewerSigned") is False
                and packet.get("scientificScore") is None
                and packet.get("officialFDAOutcomeForecast") == "ABSTAIN"
                and original_result.get("independentlyQualifiedStatisticalJudgment") is None
                and original_result.get("independentlyQualifiedSafetyJudgment") is None
                and original_result.get("fdaOutcome") == "ABSTAIN",
                "TRIAL_PROVENANCE_OR_UNRELEASED_REVIEW_INVARIANT")

        docs = methods.get("documents")
        receipt_docs = packet.get("sourceMethodsPageReferences")
        require(type(docs) is list and type(receipt_docs) is list
                and len(docs) == methods.get("sourceDocumentCount") == len(receipt_docs)
                and len(docs) <= 8, "TRIAL_ORIGINAL_DOCUMENT_CENSUS_CHANGED")
        receipts = {d.get("sha256"): d for d in receipt_docs}
        require(len(receipts) == len(docs), "DUPLICATE_ORIGINAL_PDF_RECEIPTS")
        total_attached += len(docs)
        domains = []
        for dim in DOMAINS:
            leads = []
            for d in docs:
                sha = d.get("sourceSha256")
                receipt = receipts.get(sha)
                require(type(sha) is str and SHA.fullmatch(sha)
                        and type(receipt) is dict and
                        receipt.get("sourceUrl") == d.get("sourceUrl") and
                        type(d.get("sourceUrl")) is str and URL.fullmatch(d["sourceUrl"])
                        and receipt.get("filename") == d.get("filename"),
                        "DOCUMENT_SHA_OR_ORIGINAL_URL_MISMATCH")
                machine = d.get("machineTextEvidence")
                require(type(machine) is dict
                        and machine.get("clinicalMethodCompletenessVerified") is False
                        and machine.get("historicalProspectiveSAPLockVerified") is False
                        and machine.get("statisticalReviewerSigned") is False
                        and machine.get("FDAOutcomeForecast") == "ABSTAIN",
                        "UNREVIEWED_PDF_MACHINE_LEAD_IMPERSONATING_ADJUDICATION")
                evidence = machine.get("eightSourceReviewDomains")
                require(type(evidence) is dict and set(evidence) == set(DOMAINS),
                        "EXACT_EIGHT_DOMAIN_REVIEW_REQUIRED")
                item = evidence[dim]
                cited = item.get("pageLinkedSourceLeads")
                require(type(cited) is list and len(cited) <= 3
                        and item.get("sourceState") ==
                        ("PAGE_LINKED_TERMS_FOUND_REVIEW_REQUIRED" if cited
                         else "NO_EXACT_TERMS_FOUND_NOT_PROOF_OF_ABSENCE"),
                        "UNTRUSTED_MACHINE_METHOD_STATE")
                require(receipt.get("eightScientificMethodPageLeads", {}).get(dim) ==
                        [p.get("pdfPageOneBased") for p in cited],
                        "R54_R55_PDF_PAGE_IDENTITY_CHANGED")
                for p in cited:
                    page = p.get("pdfPageOneBased")
                    require(type(page) is int and
                            1 <= page <= machine.get("pageCount", 0) <= 1800
                            and type(p.get("term")) is str
                            and type(p.get("sourceExcerpt")) is str
                            and len(p["sourceExcerpt"]) <= 225,
                            "ORIGINAL_PDF_PAGE_OR_EXCERPT_INVALID")
                    leads.append({
                        "documentSha256":sha,
                        "originalUrl":d["sourceUrl"],
                        "filename":d["filename"],
                        "pdfPageOneBased":page,
                        "machineMatchedTerm":p["term"],
                        "unverifiedSourceExcerpt":p["sourceExcerpt"],
                        "possibleTableOfContentsOrIntro":bool(
                            p.get("indexOrIntroPagePossibility")),
                    })
            if leads:
                state = "LITERAL_PAGE_REFERENCE_REVIEW_REQUIRED"
                found_domains.add(dim)
            elif not docs:
                state = "NO_CURRENT_ATTACHED_DOCUMENT_SEARCH_OTHER_ORIGINALS"
            else:
                state = "NO_LITERAL_PAGE_REFERENCE_NOT_PROOF_OF_ABSENCE"
            domain_leads += len(leads)
            domains.append({
                "domain":dim,"sourceLeadStateNotScientificGrade":state,
                "sourceLeads":leads,
                "independentScientificJudgment":None,
                "sourceVersionAndPreunblindingVerified":False,
                "qualifiedReviewerSignoff":False,
                "assessmentLevel":"UNASSESSED_SOURCE_ONLY",
            })
        output_trials.append({
            "nct":n,
            "applicationCycleIds":expected,
            "originalRegistrySha256":packet["currentRegistrySourceSha256"],
            "originalCurrentProtocolSapCount":len(docs),
            "currentPostedPrimaryTables":len(original_result["sourceReportedPrimaryTables"]),
            "currentReportedSafetyArmCount":len(original_result["sourceReportedSafetyArms"]),
            "machineSourceReviewDimensions":domains,
            "unresolvedProtocolVersionFlags":methods.get("reviewFlags",[]),
            "sourceOnlyAssessmentStage":"STAGE_4_SOURCE_EVIDENCE_COLLECTION",
            "independentlyCompletedAssessmentLevel":None,
            "clinicalMethodScore":None,
            "officialFutureFdaDecision":"ABSTAIN",
            "qualifiedReviewerSigned":False,
        })
    require(total_attached == 23, "ORIGINAL_PDF_CENSUS_NO_LONGER_23")

    by_trial = {t["nct"]:t for t in output_trials}
    applications = []
    for app in manifest["applicationGroups"]:
        cid = app["cycleId"]
        prior = old_apps[cid]
        packet = eff_apps[cid]
        challenge = challenged_apps[cid]
        ncts = list(app["ncts"])
        require(prior.get("exactNcts") == ncts
                and packet.get("exactNcts") == ncts
                and challenge.get("supportingExactNcts") == ncts
                and prior.get("clinicalGrade") is None
                and prior.get("fdaApprovalProbability") is None
                and prior.get("officialFDAPrediction") == "ABSTAIN"
                and packet.get("independentClinicalReviewerSignoff") is False
                and packet.get("fdaProbability") is None
                and packet.get("officialFDAOutcomePrediction") == "ABSTAIN"
                and challenge.get("officialApprovalOrCrlForecast") == "ABSTAIN",
                "APPLICATION_REVIEW_OR_FDA_STATE_CHANGED")
        applications.append({
            "applicationCycleId":cid,
            "ticker":app["ticker"],
            "linkedNcts":ncts,
            "sourceDomainsPerTrial":len(DOMAINS),
            "linkedTrialOriginalDocuments":sum(by_trial[n]["originalCurrentProtocolSapCount"] for n in ncts),
            "domainsWithAtLeastOneMachinePageLead":[
                d for d in DOMAINS
                if any(next(row for row in by_trial[n]["machineSourceReviewDimensions"]
                            if row["domain"] == d)["sourceLeads"] for n in ncts)
            ],
            "signedScienceReviews":0,
            "independentClinicalMethodGrade":None,
            "officialFdaPrediction":"ABSTAIN",
            "measuredAccuracy":None,
        })
    require(len(output_trials) == 29 and len(applications) == 23
            and sum(bool(t["currentPostedPrimaryTables"]) for t in output_trials) ==
                r60.get("sourceVerifiedCurrentPrimaryTrialCount") == 12
            and sum(bool(t["currentReportedSafetyArmCount"]) for t in output_trials) ==
                r60.get("sourceVerifiedCurrentSafetyArmTrialCount") == 12,
            "ORIGINAL_RESULTS_OR_METHODS_COVERAGE_CHANGED")

    return {
        "schema":SCHEMA,
        "generatedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "originalSourceReportHashes":hashes,
        "uniqueTrials":29,
        "provisionalApplicationGroups":23,
        "sourceReviewDomains":list(DOMAINS),
        "domainTrialReviewSlots":29*len(DOMAINS),
        "publicOriginalProtocolSapDocuments":total_attached,
        "trialsWithOriginalAttachedMethodsDocuments":sum(bool(t["originalCurrentProtocolSapCount"]) for t in output_trials),
        "machinePageLinkedSourceLeadCount":domain_leads,
        "domainsWithAtLeastOneMachineLead":sorted(found_domains),
        "trialMethodReviewerQueue":output_trials,
        "applicationMethodReviewerQueue":applications,
        "independentlySignedScientificAssessments":0,
        "scientificScoresCalculated":0,
        "validatedFDAForecasts":0,
        "independentHistoricalBacktests":0,
        "measuredPredictionAccuracy":None,
        "officialFutureFDAOutcome":"ABSTAIN",
        "officialReviewDelayPrediction":"ABSTAIN",
        "productionOrClinicalLedgerWrites":False,
        "modelTrainingAuthorized":False,
        "machinePageLeadsAreNeither800CompletedTestsNorClinicalValidation":True,
    }


def summary(report):
    rows = [
        "# MAIN R63 — Eight source-review domains across 29 FOCUS trials",
        "",
        "**232 source-review slots are not 232 completed scientific assessments.**",
        "Machine page references require dated original protocol/SAP and independent human review.",
        "",
        "| Source review dimension | Trials with at least one original PDF page lead |",
        "| --- | ---: |",
    ]
    for domain in DOMAINS:
        matches = sum(any(d["domain"] == domain and d["sourceLeads"]
                          for d in trial["machineSourceReviewDimensions"])
                      for trial in report["trialMethodReviewerQueue"])
        rows.append(f"| {domain} | {matches}/29 |")
    rows.extend([
        "",
        f'Original protocol/SAP files attached to current registry: {report["publicOriginalProtocolSapDocuments"]} across {report["trialsWithOriginalAttachedMethodsDocuments"]}/29 trials.',
        "",
        "**Clinical scores:** none. **Validated FDA decisions:** none. **Historical accuracy:** not measured.",
        "**Future FDA approval/CRL and review timing:** ABSTAIN.",
        "Current source omission or no machine keyword match is not evidence of a failed trial.",
        "",
    ])
    return "\n".join(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("r54","r55","r60","output","summary"):
        parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args()
    require(args.output != args.summary and
            all(not p.exists() and not p.is_symlink() and p.parent.is_dir()
                for p in (args.output,args.summary)),
            "WRITE_ONCE_RESEARCH_OUTPUTS_REQUIRED")
    r54,h54=original(args.r54)
    r55,h55=original(args.r55)
    r60,h60=original(args.r60)
    doc=build(build_manifest(_read_json(ROSTER),_read_json(APPS)),
              r54,r55,r60,hashes={"r54":h54,"r55":h55,"r60":h60})
    with args.output.open("xb") as f:
        f.write((json.dumps(doc,indent=2,sort_keys=True)+"\n").encode())
    with args.summary.open("xb") as f:
        f.write(summary(doc).encode())
    print(json.dumps({key:doc[key] for key in (
        "uniqueTrials","provisionalApplicationGroups","domainTrialReviewSlots",
        "publicOriginalProtocolSapDocuments","independentlySignedScientificAssessments",
        "validatedFDAForecasts")},sort_keys=True))


if __name__=="__main__":
    main()
