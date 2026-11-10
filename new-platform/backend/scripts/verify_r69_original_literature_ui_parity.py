#!/usr/bin/env python3
"""MAIN R69: fail closed unless every displayed PubMed PMID matches archived
original R69 ClinicalTrials.gov DERIVED reference receipt. No clinical grade.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path

ORIGINAL_SHA="8b11d9f7e6f8896286944a454569b59cac9d63c5350fcb9665e6ff47e5519e77"
SCHEMA="MAIN_R69_ORIGINAL_REGISTRY_PUBMED_REFERENCE_LEAD_RECOVERY"
NCT=re.compile(r"NCT[0-9]{8}\Z")
PMID=re.compile(r"[1-9][0-9]{5,9}\Z")

def require(ok,code):
 if not ok:raise ValueError(code)

def load(path,size):
 require(path.is_file() and not path.is_symlink() and 50<path.stat().st_size<size,
         "R69_ORIGINAL_RESEARCH_FILE_MISSING_OR_UNSAFE")
 raw=path.read_bytes()
 d=json.loads(raw)
 require(type(d) is dict,"R69_ORIGINAL_REPORT_NOT_OBJECT")
 return d,hashlib.sha256(raw).hexdigest()

def canonical(orig,digest):
 require(digest==ORIGINAL_SHA and orig.get("schema")==SCHEMA
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
         and orig.get("registryReferenceCannotEstablishTrialEfficacy") is True
         and orig.get("externalArticlesNotFetchedOrContentAdjudicated") is True
         and orig.get("historicalBacktestDataInspected") is False
         and orig.get("modelTrainingOrProductionWrites") is False,
         "R69_ORIGINAL_REPORT_INTEGRITY_OR_FORECAST_RELEASE_DRIFT")
 cases=orig.get("missingPrimaryLiteratureReviewQueue")
 require(type(cases) is list and len(cases)==17
         and len({t["nct"] for t in cases})==17,
         "ORIGINAL_MISSING_PRIMARY_TRIAL_CENSUS_CHANGED")
 rows=[]
 for t in cases:
  n=t["nct"]
  require(type(n) is str and NCT.fullmatch(n)
          and t["currentRegistryPrimaryTables"]==0
          and t["originalRegistryUrl"]=="https://clinicaltrials.gov/study/"+n
          and t["mustVerifyExactNctInFullPublication"] is True
          and t["mustVerifyOriginalSignedProspectiveSap"] is True
          and t["independentEfficacyAssessment"] is None
          and t["independentSafetyAssessment"] is None
          and t["scientificMethodGrade"] is None
          and t["officialFdaForecast"]=="ABSTAIN",
          "R69_PUBLICATION_CASE_HAS_UNAUTHORIZED_EVIDENCE_GRADE")
  leads=t["registryDerivedPubmedReferenceLeads"]
  require(type(leads) is list and len(leads)<20,
          "UNTRUSTED_PUBLICATION_LEADS")
  pmids=[]
  for lead in leads:
   p=lead.get("pmid")
   require(type(p) is str and PMID.fullmatch(p)
           and lead.get("pubmedUrl")=="https://pubmed.ncbi.nlm.nih.gov/"+p+"/"
           and lead.get("registryReferenceType")=="DERIVED"
           and lead.get("articleContentIndependentlyInspected") is False
           and lead.get("exactNctMentionInArticleVerified") is False
           and lead.get("paperReportsPivotalPrimaryOutcomeVerified") is False
           and lead.get("independentQualifiedPublicationReviewSigned") is False
           and lead.get("publicationIsCandidateLeadNotConfirmedTrialResult") is True,
           "PUBMED_CANDIDATE_WRONGLY_CLAIMED_AS_EXACT_STUDY_RESULT")
   pmids.append(p)
  require(len(pmids)==len(set(pmids)),"DUPLICATED_NCT_PUBLICATION")
  rows.append([n,pmids])
 require(sum(len(x[1]) for x in rows)==11 and
         sum(bool(x[1]) for x in rows)==7,"PUBMED_CANDIDATE_COUNTS_DRIFT")
 return {"schema":"MAIN_R69_COMPACT_UNVERIFIED_ORIGINAL_REGISTRY_PUBLICATION_LEADS",
         "run":42727350931,"artifact":13723526354,
         "originalR69Sha256":ORIGINAL_SHA,"rows":rows}

def verify(original,frontend):
 orig,digest=load(original,1_000_000)
 compact,_=load(frontend,40_000)
 require(compact==canonical(orig,digest),
         "R69_DISPLAY_PUBLICATION_PMIDS_DIFFER_FROM_IMMUTABLE_SOURCE")
 return {"status":"PASS","sourceSha256":digest,"exactNcts":29,
         "missingPrimaryTrials":17,"candidatePubmedIds":11,
         "trialsWithCandidateReferences":7,
         "originalArticlesFetchedOrReviewed":0,
         "qualifiedScienceGrades":0,"validatedFDAPredictions":0,
         "futureFDAOutcome":"ABSTAIN","productionWrites":False}

if __name__=="__main__":
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("--original",type=Path,required=True)
 parser.add_argument("--frontend",type=Path,required=True)
 arg=parser.parse_args()
 print(json.dumps(verify(arg.original,arg.frontend),sort_keys=True))
