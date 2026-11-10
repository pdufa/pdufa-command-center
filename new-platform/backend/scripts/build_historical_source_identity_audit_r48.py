#!/usr/bin/env python3
"""MAIN R48: identify repeated FDA source applications and build a cycle-review queue.

Inputs are selected published approval and CRL source ACTIONS, not a consecutive
NDA/BLA filing denominator. Grouping by parent application is an audit for
possible duplicate/serial review cycles, NOT cycle adjudication. The two output
files both remain outcome-selected research and MUST NEVER feed a forecaster.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from collections import defaultdict
from datetime import date,datetime,timezone
from pathlib import Path
from scripts.build_historical_source_checkpoint_r47 import verify as verify_r47

APP=re.compile(r"(?:BLA|NDA)[0-9]{6}\Z")
SHA=re.compile(r"[a-f0-9]{64}\Z")
ACTIONS={"AP","TA","COMPLETE RESPONSE"}
RESEARCH_CLASSES={
 "AP_SOURCE_REGISTRY","TA_NONBINARY_SOURCE_REGISTRY",
 "CRL_PARENT_APPLICATION_ONLY","CRL_LEGACY_OR_UNRESOLVED_IDENTIFIER",
 "CRL_MULTIPLE_OR_MISSING_IDENTIFIERS","CRL_SUPPLEMENT_NOT_ORIGINAL",
 "CRL_EXPLICIT_ORIGINAL"
}

def validate_action(row,at_date):
    if not isinstance(row,dict):
        raise ValueError("MALFORMED_ORIGINAL_ACTION_RECORD")
    label=row.get("sourceAction")
    if label not in ACTIONS or row.get("researchClass") not in RESEARCH_CLASSES:
        raise ValueError("UNCLASSIFIED_ORIGINAL_FDA_ACTION")
    digest=row.get("sourceRecordSha256")
    if not isinstance(digest,str) or not SHA.fullmatch(digest):
        raise ValueError("FDA_ACTION_SOURCE_DIGEST_REQUIRED")
    raw=row.get("reportedActionDate")
    try: when=date.fromisoformat(raw)
    except (TypeError,ValueError):raise ValueError("MALFORMED_REPORTED_FDA_ACTION_DATE")
    if when>at_date:raise ValueError("FDA_ACTION_DATE_AFTER_SOURCE_CAPTURE")
    ident=row.get("applicationId")
    if ident is not None and (not isinstance(ident,str) or not APP.fullmatch(ident)):
        raise ValueError("AMBIGUOUS_PARENT_APPLICATION_IDENTIFIER")
    original=row.get("sourceOriginalSubmissionNo") or row.get("sourceOriginalOrSupplementUnit")
    if original is not None and (not isinstance(original,str) or not
                                  re.fullmatch(r"[A-Za-z0-9-]{1,30}",original)):
        raise ValueError("INVALID_REPORTED_SUBMISSION_UNIT")
    references=row.get("sourceApplicationReferences",[])
    if not isinstance(references,list) or len(references)>12 or any(
      not isinstance(x,str) or not x.strip() or len(x)>150 for x in references):
        raise ValueError("INVALID_PUBLIC_ACTION_REFERENCES")
    return {
      "reportedActionDate":when.isoformat(),"sourceAction":label,
      "researchClass":row["researchClass"],"sourceRecordSha256":digest,
      "reportedOriginalOrSupplementUnit":original,
      "sourceApplicationReferences":sorted(references)
    }

def triage(rows: list,receipt:dict,raw:bytes,as_of:str):
    verify_r47(rows,receipt,raw,as_of)
    if not rows:raise ValueError("EMPTY_FDA_SOURCE_COHORT")
    at_date=date.fromisoformat(as_of[:10])
    groups=defaultdict(list)
    seen=set()
    for row in rows:
        rec=validate_action(row,at_date)
        key=json.dumps(row,sort_keys=True,separators=(",",":"))
        if key in seen:raise ValueError("DUPLICATED_ORIGINAL_SOURCE_ACTION_CANDIDATE")
        seen.add(key)
        app=row.get("applicationId")
        # A null/legacy parent ID stays distinct; never guessed from references.
        group_id=app if app is not None else "UNRESOLVED_SOURCE_"+rec["sourceRecordSha256"]
        groups[group_id].append(rec)
    if sum(map(len,groups.values()))!=len(rows):
        raise ValueError("FDA_SOURCE_GROUPING_CARDINALITY_CHANGED")
    audits=[]
    neutral=[]
    multi=0;mixed=0;multi_crl=0;collisions=0
    for gid,items in sorted(groups.items()):
        items=sorted(items,key=lambda x:(x["reportedActionDate"],x["sourceAction"],
            x["reportedOriginalOrSupplementUnit"] or "",x["sourceRecordSha256"]))
        kinds={x["sourceAction"] for x in items}
        reported_dates={x["reportedActionDate"] for x in items}
        is_known=bool(APP.fullmatch(gid))
        simultaneous=len(reported_dates)<len(items)
        conflicting="AP" in kinds and "COMPLETE RESPONSE" in kinds
        repeated=len(items)>1
        multi+=int(is_known and repeated)
        mixed+=int(is_known and conflicting)
        multi_crl+=int(is_known and sum(x["sourceAction"]=="COMPLETE RESPONSE" for x in items)>1)
        collisions+=int(is_known and simultaneous)
        flags=[]
        if not is_known:flags.append("NO_RESOLVED_STANDARD_NDA_BLA_PARENT_IDENTIFIER")
        if repeated:flags.append("MULTIPLE_PUBLIC_ACTION_SOURCE_RECORDS_SAME_PARENT_NOT_INDEPENDENT_CYCLES")
        if conflicting:flags.append("MIXED_PUBLIC_ACTION_TYPES_NEEDS_ORIGINAL_CYCLE_RECONCILIATION")
        if simultaneous:flags.append("SAME_DAY_MULTIPLE_SOURCE_ACTIONS_OR_SUBMISSIONS")
        if any(x["reportedOriginalOrSupplementUnit"] is None for x in items):
            flags.append("ORIGINAL_OR_SUPPLEMENT_UNIT_NOT_FULLY_AVAILABLE")
        flags.extend([
           "CONSECUTIVE_FILING_DENOMINATOR_NOT_VERIFIED",
           "INDEPENDENT_FDA_CYCLE_AND_REVIEW_DATE_NOT_VERIFIED",
           "BEFORE_ACTION_PIVOTAL_EVIDENCE_NOT_VERIFIED"
        ])
        audits.append({
          "parentApplicationResearchId":gid,"parentIdStandardFormat":is_known,
          "sourceRowCount":len(items),
          "observedPublishedActionSourceRecords":items,
          "observedActionsSpanMultipleReportedDates":len(reported_dates)>1,
          "multipleOriginalUnitsOrSameDayActions":simultaneous,
          "mixedPublishedActionTypes":conflicting,
          "independentlyVerifiedDecisionCycles":0,"researchUseOnly":True,
          "modelEligible":False,"sourceAuditFlags":flags
        })
        # This is a *source-outcome-selected* identity worklist, NOT a blind forecast
        # case. Deliberately exclude the action source dates, labels and results.
        neutral.append({
          "parentApplicationResearchId":gid,"parentIdStandardFormat":is_known,
          "originalFilingAndClinicalProgramCrosswalk":"NOT_VERIFIED",
          "supportingNctIds":[],
          "firstPublicPivotalReadout":"NOT_VERIFIED",
          "originalAsPublishedSourceVersion":"NOT_VERIFIED",
          "independentRegulatorReviewCycle":"NOT_VERIFIED",
          "requiredInvestigation":sorted(set(flags)),
          "outcomeBlindForecastInputEligible":False,
          "sourceSelectedByObservedFdaAction":True,
          "officialFdaForecast":"ABSTAIN",
          "trainingAuthorized":False
        })
    full_sha=hashlib.sha256(raw).hexdigest()
    shared={
      "asOfUtc":as_of,"originalFdaCandidateSha256":full_sha,
      "sourceActionRecords":len(rows),
      "sourceSelectedAndSurvivorshipBiased":True,
      "completeConsecutiveNdaBlaFilingCohort":False,
      "independentApplicationReviewCyclesVerified":0,
      "independentRetrospectiveBacktests":0,
      "modelTrainingAuthorized":False,"measuredAccuracy":None,
      "calibratedProbability":None,"officialForecast":"ABSTAIN",
      "automaticClinicalScoringAllowed":False,
      "productionMutationAuthorized":False
    }
    audit={
      **shared,
      "schema":"MAIN_R48_SELECTED_FDA_SOURCE_PARENT_ACTION_AUDIT",
      "standardParentApplicationIds":sum(a["parentIdStandardFormat"] for a in audits),
      "unresolvedSourceIdentityGroups":sum(not a["parentIdStandardFormat"] for a in audits),
      "sourceIdentityGroups":len(audits),
      "knownParentGroupsWithMultipleSourceRows":multi,
      "knownParentGroupsWithMixedApprovalAndCrlSourceTypes":mixed,
      "knownParentGroupsWithMultipleCrlRows":multi_crl,
      "knownParentGroupsWithSameDayMultipleSourceRows":collisions,
      "records":audits,
      "warning":"Postdecision original FDA source action descriptions are NOT independent application/review cycles. No FDA prediction, measured accuracy, or completed original cohort is implied."
    }
    predecision={
      **shared,
      "schema":"MAIN_R48_OUTCOME_SELECTED_NONFORECAST_IDENTITY_WORKLIST",
      "sourceIdentityGroups":len(neutral),
      "records":neutral,
      "outcomeVaultAccessControlEstablished":False,
      "futureForecasterMayConsumeThisWorklist":False,
      "warning":"Although action types and dates are excluded from each row, the source population was selected from observed postdecision FDA actions. This is NOT blinded, consecutive or model-eligible."
    }
    return audit,predecision

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidates",type=Path,required=True)
    p.add_argument("--receipt",type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True)
    args=p.parse_args()
    if not args.out_dir.is_dir() or args.out_dir.is_symlink():
        raise ValueError("WRITE_ONCE_RESULT_DIRECTORY_REQUIRED")
    for path in (args.candidates,args.receipt):
        if not path.is_file() or path.is_symlink() or path.stat().st_size>85_000_000:
            raise ValueError("SOURCE_CANDIDATES_NOT_SAFE")
    raw=args.candidates.read_bytes()
    audit,review=triage(json.loads(raw),json.loads(args.receipt.read_bytes()),raw,
       datetime.now(timezone.utc).isoformat(timespec="seconds"))
    outputs=[
     (args.out_dir/"postdecision_fda_source_identity_audit.json",audit),
     (args.out_dir/"source_selected_identity_research_worklist_NOT_MODEL_INPUT.json",review)
    ]
    if any(path.exists() or path.is_symlink() for path,_ in outputs):
        raise ValueError("IMMUTABLE_SOURCE_IDENTITY_REPORT_OVERWRITE")
    for path,report in outputs:
        with path.open("xb") as f:
            f.write((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
    print(json.dumps({k:audit[k] for k in (
       "sourceActionRecords","sourceIdentityGroups","standardParentApplicationIds",
       "unresolvedSourceIdentityGroups","knownParentGroupsWithMultipleSourceRows",
       "knownParentGroupsWithMixedApprovalAndCrlSourceTypes",
       "knownParentGroupsWithSameDayMultipleSourceRows",
       "independentApplicationReviewCyclesVerified","independentRetrospectiveBacktests"
    )},sort_keys=True),flush=True)

if __name__=="__main__":main()
