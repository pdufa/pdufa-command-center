#!/usr/bin/env python3
"""R64 display parity check: every original R63 PDF page is intact and ungraded.

Reconstruct the compact Next.js snapshot from the immutable original R63
eight-domain method reviewer artifact. The UI may render links to page leads;
it must never substitute a grade or historical FDA outcome. No fetch or write
to trial databases. Fail closed on any changed original source row.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

R63_SHA = "b39028e972c45949147d405c447af45ef8ceab7089d8e89247cacd1d2cef6a18"
R63_RUN = 42713443428
R63_ARTIFACT = 13717655352
ORIGINAL_SCHEMA = "MAIN_R63_EIGHT_DOMAIN_ORIGINAL_METHOD_REVIEW_LADDER"
DOMAINS = [
    "PRIMARY_ENDPOINT", "ESTIMAND_ANALYSIS_POPULATION", "STATISTICAL_MODEL",
    "MULTIPLICITY_CONTROL", "MISSING_DATA_INTERCURRENT_EVENTS",
    "SENSITIVITY_ANALYSIS", "ADVERSE_EVENTS_SAFETY",
    "PROTOCOL_SAP_VERSION_CHANGES",
]
SAFE_NCT = re.compile(r"NCT\d{8}\Z")


def require(condition, code):
    if not condition:
        raise ValueError(code)


def read_json(path: Path, limit: int):
    require(path.is_file() and not path.is_symlink()
            and 1 <= path.stat().st_size <= limit, "MISSING_OR_UNSAFE_SOURCE_FILE")
    raw = path.read_bytes()
    obj = json.loads(raw)
    require(isinstance(obj, dict), "SOURCE_MUST_BE_OBJECT")
    return obj, hashlib.sha256(raw).hexdigest()


def compact_from_original(orig: dict):
    require(orig.get("schema") == ORIGINAL_SCHEMA
            and orig.get("uniqueTrials") == 29
            and orig.get("provisionalApplicationGroups") == 23
            and orig.get("sourceReviewDomains") == DOMAINS
            and orig.get("domainTrialReviewSlots") == 232
            and orig.get("publicOriginalProtocolSapDocuments") == 23
            and orig.get("trialsWithOriginalAttachedMethodsDocuments") == 12
            and orig.get("machinePageLinkedSourceLeadCount") == 466
            and orig.get("independentlySignedScientificAssessments") == 0
            and orig.get("scientificScoresCalculated") == 0
            and orig.get("validatedFDAForecasts") == 0
            and orig.get("independentHistoricalBacktests") == 0
            and orig.get("measuredPredictionAccuracy") is None
            and orig.get("officialFutureFDAOutcome") == "ABSTAIN"
            and orig.get("officialReviewDelayPrediction") == "ABSTAIN"
            and orig.get("productionOrClinicalLedgerWrites") is False
            and orig.get("modelTrainingAuthorized") is False
            and orig.get("machinePageLeadsAreNeither800CompletedTestsNorClinicalValidation") is True,
            "R63_SCOPE_OR_CLINICAL_READINESS_CHANGED")
    trials = orig.get("trialMethodReviewerQueue")
    apps = orig.get("applicationMethodReviewerQueue")
    require(type(trials) is list and len(trials) == 29
            and type(apps) is list and len(apps) == 23
            and len({t["nct"] for t in trials}) == 29
            and len({a["applicationCycleId"] for a in apps}) == 23,
            "UNIQUE_TRIAL_APPLICATION_MEMBERSHIP_CHANGED")

    docs = []
    doc_positions = {}
    parsed = []
    all_rows = set()
    for trial in trials:
        nct = trial["nct"]
        require(isinstance(nct, str) and SAFE_NCT.fullmatch(nct)
                and nct not in all_rows
                and trial.get("independentlyCompletedAssessmentLevel") is None
                and trial.get("clinicalMethodScore") is None
                and trial.get("qualifiedReviewerSigned") is False
                and trial.get("officialFutureFdaDecision") == "ABSTAIN"
                and trial.get("sourceOnlyAssessmentStage") == "STAGE_4_SOURCE_EVIDENCE_COLLECTION",
                "TRIAL_METHOD_NOT_SOURCE_ONLY")
        all_rows.add(nct)
        dimensions = trial.get("machineSourceReviewDimensions")
        require(type(dimensions) is list and len(dimensions) == 8
                and [d.get("domain") for d in dimensions] == DOMAINS,
                "EIGHT_PHASE_FIRST_DOMAINS_CHANGED")
        domain_leads = []
        for d in dimensions:
            require(d.get("assessmentLevel") == "UNASSESSED_SOURCE_ONLY"
                    and d.get("independentScientificJudgment") is None
                    and d.get("qualifiedReviewerSignoff") is False
                    and d.get("sourceVersionAndPreunblindingVerified") is False,
                    "FALSE_CLINICAL_REVIEW_OR_RATING")
            found = []
            for source in d.get("sourceLeads", []):
                sha = source["documentSha256"]
                filename = source["filename"]
                url = source["originalUrl"]
                page = source["pdfPageOneBased"]
                require(type(sha) is str and re.fullmatch(r"[a-f0-9]{64}", sha)
                        and type(page) is int and 1 <= page <= 1800
                        and type(filename) is str
                        and re.fullmatch(r"(?:Prot|SAP|Prot_SAP)_\d{3}\.pdf", filename)
                        and url == f"https://cdn.clinicaltrials.gov/large-docs/{nct[-2:]}/{nct}/{filename}",
                        "UNTRUSTED_ORIGINAL_PDF_OR_PAGE_CITATION")
                key = (nct, filename, sha)
                if key not in doc_positions:
                    doc_positions[key] = len(docs)
                    docs.append([nct, filename])
                found.append([doc_positions[key], page])
            domain_leads.append(found)
        if any(domain_leads):
            parsed.append([nct, domain_leads])
    require(len(parsed) == 12 and len(docs) == 22
            and sum(len(domain) for _, row in parsed for domain in row) == 466,
            "SOURCE_CITATION_COVERAGE_DRIFT")
    require(len({(n, f) for n, f in docs}) == len(docs),
            "SAME_PDF_FILENAME_WITH_MULTIPLE_HASHES")
    return docs, parsed


def verify(original_path: Path, frontend_path: Path):
    orig, digest = read_json(original_path, 2_000_000)
    require(digest == R63_SHA, "R63_IMMUTABLE_SOURCE_SHA_NOT_MATCHING")
    compact, _ = read_json(frontend_path, 50_000)
    require(set(compact) == {
        "rev", "originalRun", "originalArtifact", "originalR63Sha256",
        "docs", "trialPageLeads",
    }, "FRONTEND_DATA_SCHEMA_DRIFT")
    require(compact.get("rev") == 64 and
            compact.get("originalRun") == R63_RUN and
            compact.get("originalArtifact") == R63_ARTIFACT and
            compact.get("originalR63Sha256") == R63_SHA,
            "UNVERIFIED_SOURCE_REFERENCE")
    docs, pages = compact_from_original(orig)
    require(compact.get("docs") == docs, "ORIGINAL_PDF_DOCUMENT_IDENTITY_OR_ORDER_MISMATCH")
    require(compact.get("trialPageLeads") == pages,
            "ORIGINAL_PDF_PAGE_LEAD_SOURCE_PARITY_MISMATCH")
    return {
        "exactUniqueNcts": 29,
        "provisionalCycles": 23,
        "scientificSourceDomains": 8,
        "unscoredSourceReviewSlots": 232,
        "currentAttachedProtocolSapDocuments": 23,
        "linkedPdfDocumentsWithMachinePageLeads": len(docs),
        "pageLinkedSourceLeads": 466,
        "clinicalGradesSigned": 0,
        "validFDAForecasts": 0,
        "measuredForecastAccuracy": None,
        "FDAOutcome": "ABSTAIN",
        "noProductionWrites": True,
        "status": "ORIGINAL_R63_SOURCE_VIEW_PARITY_PASSED",
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",required=True,type=Path)
    p.add_argument("--frontend",required=True,type=Path)
    args=p.parse_args()
    print(json.dumps(verify(args.original,args.frontend),sort_keys=True))


if __name__ == "__main__":
    main()
