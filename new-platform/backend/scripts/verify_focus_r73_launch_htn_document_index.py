#!/usr/bin/env python3
"""Verify R73 published supplement *index*, never the PDF bytes or clinical outcome."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

INDEX="https://pmc.ncbi.nlm.nih.gov/articles/PMC12210145/"
JOURNAL="https://jamanetwork.com/journals/jama/fullarticle/2835763"
BASE="https://pmc.ncbi.nlm.nih.gov/articles/instance/12210145/bin/"
ROLES=("METHODS_SUPPLEMENT","PROTOCOL_VERSION","PROTOCOL_VERSION","PROTOCOL_VERSION",
       "SAP_ADDENDUM","SAP_AMENDMENT","SAP_ADDENDUM")
TITLES=(
 "Published Supplement 1: eMethods, multiplicity figure, sensitivity and adverse-event tables",
 "Trial protocol version 3.1",
 "Trial protocol version 3.0",
 "Trial protocol version 2.1",
 "Statistical analysis plan, windowing addendum 1",
 "Statistical analysis plan, amendment 2",
 "Statistical analysis plan, multiple-imputation addendum 1")
DOC_FIELDS={"supplementNumber","role","title","filename","publicOriginalIndexLink",
 "indexedInPublicPMCArticle","originalPdfBytesIndependentVerification","sha256",
 "documentInternalVersionDate","firstPublicAvailabilityDate",
 "prospectivelySignedAndLockedBeforeUnblinding","independentMethodAdjudicationStatus"}
TOP_FIELDS={"schema","asOf","nct","ticker","trial","pmid","doi",
 "articleOnlinePublicationDate","journalArticle","originalPublicArticleIndex",
 "indexObservation","scope","sourceDocumentBytesStored","sourceDocumentHashesVerified",
 "originalPreunblindingSignaturesVerified","earliestPublicReleaseDatesVerified",
 "originalLockChronologiesVerified","originalFullPdfScientificReviewsSigned",
 "validatedFDAApplicationForecasts","officialFutureFDAOutcome","forecastTiming",
 "clinicalGrade","trainingOrProductionWrites","documents","checksRemaining"}

def must(condition, message):
 if not condition:
  raise ValueError("R73_"+message)

def validate(manifest:dict, r71:dict)->dict:
 must(type(manifest) is dict and set(manifest)==TOP_FIELDS,"UNEXPECTED_TOP_LEVEL")
 must((manifest["schema"]=="MAIN_R73_LAUNCH_HTN_PUBLISHED_PROTOCOL_SAP_DOCUMENT_INDEX_NOT_LOCK_AUTHENTICATION"
       and manifest["asOf"]=="2026-11-09"
       and manifest["nct"]=="NCT06153693"
       and manifest["ticker"]=="MLYS"
       and manifest["trial"]=="Launch-HTN"
       and manifest["pmid"]=="40587141"
       and manifest["doi"]=="10.1001/jama.2025.9413"
       and manifest["articleOnlinePublicationDate"]=="2025-06-30"
       and manifest["journalArticle"]==JOURNAL
       and manifest["originalPublicArticleIndex"]==INDEX
       and manifest["indexObservation"]=="SEVEN_DOCUMENT_LINKS_IN_ORIGINAL_PMC_ARTICLE_LISTING"
       and manifest["scope"]=="CURRENT_PUBLICATION_INDEX_ONLY_NOT_ORIGINAL_SIGNED_PREUNBLINDING_PLANS"),
      "SOURCE_IDENTITY_OR_SCOPE")
 must(type(r71) is dict and r71.get("schema")==
  "MAIN_R71_FIVE_PIVOTAL_ABSTRACT_RESULT_AND_FULLTEXT_ACCESS_REVIEW_ONLY",
  "R71_UPSTREAM_INVALID")
 cases=r71.get("cases")
 must(type(cases) is list and len(cases)==5,"R71_CASE_CENSUS")
 study=[c for c in cases if c.get("nct")=="NCT06153693"]
 must(len(study)==1 and study[0].get("ticker")=="MLYS" and
  study[0].get("pmid")=="40587141" and
  study[0].get("doi")=="10.1001/jama.2025.9413" and
  study[0].get("fullOriginalPaperIndependentlyRead") is False,
  "R71_MATCH_OR_SOURCE_STATUS")
 for k in ("sourceDocumentHashesVerified","originalPreunblindingSignaturesVerified",
           "earliestPublicReleaseDatesVerified","originalLockChronologiesVerified",
           "originalFullPdfScientificReviewsSigned","validatedFDAApplicationForecasts"):
  must(type(manifest[k]) is int and manifest[k]==0,"FALSE_VERIFICATION_"+k)
 must(manifest["sourceDocumentBytesStored"] is False and
  manifest["trainingOrProductionWrites"] is False and
  manifest["clinicalGrade"] is None and
  manifest["officialFutureFDAOutcome"]=="ABSTAIN" and
  manifest["forecastTiming"]=="UNKNOWN","UNAUTHORIZED_FORECAST")
 docs=manifest["documents"]
 must(type(docs) is list and len(docs)==7,"EXACT_SEVEN_SUPPLEMENTS")
 for i,d in enumerate(docs,1):
  filename=f"jama-e259413-s{i:03d}.pdf"
  must(type(d) is dict and set(d)==DOC_FIELDS and
    type(d["supplementNumber"]) is int and d["supplementNumber"]==i and
    d["role"]==ROLES[i-1] and d["title"]==TITLES[i-1] and
    d["filename"]==filename and
    d["publicOriginalIndexLink"]==BASE+filename and
    d["indexedInPublicPMCArticle"] is True and
    d["originalPdfBytesIndependentVerification"] is False and
    d["sha256"] is None and d["documentInternalVersionDate"] is None and
    d["firstPublicAvailabilityDate"] is None and
    d["prospectivelySignedAndLockedBeforeUnblinding"] is False and
    d["independentMethodAdjudicationStatus"]=="PENDING_ORIGINAL_VERSION_REVIEW",
    "DOCUMENT_"+str(i)+"_FORGED_OR_PREMATURE")
 gates=manifest["checksRemaining"]
 must(type(gates) is list and len(gates)==6 and
   all(type(x) is str and len(x)>=55 for x in gates),
   "SIX_REMAINING_REVIEW_GATES")
 return {"status":"PASS","exactNct":"NCT06153693","indexedSourceDocumentLinks":7,
  "protocolVersions":3,"statisticalAnalysisPlanDocuments":3,
  "methodsSupplements":1,"verifiedOriginalPDFBytes":0,
  "signedPreunblindingStatisticalPlans":0,"signedScientificReviews":0,
  "validatedFDAForecasts":0,"futureFDAOutcome":"ABSTAIN",
  "researchOnly":True,"productionWrites":False}

if __name__=="__main__":
 parser=argparse.ArgumentParser()
 parser.add_argument("--manifest",default="new-platform/frontend/data/focus-r73-launch-htn-original-document-index.json")
 parser.add_argument("--r71",default="new-platform/frontend/data/focus-r71-five-main-publication-source-review.json")
 args=parser.parse_args()
 result=validate(json.loads(Path(args.manifest).read_text()),
                 json.loads(Path(args.r71).read_text()))
 print(json.dumps(result,sort_keys=True))
