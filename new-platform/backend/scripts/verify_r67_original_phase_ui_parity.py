#!/usr/bin/env python3
"""R67 original byte-exact dated registry phase/status-to-UI parity gate.

Checks all 29 original source fields against the archived R66 original
research. A successful result is not a licensed clinical reviewer approval,
real FDA application state, science grade or historical forecast accuracy.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path

SHA="be3f8f0f4351579a7eddea2ebb67654992f8dd8f5125cbd78bf56ed440f43257"
R46="7e1681399ed242d0080d8517bbe62cfb931e88e1340295fdf9839affbc0d3f92"
R65="1238d5a0ed120cd47d05dec12486e59e2bf8dbd6e7b73b989372955db622127a"
SCHEMA="MAIN_R66_EXACT_ORIGINAL_29_TRIAL_PHASE_SOURCE_CENSUS"

def require(ok,code):
 if not ok:raise ValueError(code)

def read(path,limit):
 require(path.is_file() and not path.is_symlink()
         and 10<path.stat().st_size<limit,"SOURCE_MISSING_UNSAFE")
 raw=path.read_bytes()
 value=json.loads(raw)
 require(type(value) is dict,"SOURCE_INVALID_JSON")
 return value,hashlib.sha256(raw).hexdigest()

def expected_compact(original,hash_):
 require(hash_==SHA and original.get("schema")==SCHEMA
         and original.get("inputsPinnedOriginalSha256")=={"r46":R46,"r65":R65}
         and original.get("exactNcts")==29
         and original.get("provisionalApplicationCycles")==23
         and original.get("registryReportedPhase3Only")==28
         and original.get("registryReportedPhase2Phase3")==1
         and original.get("registryReportedCompleted")==19
         and original.get("registryReportedActiveNotRecruiting")==8
         and original.get("registryReportedRecruiting")==2
         and original.get("registryReportedRandomized")==28
         and original.get("registryReportedAllocationNA")==1
         and original.get("independentlyQualifiedPhaseReviews")==0
         and original.get("signedScientificMethodGrades")==0
         and original.get("futureFDAOutcomePredictionsValidated")==0
         and original.get("officialFutureFDAOutcome")=="ABSTAIN"
         and original.get("officialFDAReviewDelay")=="ABSTAIN"
         and original.get("measuredForecastAccuracy") is None
         and original.get("historicalOutcomesInspected") is False
         and original.get("productionOrReviewerLedgerWrites") is False
         and original.get("phaseFieldsFromSourceAreNotClinicalOrRegulatoryAdjudications") is True,
         "R66_SOURCE_OR_FALSE_REVIEW_PROMOTION")
 trials=original.get("originalRegistryPhaseEvidence")
 groups=original.get("provisionalApplicationPhaseEvidence")
 require(type(trials) is list and len(trials)==29 and
         type(groups) is list and len(groups)==23 and
         len({x["nct"] for x in trials})==29 and
         len({g["applicationCycleId"] for g in groups})==23,
         "ORIGINAL_R66_TRIAL_APPLICATION_IDENTITY_CHANGED")
 member={g["applicationCycleId"]:g for g in groups}
 rows=[]
 for t in trials:
  n=t["nct"]
  require(re.fullmatch(r"NCT\d{8}",n)
          and t["exactOriginalRegistryRecord"]=="https://clinicaltrials.gov/study/"+n
          and t["independentPhaseReviewEventId"] is None
          and t["clinicalMethodGradesCalculated"]==0
          and t["fdaPrediction"]=="ABSTAIN"
          and t["requiresHumanPhaseValidation"] is True
          and t["originalPreUnblindingScientificHierarchyVerified"] is False
          and all(n in member[a]["linkedNcts"] for a in t["applicationCycleIds"]),
          "R66_ORIGINAL_TRIAL_INDEPENDENT_PHASE_STATUS_CHANGED")
  rows.append([
    n,",".join(t["sourceReportedPhases"]),t["sourceReportedStatus"],
    t["sourceRegistryLastUpdatePostedDate"],t["sourceReportedStatusVerifiedMonth"],
    t["sourceReportedAllocation"],t["sourceReportedMasking"],
    t["sourceReportedEnrollmentCount"],t["sourceReportedEnrollmentType"],
    t["sourceReportedPrimaryCompletionDate"],t["sourceReportedPrimaryCompletionDateType"]
  ])
 return {"schema":"MAIN_R67_COMPACT_ORIGINAL_R66_PHASE_SOURCE_ONLY",
         "run":42720903307,"artifact":13720041195,
         "originalR66Sha256":SHA,"rows":rows}

def verify(original_path,frontend_path):
 original,h=read(original_path,500000)
 compact,_=read(frontend_path,50000)
 require(compact==expected_compact(original,h),
         "FRONTEND_REGISTRY_PHASE_DATA_DRIFT_FROM_ORIGINAL_R66")
 return {"status":"PASS","sourceRun":42720903307,"sourceSha256":h,
         "exactNcts":29,"applicationCycles":23,
         "phase3Only":28,"combinedPhase23":1,
         "completed":19,"activeNotRecruiting":8,"recruiting":2,
         "independentPhaseSignoffs":0,"scientificGrades":0,
         "validatedFDAPredictions":0,"FdaPrediction":"ABSTAIN",
         "productionWrites":False}

if __name__=="__main__":
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("--original",type=Path,required=True)
 parser.add_argument("--frontend",type=Path,required=True)
 arg=parser.parse_args()
 print(json.dumps(verify(arg.original,arg.frontend),sort_keys=True))
