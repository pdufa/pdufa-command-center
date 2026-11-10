#!/usr/bin/env python3
"""R47 track B: historical source cohort screening, NEVER an accuracy rating.

Independent reference protocol handles true as-published predecision evidence
but the selected approval/CRL publication sources do NOT constitute an unbiased
consecutive original NDA/BLA filing or review-cycle denominator.
"""
from __future__ import annotations
import argparse,hashlib,json
from datetime import date,datetime,timezone
from pathlib import Path
from app.hop_blinded_phase3_backtest import evaluate_replay_protocol
from app.hop_probability_calibration import calibration_readiness_status

def verify(candidate_doc,receipt,raw_candidates:bytes,at:str)->dict:
    if (not isinstance(candidate_doc,list) or not isinstance(receipt,dict)
        or receipt.get("schema")!="MAIN_FDA_PUBLIC_SOURCE_REPLAY_R38"
        or receipt.get("status")!="SELECTED_SOURCES_NOT_A_COMPLETE_FDA_COHORT"
        or receipt.get("candidateFileSha256")!=hashlib.sha256(raw_candidates).hexdigest()
        or receipt.get("researchCandidateRows")!=len(candidate_doc)
        or receipt.get("completeOriginalApplicationFilingRosterVerified") is not False
        or receipt.get("allPdufaReviewCyclesIndependentlyEnumerated") is True
        or receipt.get("modelEligibleHistoricalCases")!=0
        or receipt.get("historicalRealBacktests")!=0
        or receipt.get("trainingAuthorized") is not False
        or receipt.get("approvalProbability") is not None):
        raise ValueError("UNQUALIFIED_FDA_COHORT_OR_SOURCE_HASH_MISMATCH")
    if any(not isinstance(r,dict) or r.get("modelEligible") is not False or
            r.get("exactReviewCycleIndependentlyVerified") is not False or
            r.get("predecisionEvidenceVerified") is not False or
            r.get("publicOutcomeLabelDateIndependentlyVerified") is not False
            for r in candidate_doc):
        raise ValueError("UNVERIFIED_FDA_SOURCE_PROMOTED_TO_LABEL")
    measured=evaluate_replay_protocol(frozen_packets=[],provisional_predictions=[],
       outcome_vault=[],as_of=date.fromisoformat(at[:10]))
    if (measured["independentRealBacktests"]!=0 or
        measured["measuredProspectiveAccuracy"] is not None or
        measured["fdaProbability"] is not None or measured["trainingAuthorized"] is not False):
        raise ValueError("INVALID_HISTORICAL_CALIBRATION_RELEASE")
    report={
     "schema":"MAIN_R47_HISTORICAL_SOURCE_BUILD_CHECKPOINT",
     "generatedAtUtc":at,"originalFdaSourceReceiptSha256":hashlib.sha256(
       json.dumps(receipt,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
     "candidateFileSha256":hashlib.sha256(raw_candidates).hexdigest(),
     "researchSourceActionCandidates":len(candidate_doc),
     "researchClasses":receipt.get("researchClasses",{}),
     "completeConsecutiveOriginalFilingCohort":False,
     "pendingAndWithdrawnCycleCoverageIndependentlyVerified":False,
     "exactCycleOutcomesAdjudicated":0,"frozenPredecisionClinicalPackets":0,
     "pairedIndependentHistory":0,"qualifiedResearchPredictions":0,
     "qualifiedClinicalReviewerSignoffs":0,"outOfTimeValidationCases":0,
     "prospectiveAccuracy":None,"calibration":None,"approvalProbability":None,
     "replayProtocolHealth":"LEAKAGE_GUARDS_PASS_EMPTY_REAL_COHORT",
     "missingGates":[
      "CONSECUTIVE_FULL_ORIGINAL_APPLICATION_FILING_COHORT",
      "EXACT_APPLICATION_CYCLE_AND_PENDING_WITHDRAWN_OUTCOME_DENOMINATOR",
      "BEFORE_FDA_DECISION_ORIGINAL_PIVOTAL_RESULTS_AND_AS_PUBLISHED_VERSIONS",
      "SEALED_OUTCOME_BLIND_PREDECISION_PREDICTION",
      "INDEPENDENT_FDA_ACTION_LABEL_SIGNOFF",
      "TEMPORALLY_HELD_OUT_CASES_AND_CALIBRATION"
     ],
     "modelTrainingAuthorized":False,"productionWriteAuthorized":False,
     "automaticAccuracyOrHundredPercentClaimAuthorized":False,
     "status":"LIVE_HISTORICAL_FDA_CANDIDATE_SOURCE_RESEARCH_NOT_REAL_BACKTEST",
     "warning":"This checks the actual fresh FDA source candidates and backtest leakage guard. It does not issue retrospective predictions, calculate real historical accuracy or improve a model automatically."
    }
    report["calibrationProtocol"]=calibration_readiness_status(source_checkpoint=report)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidates",type=Path,required=True)
    p.add_argument("--receipt",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir():
        raise ValueError("IMMUTABLE_REVIEW_REPORT_REQUIRED")
    for path in (a.candidates,a.receipt):
        if path.is_symlink() or not path.is_file() or path.stat().st_size>85_000_000:
            raise ValueError("UNVERIFIED_FDA_ORIGINAL_SOURCE_PATH")
    raw=a.candidates.read_bytes()
    report=verify(json.loads(raw),json.loads(a.receipt.read_bytes()),raw,
       datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with a.output.open("x") as file:file.write(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("researchSourceActionCandidates",
       "pairedIndependentHistory","prospectiveAccuracy","replayProtocolHealth","status")},sort_keys=True))

if __name__=="__main__":main()
