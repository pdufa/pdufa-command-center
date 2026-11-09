#!/usr/bin/env python3
"""Public FDA action-source refresh; never a complete historic filing cohort."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date,datetime,timezone
import hashlib,json
from pathlib import Path
from app.hop_fda_action_candidate_universe import build_fda_action_candidate_queue

ROOT=Path(__file__).resolve().parents[1]
BENCH=ROOT/"app/research_sources/hop_fda_pdufa_filing_benchmarks.json"
APP="drugsfda_approved_registry_quarantined.json"
CRL="fda_crl_published_quarantined.json"

def no_duplicates(pairs):
    obj={}
    for key,value in pairs:
        if key in obj:raise ValueError("DUPLICATE_FDA_SOURCE_JSON_PROPERTY")
        obj[key]=value
    return obj

def load_source(path:Path,expected_name:str)->tuple[dict,dict]:
    if not path.is_file() or path.is_symlink() or path.name!=expected_name:
        raise ValueError("INVALID_FDA_SOURCE_PATH")
    length=path.stat().st_size
    if length<30 or length>85_000_000:raise ValueError("FDA_SOURCE_SIZE_NOT_BOUNDED")
    original=path.read_bytes()
    doc=json.loads(original,object_pairs_hook=no_duplicates)
    if not isinstance(doc,dict):raise ValueError("FDA_SOURCE_NOT_OBJECT")
    return doc,{"file":expected_name,"bytes":len(original),
        "sha256":hashlib.sha256(original).hexdigest(),
        "exportedOn":doc.get("source_export_date"),"retrievedOn":doc.get("retrieved_on")}

def research_refresh(approved:dict,crl:dict,benchmarks:dict,as_of:date)->tuple[dict,list]:
    if type(as_of) is not date:raise ValueError("EXPLICIT_AS_OF_REQUIRED")
    source=build_fda_action_candidate_queue(approved,crl,benchmarks,as_of=as_of)
    rows=source.pop("researchCandidates")
    if (source.get("status")!="FDA_ACTION_CANDIDATE_UNION_FROM_SELECTED_PUBLISHED_SOURCES_NOT_A_COMPLETE_COHORT"
        or source.get("sourceUniverse")!="APPROVED_PRODUCT_AND_PUBLISHED_CRL_SELECTION_BIASED"
        or source.get("applicationLevelFilingDenominatorIndependentlyVerified") is not False
        or source.get("allPendingWithdrawnAndUnapprovedCasesRepresented") is not False
        or source.get("allPdufaReviewCyclesIndependentlyEnumerated") is not False
        or source.get("independentlyVerifiedModelEligibleCycles")!=0
        or source.get("independentRealBacktests")!=0
        or source.get("approvalProbability") is not None
        or source.get("predictionAccuracy") is not None
        or source.get("trainingAuthorized") is not False
        or source.get("tradeAuthorized") is not False
        or not isinstance(rows,list) or len(rows)!=source.get("researchCandidateRows")):
        raise ValueError("FDA_CANDIDATES_NOT_QUARANTINED")
    seen=set()
    for row in rows:
        if not isinstance(row,dict) or any(row.get(k) is not False for k in (
                "modelEligible","exactReviewCycleIndependentlyVerified",
                "publicOutcomeLabelDateIndependentlyVerified","predecisionEvidenceVerified")):
            raise ValueError("UNVERIFIED_CANDIDATE_PROMOTED_TO_MODEL_LABEL")
        key=(row.get("source"),row.get("sourceRecordSha256"),row.get("reportedActionDate"),
             row.get("sourceAction"),row.get("sourceOriginalSubmissionNo"),
             row.get("sourceOriginalOrSupplementUnit"))
        if key in seen:raise ValueError("DUPLICATE_FDA_SOURCE_CANDIDATE")
        seen.add(key)
    report={
        "schema":"MAIN_FDA_PUBLIC_SOURCE_REPLAY_R38",
        "status":"SELECTED_SOURCES_NOT_A_COMPLETE_FDA_COHORT",
        "asOf":as_of.isoformat(),
        "sourceExports":source["sourceExports"],
        "sourceRecordsInspected":source["sourceRecordsInspected"],
        "researchCandidateRows":len(rows),
        "researchClasses":dict(sorted(Counter(r["researchClass"] for r in rows).items())),
        "fiscalActionYearSourceCandidates":source["selectedFiscalActionYears"],
        "completeOriginalApplicationFilingRosterVerified":False,
        "pendingWithdrawnAndNeverApprovedCasesEnumerated":False,
        "exactReviewCyclesIndependentlyAdjudicated":False,
        "publicOutcomeClocksIndependentlyVerified":False,
        "frozenPredecisionFeaturesVerified":False,
        "modelEligibleHistoricalCases":0,
        "historicalRealBacktests":0,
        "approvalProbability":None,"measuredAccuracy":None,
        "trainingAuthorized":False,"tradeAuthorized":False,
        "retentionLimit":"GITHUB_ARTIFACT_90_DAYS_NOT_PERMANENT_BACKUP",
        "nextRequired":"Exhaustive original NDA/BLA filing roster, pending and withdrawn census, independent application-cycle outcomes, source-publication clocks and frozen predecision features",
        "warning":"FY original-filing counts cannot be a denominator for FY action-source candidates"
    }
    return report,rows

def write_snapshot(approved_file:Path,crl_file:Path,out:Path,as_of:date)->dict:
    if not out.is_dir() or out.is_symlink():raise ValueError("OUTPUT_DIRECTORY_NOT_READY")
    approved,ap=load_source(approved_file,APP)
    crl,cp=load_source(crl_file,CRL)
    benchmarks=json.loads(BENCH.read_text(encoding="utf-8"),object_pairs_hook=no_duplicates)
    result,rows=research_refresh(approved,crl,benchmarks,as_of)
    raw=(json.dumps(rows,sort_keys=True,indent=2)+"\n").encode()
    result["sourceProvenance"]={"approvedRegistry":ap,"selectedCrl":cp}
    result["candidateFileSha256"]=hashlib.sha256(raw).hexdigest()
    result["capturedUtc"]=datetime.now(timezone.utc).isoformat(timespec="seconds")
    files=(out/"r38_fda_source_candidates.json",out/"r38_fda_source_receipt.json")
    if any(f.exists() or f.is_symlink() for f in files):raise ValueError("IMMUTABLE_SOURCE_OVERWRITE")
    receipt=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    for path,body in zip(files,(raw,receipt)):
        with path.open("xb") as stream:stream.write(body)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved",type=Path,required=True)
    parser.add_argument("--crl",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--as-of",type=date.fromisoformat,required=True)
    args=parser.parse_args()
    result=write_snapshot(args.approved,args.crl,args.out,args.as_of)
    print(json.dumps({key:result[key] for key in (
        "status","asOf","researchCandidateRows","modelEligibleHistoricalCases",
        "approvalProbability","candidateFileSha256","sourceProvenance")},sort_keys=True))

if __name__=="__main__":main()
