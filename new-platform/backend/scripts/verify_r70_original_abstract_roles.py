#!/usr/bin/env python3
"""R70: every publication role must map to an unchanged original R69 PMID/NCT.

R70 editorial classification is based on public PubMed/journal title/abstract.
This does NOT independently verify original full clinical study reports,
locked pre-unblinding SAPs, safety, qualified scientific grades or FDA outcomes.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
R69_SHA="8b11d9f7e6f8896286944a454569b59cac9d63c5350fcb9665e6ff47e5519e77"
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
R69_SCHEMA="MAIN_R69_ORIGINAL_REGISTRY_PUBMED_REFERENCE_LEAD_RECOVERY"
R70_SCHEMA="MAIN_R70_PUBMED_ABSTRACT_ROLE_TRIAGE_NOT_CLINICAL_ADJUDICATION"

def guard(ok,message):
 if not ok: raise ValueError(message)

def load(path,limit):
 guard(path.is_file() and not path.is_symlink()
       and 50<path.stat().st_size<limit,
       "UNSAFE_ORIGINAL_PUBLICATION_SOURCE")
 blob=path.read_bytes()
 doc=json.loads(blob)
 guard(type(doc) is dict,"INVALID_PUBLICATION_JSON_OBJECT")
 return doc,hashlib.sha256(blob).hexdigest()

def validate(orig,sha,triage):
 guard(sha==R69_SHA and orig.get("schema")==R69_SCHEMA
       and orig.get("canonicalUniqueNcts")==29
       and orig.get("provisionalApplicationCycles")==23
       and orig.get("originalRegistryNoCurrentPrimaryTrials")==17
       and orig.get("missingPrimaryTrialsWithPubmedReferenceLeads")==7
       and orig.get("missingPrimaryTrialsWithoutPubmedReferenceLeads")==10
       and orig.get("registryListedUnverifiedPubmedReferences")==11
       and orig.get("independentlyVerifiedArticlesReportingExactTrialPrimary")==0
       and orig.get("independentlyQualifiedReviewerAssessments")==0
       and orig.get("validatedFutureFDAForecasts")==0
       and orig.get("FDAOutcome")=="ABSTAIN"
       and orig.get("measuredPredictionAccuracy") is None
       and orig.get("externalArticlesNotFetchedOrContentAdjudicated") is True
       and orig.get("historicalBacktestDataInspected") is False
       and orig.get("modelTrainingOrProductionWrites") is False,
       "ORIGINAL_R69_RESEARCH_SHA_OR_CLINICAL_GRADE_DRIFT")
 cases=orig.get("missingPrimaryLiteratureReviewQueue")
 guard(type(cases) is list and len(cases)==17
       and len({t["nct"] for t in cases})==17,
       "ORIGINAL_R69_MISSING_PRIMARY_ROSTER_DRIFT")
 ids={}
 for study in cases:
  n=study["nct"]
  guard(re.fullmatch(r"NCT[0-9]{8}",n) and
        study.get("scientificMethodGrade") is None and
        study.get("independentEfficacyAssessment") is None and
        study.get("officialFdaForecast")=="ABSTAIN" and
        study.get("mustVerifyExactNctInFullPublication") is True,
        "ORIGINAL_R69_REVIEW_NOT_PENDING")
  for article in study["registryDerivedPubmedReferenceLeads"]:
   pmid=article["pmid"]
   guard(pmid not in ids and
         article.get("registryReferenceType")=="DERIVED" and
         article.get("pubmedUrl")=="https://pubmed.ncbi.nlm.nih.gov/"+pmid+"/" and
         article.get("exactNctMentionInArticleVerified") is False and
         article.get("paperReportsPivotalPrimaryOutcomeVerified") is False and
         article.get("independentQualifiedPublicationReviewSigned") is False,
         "ORIGINAL_R69_PUBLICATION_NOT_UNVERIFIED")
   ids[pmid]=n
 guard(set(ids)==set(ROLES),"R69_ORIGINAL_PMIDS_DIFFER_FROM_R70_CURATION")
 guard(set(triage)=={
       "schema","basedOnR69Run","basedOnR69Sha256",
       "verificationBasis","independentlyVerifiedOriginalSignedProtocolSAP",
       "qualifiedReviewerSigned","externalFullTextStatisticalReviewComplete",
       "fdaOutcomeForecast","rows"
       } and
       triage.get("schema")==R70_SCHEMA and
       triage.get("basedOnR69Run")==42727350931 and
       triage.get("basedOnR69Sha256")==sha and
       triage.get("verificationBasis")=="PUBLIC_PUBMED_AND_JOURNAL_TITLE_ABSTRACT_METADATA" and
       triage.get("independentlyVerifiedOriginalSignedProtocolSAP") is False and
       triage.get("qualifiedReviewerSigned") is False and
       triage.get("externalFullTextStatisticalReviewComplete") is False and
       triage.get("fdaOutcomeForecast")=="ABSTAIN",
       "R70_UNAUTHORIZED_SCIENTIFIC_REVIEW_OR_FORECAST")
 rows=triage["rows"]
 guard(type(rows) is list and len(rows)==11,
       "R70_MISSING_PUBLICATION_ROLES")
 seen=set()
 byrole={}
 matched_trial=set()
 for row in rows:
  guard(type(row) is list and len(row)==5 and
        all(type(v) is str and 12<=len(v)<=260
            for v in (row[3],row[4])) and
        type(row[0]) is str and type(row[1]) is str and type(row[2]) is str,
        "R70_PAPER_ROLE_STRUCTURE_INVALID")
  n,pmid,role,title,reason=row
  guard(pmid not in seen and pmid in ids and ids[pmid]==n
        and ROLES[pmid]==role and len(title)>15 and len(reason)>28,
        "R70_PUBMED_ROLE_NCT_OR_TITLE_INCONSISTENCY")
  seen.add(pmid)
  byrole[role]=byrole.get(role,0)+1
  if role=="PRIMARY_PHASE3_ABSTRACT":
   matched_trial.add(n)
 guard(len(seen)==11 and len(matched_trial)==5 and
       byrole=={
        "PRIMARY_PHASE3_ABSTRACT":5,
        "SAME_TRIAL_SECONDARY_ANALYSIS":2,
        "PROTOCOL_ONLY":1,
        "PHASE2_COMPONENT_NOT_PHASE3":1,
        "EARLIER_PHASE_OTHER_COHORT":1,
        "BACKGROUND_NOT_PIVOTAL":1
       } and matched_trial=={
        "NCT05126758","NCT05662241","NCT06081894",
        "NCT06153693","NCT06343779"},
       "R70_ABSTRACT_ROLE_COUNT_OR_UNIQUE_TRIAL_DRIFT")
 return {"status":"PASS","originalR69Sha256":sha,
  "originalExactNcts":29,"originalApplicationCycles":23,
  "candidatePubMedCitations":11,
  "potentialPrimaryPhase3AbstractReports":5,
  "distinctPotentialPrimaryTrials":5,
  "sameTrialSecondaryAnalyses":2,"designOnlyPapers":1,
  "otherPriorPhaseOrBackgroundPapers":3,
  "fullPivotalMethodsIndependentlyReviewed":0,
  "qualifiedClinicalGrades":0,"validatedFDAForecasts":0,
  "officialFDAOutcome":"ABSTAIN",
  "productionOrModelTrainingWrites":False}

def main():
 a=argparse.ArgumentParser(description=__doc__)
 a.add_argument("--r69-original",required=True,type=Path)
 a.add_argument("--r70-frontend",required=True,type=Path)
 args=a.parse_args()
 original,sha=load(args.r69_original,1000000)
 new,_=load(args.r70_frontend,100000)
 print(json.dumps(validate(original,sha,new),sort_keys=True))

if __name__=="__main__":
 main()
