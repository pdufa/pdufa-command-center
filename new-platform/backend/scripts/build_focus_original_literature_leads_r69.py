#!/usr/bin/env python3
"""MAIN R69: source-locked literature recovery leads from archived NCT records.

Registry 'DERIVED' PubMed references are NOT independent confirmation that an
article reports THIS NCT's pivotal primary result, statistically positive
efficacy, an FDA approval, or the original pre-unblinding SAP. Reviewers must
open and verify each publication, study ID, protocol version and methods.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime,timezone
from pathlib import Path

from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest

R46_SHA="7e1681399ed242d0080d8517bbe62cfb931e88e1340295fdf9839affbc0d3f92"
R66_SHA="be3f8f0f4351579a7eddea2ebb67654992f8dd8f5125cbd78bf56ed440f43257"
SCHEMA="MAIN_R69_ORIGINAL_REGISTRY_PUBMED_REFERENCE_LEAD_RECOVERY"
NCT=re.compile(r"NCT[0-9]{8}\Z")
PMID=re.compile(r"[1-9][0-9]{5,9}\Z")
HASH=re.compile(r"[a-f0-9]{64}\Z")


def require(test,code):
    if not test:raise ValueError(code)


def read_file(path:Path,size=1_200_000):
    require(path.is_file() and not path.is_symlink() and
            50<path.stat().st_size<size,"ORIGINAL_ARCHIVE_FILE_UNSAFE")
    b=path.read_bytes()
    obj=json.loads(b)
    require(type(obj) is dict,"SOURCE_REPORT_NOT_OBJECT")
    return obj,hashlib.sha256(b).hexdigest()


def index_exact(rows,key,expected,code):
    require(type(rows) is list and len(rows)==len(expected) and
            all(type(row) is dict and type(row.get(key)) is str for row in rows),
            code+"_COUNT")
    out={row[key]:row for row in rows}
    require(len(out)==len(expected) and set(out)==set(expected),code+"_IDENTITY")
    return out


def build(manifest,r46,r66,original_dir:Path,*,hashes):
    require(type(manifest) is dict and type(r46) is dict and type(r66) is dict and
            hashes=={"r46":R46_SHA,"r66":R66_SHA} and
            manifest.get("trialCount")==29 and manifest.get("applicationCount")==23 and
            r46.get("schema")=="MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX" and
            r46.get("nctCount")==29 and r46.get("applicationGroupCount")==23 and
            r46.get("registryRecordsFetched")==29 and
            r46.get("validatedApplicationFdaForecasts")==0 and
            r46.get("scientificGradesWritten")==0 and
            r46.get("signedIndependentReviews")==0 and
            r46.get("productionOrReviewerWrites") is False and
            r46.get("modelTrainingAuthorized") is False and
            r66.get("schema")=="MAIN_R66_EXACT_ORIGINAL_29_TRIAL_PHASE_SOURCE_CENSUS" and
            r66.get("exactNcts")==29 and
            r66.get("provisionalApplicationCycles")==23 and
            r66.get("futureFDAOutcomePredictionsValidated")==0 and
            r66.get("independentlyQualifiedPhaseReviews")==0 and
            r66.get("signedScientificMethodGrades")==0 and
            r66.get("officialFutureFDAOutcome")=="ABSTAIN" and
            r66.get("measuredForecastAccuracy") is None and
            r66.get("historicalOutcomesInspected") is False and
            r66.get("productionOrReviewerLedgerWrites") is False,
            "RESEARCH_EVIDENCE_NOT_IMMUTABLE_OR_FORECAST_UNAUTHORIZED")
    require(original_dir.is_dir() and not original_dir.is_symlink(),
            "ORIGINAL_REGISTRY_ARCHIVE_DIRECTORY_MISSING")
    id_rows=manifest["trialRows"]
    ids=[x["nct"] for x in id_rows]
    cycles=[c["cycleId"] for c in manifest["applicationGroups"]]
    require(len(set(ids))==29 and len(set(cycles))==23,"CANONICAL_NCT_OR_APPLICATION_DUPLICATED")
    receipt=index_exact(r46.get("records"),"nct",ids,"R46_ORIGINAL")
    phase=index_exact(r66.get("originalRegistryPhaseEvidence"),"nct",ids,"R66_PHASE")
    memberships={n:[] for n in ids}
    for app in manifest["applicationGroups"]:
        for n in app["ncts"]:
            require(n in memberships and app["cycleId"] not in memberships[n],
                    "UNTRUSTED_APPLICATION_NCT_IDENTITY")
            memberships[n].append(app["cycleId"])
    all_cases=[]
    missing=[]
    for n in ids:
        path=original_dir/(n+".json")
        require(NCT.fullmatch(n) and path.resolve().is_relative_to(original_dir.resolve())
                and path.is_file() and not path.is_symlink() and
                50<path.stat().st_size<8_000_000,
                "ORIGINAL_TRIAL_RECORD_NOT_FOUND_"+n)
        raw=path.read_bytes()
        digest=hashlib.sha256(raw).hexdigest()
        old=receipt[n]
        frozen=phase[n]
        expected=sorted(memberships[n])
        require(old.get("sourceResponseSha256")==digest
                and old.get("sourceResponseBytes")==len(raw)
                and frozen.get("sourceOriginalResponseSha256")==digest
                and sorted(old.get("applicationCycleIds",[]))==expected
                and frozen.get("applicationCycleIds")==expected
                and frozen.get("requiresHumanPhaseValidation") is True
                and frozen.get("independentPhaseReviewEventId") is None
                and frozen.get("fdaPrediction")=="ABSTAIN",
                "ORIGINAL_REGISTRY_HASH_OR_APPLICATION_EDGE_CHANGED_"+n)
        obj=json.loads(raw)
        protocol=obj.get("protocolSection") or {}
        require(protocol.get("identificationModule",{}).get("nctId")==n,
                "ORIGINAL_NCT_MISMATCH")
        result=obj.get("resultsSection") or {}
        measures=(result.get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []
        require(type(measures) is list,"MALFORMED_POSTED_OUTCOME_MEASURES")
        posted_primary=sum(type(o) is dict and o.get("type")=="PRIMARY" for o in measures)
        refs=(protocol.get("referencesModule") or {}).get("references") or []
        require(type(refs) is list and len(refs)<=60,
                "REGISTRY_REFERENCE_MODULE_UNTRUSTED")
        leads=[]
        seen=set()
        for ref in refs:
            require(type(ref) is dict and type(ref.get("type")) is str,
                    "UNTRUSTED_ORIGINAL_REFERENCE_TYPE")
            pmid=ref.get("pmid")
            citation=ref.get("citation")
            require(pmid is None or type(pmid) is str and PMID.fullmatch(pmid),
                    "UNTRUSTED_ORIGINAL_REFERENCE_PMID")
            require(citation is None or type(citation) is str and len(citation)<=5000,
                    "UNTRUSTED_ORIGINAL_REFERENCE_CITATION")
            if pmid is None:continue
            require(pmid not in seen,"DUPLICATED_PUBMED_ID_IN_ORIGINAL_REGISTRY")
            seen.add(pmid)
            if posted_primary==0:
                leads.append({
                    "pmid":pmid,
                    "pubmedUrl":"https://pubmed.ncbi.nlm.nih.gov/"+pmid+"/",
                    "registryReferenceType":ref["type"],
                    "citationExactlyAsRecorded":citation,
                    "registryClaimsExactStudyPrimaryOutcomeVerification":False,
                    "articleContentIndependentlyInspected":False,
                    "exactNctMentionInArticleVerified":False,
                    "paperReportsPivotalPrimaryOutcomeVerified":False,
                    "independentQualifiedPublicationReviewSigned":False,
                    "publicationIsCandidateLeadNotConfirmedTrialResult":True,
                })
        if posted_primary==0:
            missing.append({
                "nct":n,
                "applicationCycleIds":expected,
                "originalRegistrySourceSha256":digest,
                "originalRegistryUrl":"https://clinicaltrials.gov/study/"+n,
                "originalRegistryLastUpdatePosted":frozen["sourceRegistryLastUpdatePostedDate"],
                "currentRegistryPrimaryTables":0,
                "registryDerivedPubmedReferenceLeads":leads,
                "originalRegistryLiteratureLeadCount":len(leads),
                "externalArticleEvidenceStatus":"UNINSPECTED_REGISTRY_LISTED_REFERENCE" if leads
                    else "NO_PUBMED_REFERENCE_IN_RETAINED_REGISTRY",
                "mustVerifyExactNctInFullPublication":True,
                "mustVerifyOriginalSignedProspectiveSap":True,
                "independentEfficacyAssessment":None,
                "independentSafetyAssessment":None,
                "scientificMethodGrade":None,
                "officialFdaForecast":"ABSTAIN",
            })
        all_cases.append({"nct":n,"postedPrimaryTablesInRetainedCopy":posted_primary,
                          "registryPubmedCountAll":len(seen)})
    require(len(all_cases)==29 and len(missing)==17
            and sum(bool(x["registryDerivedPubmedReferenceLeads"]) for x in missing)==7
            and sum(x["originalRegistryLiteratureLeadCount"] for x in missing)==11
            and sum(x["nct"]=="NCT02500381" for x in missing)==1,
            "ORIGINAL_R53_PUBLICATION_LEAD_CENSUS_CHANGED")
    pmids=[lead["pmid"] for x in missing for lead in
           x["registryDerivedPubmedReferenceLeads"]]
    require(len(pmids)==len(set(pmids))==11,
            "CROSS_TRIAL_PUBLICATION_LEAD_COLLISION")
    return {
        "schema":SCHEMA,
        "generatedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pinnedOriginalInputSha256":hashes,
        "canonicalUniqueNcts":29,
        "provisionalApplicationCycles":23,
        "originalRegistryNoCurrentPrimaryTrials":17,
        "missingPrimaryTrialsWithPubmedReferenceLeads":7,
        "missingPrimaryTrialsWithoutPubmedReferenceLeads":10,
        "registryListedUnverifiedPubmedReferences":11,
        "missingPrimaryLiteratureReviewQueue":missing,
        "all29OriginalReferenceCensus":all_cases,
        "independentlyVerifiedArticlesReportingExactTrialPrimary":0,
        "independentlyQualifiedReviewerAssessments":0,
        "validatedFutureFDAForecasts":0,
        "FDAOutcome":"ABSTAIN",
        "measuredPredictionAccuracy":None,
        "registryReferenceCannotEstablishTrialEfficacy":True,
        "externalArticlesNotFetchedOrContentAdjudicated":True,
        "historicalBacktestDataInspected":False,
        "modelTrainingOrProductionWrites":False,
    }

def summary(d):
    lines=[
      "# MAIN R69: source-locked publication lead recovery for 17 FOCUS trial records",
      "",
      "**11 registry-listed PubMed reference leads across 7 NCTs** without a posted",
      "primary table in the retained public registry copies. Ten have no PubMed",
      "reference in that version. References are marked DERIVED in source and",
      "**are not independently verified exact-trial efficacy publications**.",
      "",
      "| Trial | Source update | Original publication leads | Next manual gate |",
      "| --- | --- | --- | --- |"
    ]
    for row in d["missingPrimaryLiteratureReviewQueue"]:
        links=", ".join(
          f'[{x["pmid"]}]({x["pubmedUrl"]})'
          for x in row["registryDerivedPubmedReferenceLeads"]) or "None in retained registry"
        lines.append(
          f'| [`{row["nct"]}`]({row["originalRegistryUrl"]})'
          f' | {row["originalRegistryLastUpdatePosted"]}'
          f' | {links}'
          f' | Confirm publication is about this **exact NCT** and actually reports pivotal primary outcomes |'
        )
    lines.extend(["",
      "No registry DERIVED citation was independently opened, classified as a pivotal report",
      "or scored. No signed phase or efficacy review, FDA forecast or measured accuracy.",
      "**Future FDA outcome ABSTAIN; study-source review remains uncompleted.**",
      ""])
    return "\n".join(lines)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for x in ("r46","r66","original-registry-dir","output","summary"):
        parser.add_argument("--"+x,required=True,type=Path)
    args=parser.parse_args()
    require(args.output!=args.summary and all(not p.exists()
            and not p.is_symlink() and p.parent.is_dir()
            for p in (args.output,args.summary)),
            "OUTPUT_MUST_BE_NEW_AND_WRITE_ONCE")
    r46,h46=read_file(args.r46)
    r66,h66=read_file(args.r66)
    report=build(build_manifest(_read_json(ROSTER),_read_json(APPS)),
                 r46,r66,args.original_registry_dir,
                 hashes={"r46":h46,"r66":h66})
    with args.output.open("xb") as f:
        f.write((json.dumps(report,sort_keys=True,indent=2)+"\n").encode())
    with args.summary.open("xb") as f:
        f.write(summary(report).encode())
    print(json.dumps({x:report[x] for x in (
       "canonicalUniqueNcts","originalRegistryNoCurrentPrimaryTrials",
       "missingPrimaryTrialsWithPubmedReferenceLeads",
       "missingPrimaryTrialsWithoutPubmedReferenceLeads",
       "registryListedUnverifiedPubmedReferences",
       "independentlyVerifiedArticlesReportingExactTrialPrimary",
       "validatedFutureFDAForecasts")},sort_keys=True))
if __name__=="__main__":
    main()
