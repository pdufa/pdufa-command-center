#!/usr/bin/env python3
"""MAIN R70: verify every frontend article title, DOI, publication type, NCT
source link and literal phase term against the exact original R70 PubMed
metadata+abstract research artifact, without claiming clinical review.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path

R70_REPORT_SHA="03434b975e511b2d603227bab3e25768dbcc3a0e7b412d479d9afbd100cd2577"
PUBMED_XML_SHA="2aa5fac13c7741d7ed2d9b1c2d91101978661150c87324b566b88f75994e394b"
ORIGINAL_R69_SHA="8b11d9f7e6f8896286944a454569b59cac9d63c5350fcb9665e6ff47e5519e77"
ORIGINAL_SCHEMA="MAIN_R70_ORIGINAL_PUBMED_XML_METADATA_ABSTRACT_EVIDENCE_LEADS"

def require(ok,code):
 if not ok:raise ValueError(code)

def read(path,limit):
 require(path.is_file() and not path.is_symlink()
         and 40<path.stat().st_size<limit,"R70_EVIDENCE_SOURCE_FILE_UNSAFE")
 raw=path.read_bytes()
 doc=json.loads(raw)
 require(type(doc) is dict,"R70_SOURCE_FILE_NOT_OBJECT")
 return doc,hashlib.sha256(raw).hexdigest()

def expected_projection(original,digest):
 require(original.get("schema")==ORIGINAL_SCHEMA
         and digest==R70_REPORT_SHA
         and original.get("originalPubmedXmlSha256")==PUBMED_XML_SHA
         and original.get("inputOriginalR69Sha256")==ORIGINAL_R69_SHA
         and original.get("focusExactNcts")==29
         and original.get("provisionalFDAApplicationGroups")==23
         and original.get("originalRegistryNctsWithoutCurrentPrimary")==17
         and original.get("articleMetadataRecordsRetrieved")==11
         and original.get("registryDerivedPubmedCitationLeads")==11
         and original.get("exactNctIdentifiersFoundInRetrievedMetadataOrAbstract")==11
         and original.get("exactNctMentionedInArticleTitleOrAbstract")==8
         and original.get("exactNctLinkedOnlyAsPubmedDatabankAccession")==3
         and original.get("noExactNctIdentifierFoundInRetrievedMetadataOrAbstract")==0
         and original.get("articlesWithIndependentlyAdjudicatedPivotalOutcomes")==0
         and original.get("qualifiedReviewerSignoffs")==0
         and original.get("scoredScientificMethods")==0
         and original.get("validatedFutureFdaApplicationPredictions")==0
         and original.get("measuredHistoricalForecastAccuracy") is None
         and original.get("officialFutureFDAOutcome")=="ABSTAIN"
         and original.get("originalArticleFullTextsRetrieved")==0
         and original.get("modelTrainingOrProductionWrites") is False
         and original.get("pubmedAbstractsAreNotFullPublicationAnalysis") is True
         and original.get("machineNctIdentifierMatchDoesNotEstablishClinicalGrade") is True,
         "R70_PRIMARY_SOURCE_OR_FALSE_PIVOTAL_ADJUDICATION")
 source=original.get("articleResearchLeads")
 require(type(source) is list and len(source)==11
         and len({x["pmid"] for x in source})==11,
         "R70_EXACT_11_PUBMED_ROWS_REQUIRED")
 rows=[]
 for x in source:
  n,p=x["nct"],x["pmid"]
  require(re.fullmatch(r"NCT\d{8}",n)
          and re.fullmatch(r"[1-9]\d{5,9}",p)
          and x["pubmedUrl"]=="https://pubmed.ncbi.nlm.nih.gov/"+p+"/"
          and x["sourceXmlSha256"]==PUBMED_XML_SHA
          and x["pivotalPhase3PrimaryResultsIndependentlyVerified"] is False
          and x["trialPhaseMatchIndependentlyVerified"] is False
          and x["fullTextIndependentlyRead"] is False
          and x["preUnblindingProtocolSapVersionVerified"] is False
          and x["statisticalEndpointsAdjudicated"] is False
          and x["scientificReviewerSigned"] is False
          and x["clinicalGrade"] is None
          and x["fdaApprovalOrCrlPrediction"]=="ABSTAIN",
          "ARTICLE_RECORD_CANNOT_CLAIM_QUALIFIED_SCIENCE")
  rows.append([
   n,p,x["articleTitleExactlyAsPubmed"],x["journalExactlyAsPubmed"],
   x["doiAsPubmed"],x["exactFocusNctIdentifierInArticleTitleOrAbstract"],
   x["exactFocusNctLinkedOnlyAsPubmedDatabankAccession"],
   x["pubmedPublicationTypes"],x["literalSourceTextScopeFlags"]
  ])
 require(sum(row[5] for row in rows)==8 and sum(row[6] for row in rows)==3
         and len({row[0] for row in rows})==7
         and len({row[1] for row in rows})==11
         and all((row[5] is True)^(row[6] is True) for row in rows),
         "PUBMED_TITLE_ABSTRACT_LINK_VERSUS_DATABANK_DERIVATION_DRIFT")
 return {"schema":"MAIN_R70_ORIGINAL_PUBMED_METADATA_DISPLAY_ONLY",
   "run":42729546458,
   "artifact":13724930108,
   "originalResearchSha256":R70_REPORT_SHA,
   "originalPubmedXmlSha256":PUBMED_XML_SHA,
   "entries":rows}

def verify(original_path,display_path):
 doc,sha=read(original_path,2000000)
 display,_=read(display_path,20000)
 require(display==expected_projection(doc,sha),
         "DISPLAY_R70_PUBMED_SOURCE_METADATA_NOT_EXACT_ORIGINAL")
 return {"status":"PASS","sourceSha256":sha,"sourceXmlSha256":PUBMED_XML_SHA,
  "articleMetadataRecords":11,"exactNctInArticleTitleOrAbstract":8,
  "dbLinkageOnly":3,"verifiedPivotalOutcomes":0,
  "qualifiedReviewerSignoffs":0,"validatedFDAForecasts":0,
  "futureFdaOutcome":"ABSTAIN","productionWrites":False}

if __name__=="__main__":
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--original",type=Path,required=True)
 p.add_argument("--frontend",type=Path,required=True)
 args=p.parse_args()
 print(json.dumps(verify(args.original,args.frontend),sort_keys=True))
