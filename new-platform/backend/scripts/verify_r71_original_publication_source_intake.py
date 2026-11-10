#!/usr/bin/env python3
"""R71 five published main-report source intake vs original immutable R70 NLM JSON.

Checks exact primary NCT, DOI, PMID, source electronic publication date where
provided by NLM, original SHA receipts, reviewer release and 5x8 unsigned
review requirements. Publication-reported efficacy numbers remain research
excerpts, NOT independently statistically adjudicated trial outcomes.
"""
from __future__ import annotations
import argparse,hashlib,json,re
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE_SHA="03434b975e511b2d603227bab3e25768dbcc3a0e7b412d479d9afbd100cd2577"
SOURCE_XML_SHA="2aa5fac13c7741d7ed2d9b1c2d91101978661150c87324b566b88f75994e394b"
EXPECTED={
 "NCT05126758":("42526472","10.1016/S0140-6736(26)01385-1"),
 "NCT05662241":("42233621","10.1056/NEJMoa2601337"),
 "NCT06081894":("42663312","10.1056/NEJMoa2603021"),
 "NCT06153693":("40587141","10.1001/jama.2025.9413"),
 "NCT06343779":("42849489","10.1016/S0140-6736(26)01296-1")
}
SCHEMA="MAIN_R71_FIVE_PIVOTAL_ABSTRACT_RESULT_AND_FULLTEXT_ACCESS_REVIEW_ONLY"
XML_SHA="2aa5fac13c7741d7ed2d9b1c2d91101978661150c87324b566b88f75994e394b"
# Exact strings (after decimal normalization) present BOTH in the original NLM
# abstract and in the source-reported frontend excerpt. Their presence means
# attribution/parity only, NEVER independent statistical adjudication.
PUBLISHED_RESULT_LITERALS={
 "42526472":("4.55","0.47","8.63","0.029"),
 "42233621":("0.44","0.28","0.71","0.001"),
 "42663312":("0.67","0.22","1.11","0.003","3.0","0.02"),
 "40587141":("-9.1","-13.3","-4.9","0.001"),
 "42849489":("1.28","0.0001")
}

def norm(s):
 s=s.replace("·",".").replace("−","-").replace(" "," ").replace("–","-")
 return re.sub(r"(?<![0-9])\.(\d+)",r"0.\1",s)


def require(ok,code):
 if not ok: raise ValueError(code)

def safe_json(path,max_bytes=200000):
 require(path.is_file() and not path.is_symlink()
   and 80<path.stat().st_size<max_bytes,"R71_SOURCE_JSON_MISSING_OR_UNSAFE")
 raw=path.read_bytes()
 d=json.loads(raw)
 require(type(d) is dict,"SOURCE_NOT_OBJECT")
 return d,hashlib.sha256(raw).hexdigest()

