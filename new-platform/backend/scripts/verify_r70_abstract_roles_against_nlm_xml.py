#!/usr/bin/env python3
"""MAIN R70: compare editorial role triage with source-locked original PubMed XML.

Rules deliberately stop short of full pivotal trial validation, signed
statistical review, 800-method scoring, FDA outcome prediction or calibration.
PubMed/abstract scope can identify promising papers, but not a prospective SAP.
"""
from __future__ import annotations
import argparse,hashlib,json,re
import xml.etree.ElementTree as ET
from pathlib import Path

META_SHA="03434b975e511b2d603227bab3e25768dbcc3a0e7b412d479d9afbd100cd2577"
XML_SHA="2aa5fac13c7741d7ed2d9b1c2d91101978661150c87324b566b88f75994e394b"
R69_SHA="8b11d9f7e6f8896286944a454569b59cac9d63c5350fcb9665e6ff47e5519e77"
META_SCHEMA="MAIN_R70_ORIGINAL_PUBMED_XML_METADATA_ABSTRACT_EVIDENCE_LEADS"
ROLE_SCHEMA="MAIN_R70_PUBMED_ABSTRACT_ROLE_TRIAGE_NOT_CLINICAL_ADJUDICATION"
ROLES={
"40098309":"BACKGROUND_NOT_PIVOTAL",
"34105177":"EARLIER_PHASE_OTHER_COHORT",
"42848980":"PHASE2_COMPONENT_NOT_PHASE3",
"42526472":"PRIMARY_PHASE3_ABSTRACT",
"42233621":"PRIMARY_PHASE3_ABSTRACT",
"41840328":"PROTOCOL_ONLY",
"42667274":"SAME_TRIAL_SECONDARY_ANALYSIS",
"42663312":"PRIMARY_PHASE3_ABSTRACT",
"42663111":"SAME_TRIAL_SECONDARY_ANALYSIS",
"40587141":"PRIMARY_PHASE3_ABSTRACT",
"42849489":"PRIMARY_PHASE3_ABSTRACT",
}
PRIMARY={"42526472","42233621","42663312","40587141","42849489"}
SECONDARY={"42667274","42663111"}


def require(check,code):
 if not check: raise ValueError(code)


def read(path,expected_sha,max_size):
 require(path.is_file() and not path.is_symlink()
         and 20<path.stat().st_size<=max_size,
         "ORIGINAL_ARTICLE_EVIDENCE_FILE_MISSING_OR_UNSAFE")
 b=path.read_bytes()
 require(hashlib.sha256(b).hexdigest()==expected_sha,
         "ORIGINAL_NLM_ARTICLE_REPORT_DIGEST_CHANGED")
 return b