def verify(meta,sha,data,abstracts):
 require(sha==SOURCE_SHA
         and meta.get("schema")=="MAIN_R70_ORIGINAL_PUBMED_XML_METADATA_ABSTRACT_EVIDENCE_LEADS"
         and meta.get("originalPubmedXmlSha256")==SOURCE_XML_SHA
         and meta.get("focusExactNcts")==29
         and meta.get("provisionalFDAApplicationGroups")==23
         and meta.get("registryDerivedPubmedCitationLeads")==11
         and meta.get("articleMetadataRecordsRetrieved")==11
         and meta.get("originalArticleFullTextsRetrieved")==0
         and meta.get("articlesWithIndependentlyAdjudicatedPivotalOutcomes")==0
         and meta.get("qualifiedReviewerSignoffs")==0
         and meta.get("scoredScientificMethods")==0
         and meta.get("validatedFutureFdaApplicationPredictions")==0
         and meta.get("officialFutureFDAOutcome")=="ABSTAIN"
         and meta.get("measuredHistoricalForecastAccuracy") is None
         and meta.get("modelTrainingOrProductionWrites") is False,
         "NOT_EXACT_SOURCE_ONLY_NLM_ARCHIVE")
 require(data.get("schema")==SCHEMA
         and data.get("reviewDate")=="2026-11-09"
         and data.get("originalR70PubmedResearchRun")==42729546458
         and data.get("originalR70PubmedSha256")==sha
         and data.get("verificationType")==
             "PUBLISHED_RESULTS_OR_EXCERPTS_WITH_EXPLICIT_UNREVIEWED_ORIGINAL_PROSPECTIVE_SAP"
         and data.get("originalSignedPreunblindingStatisticalPlansVerified")==0
         and data.get("independentQualifiedScienceReviews")==0
         and data.get("validatedFutureFdaApplicationForecasts")==0
         and data.get("officialFDAForecast")=="ABSTAIN"
         and set(data)=={"schema","reviewDate","originalR70PubmedResearchRun",
             "originalR70PubmedSha256","verificationType",
             "originalSignedPreunblindingStatisticalPlansVerified",
             "independentQualifiedScienceReviews",
             "validatedFutureFdaApplicationForecasts","officialFDAForecast",
             "cases"},
         "R71_UNAUTHORIZED_CLINICAL_GRADE_OR_APPROVAL_PREDICTION")
 raw_leads=meta.get("articleResearchLeads")
 require(type(raw_leads) is list and len(raw_leads)==11,
         "NLM_ARTICLE_CENSUS_CHANGED")
 original={r["pmid"]:r for r in raw_leads}
 require(len(original)==11,"DUPLICATE_ORIGINAL_PUBLICATION")
 cases=data["cases"]
 require(type(cases) is list and len(cases)==5,
         "FIVE_ORIGINAL_MAIN_TRIALS_REQUIRED")
 seen=set()
 link_counts=0
 for case in cases:
  n=case.get("nct"); p=case.get("pmid"); doi=case.get("doi")
  require(n in EXPECTED and n not in seen and
          (p,doi)==EXPECTED[n] and p in original and
          case.get("fullOriginalPaperIndependentlyRead") is False and
          case.get("published") and case["published"]<="2026-11-09" and
          isinstance(case.get("specificReviewNeeds"),list) and
          len(case["specificReviewNeeds"])>=3,
          "R71_TRIAL_PAPER_OR_REVIEW_REQUIREMENT_INVALID")
  src=original[p]
  abstract=abstracts.get(p)
  require(type(abstract) is str and n in abstract and
          src.get("exactFocusNctIdentifierInArticleTitleOrAbstract") is True,
          "ORIGINAL_PIVOTAL_STUDY_NCT_ABSTRACT_NOT_EXPLICIT")
  for literal in PUBLISHED_RESULT_LITERALS[p]:
   require(literal in norm(abstract) and literal in norm(case["reportedEffect"]),
           "SOURCE_REPORTED_EFFICACY_LITERAL_NOT_IN_ORIGINAL_NLM_ABSTRACT")
  require(src.get("nct")==n and src.get("doiAsPubmed")==doi
          and src.get("sourceAbstractAvailable") is True
          and src.get("scientificReviewerSigned") is False
          and src.get("pivotalPhase3PrimaryResultsIndependentlyVerified") is False
          and src.get("preUnblindingProtocolSapVersionVerified") is False
          and src.get("fullTextIndependentlyRead") is False
          and src.get("trialPhaseMatchIndependentlyVerified") is False
          and src.get("fdaApprovalOrCrlPrediction")=="ABSTAIN",
          "ORIGINAL_PUBMED_ID_OR_UNREVIEWED_STATUS_MISMATCH")
  if src.get("sourceElectronicPublicationDate") is not None:
   require(src["sourceElectronicPublicationDate"]==case["published"],
           "R71_PUBLICATION_DATE_DIFFERS_FROM_ORIGINAL_NLM")
  else:
   require(n=="NCT06153693" and case["published"]=="2025-06-30",
           "ORIGINAL_PUBMED_DATE_UNKNOWN_REQUIRES_PUBLISHER_PROVENANCE")
  require(case["articleUrl"].startswith("https://") and
          case["journalUrl"].startswith("https://") and
          (case.get("supplementUrl") is None or
           case["supplementUrl"].startswith("https://")),
          "INVALID_EXTERNAL_ARTICLE_OR_SUPPLEMENT_URL")
  if case.get("supplementUrl") is not None:link_counts+=1
  for key in ("primaryEndpoint","reportedEffect","analysisPopulation","safetyObservation"):
   require(type(case.get(key)) is str and 35<=len(case[key])<=500,
           "MISSING_ORIGINAL_PUBLICATION_FIELD_"+key)
  seen.add(n)
 require(seen==set(EXPECTED) and link_counts==3,
         "R71_FIVE_ORIGINAL_REPORTS_OR_SUPPLEMENT_LINK_COUNT_CHANGED")
 return {"status":"PASS","sourceSha256":sha,
         "exactOriginalPublishedNcts":5,"originalPivotalCandidates":5,
         "publishedProtocolOrSupplementListings":3,
         "scientificAssessmentPositionsUnscored":40,
         "originalLockedSapsVerified":0,
         "qualifiedScientificSignoffs":0,
         "validatedFdaForecasts":0,"FDAOutcome":"ABSTAIN",
         "noProductionWrites":True}

if __name__=="__main__":
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--original-nlm",type=Path,required=True)
 p.add_argument("--original-nlm-xml",type=Path,required=True)
 p.add_argument("--frontend",type=Path,required=True)
 args=p.parse_args()
 original,sha=safe_json(args.original_nlm)
 require(args.original_nlm_xml.is_file() and not args.original_nlm_xml.is_symlink()
   and 100<args.original_nlm_xml.stat().st_size<2_000_000,
   "SOURCE_RAW_PUBMED_XML_MISSING")
 raw_xml=args.original_nlm_xml.read_bytes()
 require(hashlib.sha256(raw_xml).hexdigest()==XML_SHA,
   "R71_ORIGINAL_NLM_ABSTRACT_XML_SHA_CHANGED")
 root=ET.fromstring(raw_xml)
 abstracts={}
 for node in root.findall(".//PubmedArticle"):
  pmid=node.findtext("./MedlineCitation/PMID")
  require(pmid not in abstracts and type(pmid) is str,"ORIGINAL_PUBMED_XML_DUPLICATE")
  abstracts[pmid]=" ".join("".join(e.itertext()) for e in
    node.findall("./MedlineCitation/Article/Abstract/AbstractText"))
 require(len(abstracts)==11,"R71_EXPECTED_EXACT_11_NLM_ABSTRACT_RECORDS")
 data,_=safe_json(args.frontend)
 print(json.dumps(verify(original,sha,data,abstracts),sort_keys=True))