def inspect(original,raw_xml,catalog):
 require(original.get("schema")==META_SCHEMA
         and original.get("inputOriginalR69Sha256")==R69_SHA
         and original.get("focusExactNcts")==29
         and original.get("provisionalFDAApplicationGroups")==23
         and original.get("originalRegistryNctsWithoutCurrentPrimary")==17
         and original.get("articleMetadataRecordsRetrieved")==11
         and original.get("registryDerivedPubmedCitationLeads")==11
         and original.get("exactNctMentionedInArticleTitleOrAbstract")==8
         and original.get("exactNctLinkedOnlyAsPubmedDatabankAccession")==3
         and original.get("originalPubmedXmlSha256")==XML_SHA
         and original.get("originalArticleFullTextsRetrieved")==0
         and original.get("articlesWithIndependentlyAdjudicatedPivotalOutcomes")==0
         and original.get("qualifiedReviewerSignoffs")==0
         and original.get("scoredScientificMethods")==0
         and original.get("validatedFutureFdaApplicationPredictions")==0
         and original.get("measuredHistoricalForecastAccuracy") is None
         and original.get("officialFutureFDAOutcome")=="ABSTAIN"
         and original.get("modelTrainingOrProductionWrites") is False
         and original.get("pubmedAbstractsAreNotFullPublicationAnalysis") is True,
         "UNVERIFIED_NLM_ORIGINAL_REPORT_SCOPE")
 pubmed_root=ET.fromstring(raw_xml)
 articles=pubmed_root.findall(".//PubmedArticle")
 require(len(articles)==11,"NLM_RAW_XML_RECORD_COUNT_CHANGED")
 xml_pmids=[]
 for article in articles:
  elem=article.find("./MedlineCitation/PMID")
  require(elem is not None and type(elem.text) is str
          and re.fullmatch(r"[1-9]\d{5,9}",elem.text),
          "INVALID_ORIGINAL_PUBMED_XML_ID")
  xml_pmids.append(elem.text)
 require(set(xml_pmids)==set(ROLES) and len(set(xml_pmids))==11,
         "SOURCE_PUBMED_XML_MEMBERSHIP_CHANGED")
 require(catalog.get("schema")==ROLE_SCHEMA
         and catalog.get("basedOnR69Sha256")==R69_SHA
         and catalog.get("basedOnR69Run")==42727350931
         and catalog.get("verificationBasis")==
             "PUBLIC_PUBMED_AND_JOURNAL_TITLE_ABSTRACT_METADATA"
         and catalog.get("independentlyVerifiedOriginalSignedProtocolSAP") is False
         and catalog.get("qualifiedReviewerSigned") is False
         and catalog.get("externalFullTextStatisticalReviewComplete") is False
         and catalog.get("fdaOutcomeForecast")=="ABSTAIN"
         and set(catalog)=={
             "schema","basedOnR69Run","basedOnR69Sha256","verificationBasis",
             "independentlyVerifiedOriginalSignedProtocolSAP",
             "qualifiedReviewerSigned","externalFullTextStatisticalReviewComplete",
             "fdaOutcomeForecast","rows"},
         "FALSE_R70_FULL_TEXT_JUDGMENT_OR_PREDICTION")
 originals=original.get("articleResearchLeads")
 rows=catalog.get("rows")
 require(type(originals) is list and len(originals)==11 and
         type(rows) is list and len(rows)==11,
         "NLM_ORIGINAL_ARTICLE_ROLE_CENSUS_CHANGED")
 prior={x["pmid"]:x for x in originals}
 require(len(prior)==11 and set(prior)==set(ROLES),
         "NLM_ORIGINAL_ARTICLE_IDS_CHANGED")
 seen=set()
 primary_ncts=set()
 for row in rows:
  require(type(row) is list and len(row)==5 and all(type(s) is str for s in row),
          "R70_ARTICLE_ROLE_BAD_ROW")
  nct,pmid,role,title,reason=row
  evidence=prior.get(pmid)
  require(pmid not in seen and evidence is not None and
          nct==evidence.get("nct") and role==ROLES[pmid] and
          len(title)>15 and len(reason)>28 and
          evidence.get("sourceXmlSha256")==XML_SHA and
          evidence.get("clinicalGrade") is None and
          evidence.get("pivotalPhase3PrimaryResultsIndependentlyVerified") is False and
          evidence.get("statisticalEndpointsAdjudicated") is False and
          evidence.get("scientificReviewerSigned") is False and
          evidence.get("trialPhaseMatchIndependentlyVerified") is False and
          evidence.get("fullTextIndependentlyRead") is False and
          evidence.get("fdaApprovalOrCrlPrediction")=="ABSTAIN",
          "NLM_ARTICLE_ROLE_TRIAL_OR_CLINICAL_SIGNOFF_MISMATCH")
  seen.add(pmid)
  flags=evidence["literalSourceTextScopeFlags"]
  types=evidence["pubmedPublicationTypes"]
  title_original=evidence["articleTitleExactlyAsPubmed"]
  in_text=evidence["exactFocusNctIdentifierInArticleTitleOrAbstract"]
  if pmid in PRIMARY:
   require(in_text is True and
           "PRIMARY_ENDPOINT_TERM" in flags and
           "PHASE_3_TERM" in flags and
           "protocol" not in title_original.lower(),
           "FALSE_PHASE3_PRIMARY_ABSTRACT_REVIEW")
   primary_ncts.add(nct)
  elif pmid in SECONDARY:
   require(nct=="NCT06081894" and in_text is True and
           "aficamten" in title_original.lower(),
           "FALSE_INDEPENDENT_PRIMARY_TRIAL_FOR_ADDITIONAL_ACACIA_PAPER")
  elif role=="PROTOCOL_ONLY":
   require("protocol" in title_original.lower() and
           "PROTOCOL_OR_METHODS_TERM" in flags,
           "PROTOCOL_MISCLASSIFIED_AS_RESULT")
  elif role=="PHASE2_COMPONENT_NOT_PHASE3":
   require("phase ii" in title_original.lower() and
           "Clinical Trial, Phase II" in types and
           in_text is False,
           "PHASE2_COMPONENT_MISCLASSIFIED_AS_PHASE3")
  elif role=="EARLIER_PHASE_OTHER_COHORT":
   require("Clinical Trial, Phase I" in types and
           "Clinical Trial, Phase II" in types and
           in_text is False,
           "EARLIER_PHASE_STUDY_REWRITTEN_AS_PIVOTAL")
  elif role=="BACKGROUND_NOT_PIVOTAL":
   require("percentile curves" in title_original.lower() and
           in_text is False and
           "Clinical Trial, Phase III" not in types,
           "REFERENCE_CURVE_IMPERSONATES_PIVOTAL_EVIDENCE")
 require(seen==set(ROLES) and len(primary_ncts)==5 and
         primary_ncts=={"NCT05126758","NCT05662241","NCT06081894",
                        "NCT06153693","NCT06343779"},
         "PRIMARY_PUBLICATION_NOT_UNIQUE_OR_UNVERIFIED")
 return {"status":"ORIGINAL_NLM_XML_ARTICLE_ROLE_PARITY_PASSED",
     "sourcePubmedXmlSha256":XML_SHA,"articleReferences":11,
     "uniqueNctsWithArticleReferences":7,
     "potentialMainPhase3ResultAbstracts":5,
     "otherRelatedOrBackgroundCitations":6,
     "fullOriginalClinicalReportsAdjudicated":0,
     "clinicalScoresSigned":0,"FDAFutureOutcomesValidated":0,
     "futureFDAOutcome":"ABSTAIN","historicalAccuracy":None,
     "productionOrModelTrainingWrites":False}


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--nlm-original",type=Path,required=True)
 p.add_argument("--nlm-original-xml",type=Path,required=True)
 p.add_argument("--role-catalog",type=Path,required=True)
 args=p.parse_args()
 original=json.loads(read(args.nlm_original,META_SHA,500_000))
 xml=read(args.nlm_original_xml,XML_SHA,1_000_000)
 catalog_path=args.role_catalog
 require(catalog_path.is_file() and not catalog_path.is_symlink()
         and 100<catalog_path.stat().st_size<100_000,
         "R70_ROLE_CATALOG_MISSING")
 catalog=json.loads(catalog_path.read_bytes())
 print(json.dumps(inspect(original,xml,catalog),sort_keys=True))


if __name__=="__main__":
 main()
