#!/usr/bin/env python3
"""R49 source-byte change triage: NOT material scientific change or FDA prediction.

Reads Track A's append-only research history *reassessment* output. A fresh
source hash is a review trigger, not evidence that a clinical endpoint, safety
profile, sponsor statement, or regulatory outcome changed materially.
"""
from __future__ import annotations
import argparse, hashlib, json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

STATES={
 "INITIAL_REVIEW_REQUIRED","SOURCE_VERSION_CHANGED_REVIEW_REQUIRED",
 "SOURCE_AVAILABILITY_CHANGED_REVIEW_REQUIRED","SOURCE_VERSIONS_UNCHANGED"
}
KINDS=("primary","safety","documents")

def _evidence_sources(case):
    if case is None:
        return {},{}
    trials={}
    for item in case.get("sourceVersions",{}).get("trials",[]):
        nct=item.get("nct");versions=item.get("sourceVersions")
        if not isinstance(nct,str) or not nct.startswith("NCT") or not isinstance(versions,dict):
            raise ValueError("INVALID_ORIGINAL_TRIAL_SOURCE_VERSION")
        for kind in KINDS:
            sha=versions.get(kind)
            if sha is not None and (not isinstance(sha,str) or len(sha)!=64 or
                                    any(c not in "0123456789abcdef" for c in sha)):
                raise ValueError("INVALID_ORIGINAL_TRIAL_SOURCE_DIGEST")
            key="https://clinicaltrials.gov/study/"+nct+"#"+kind
            if key in trials:raise ValueError("DUPLICATE_ORIGINAL_TRIAL_SOURCE")
            trials[key]=sha
    app={}
    for src in case.get("applicationSourceReferences",[]):
        url=src.get("url"); sha=src.get("sha256")
        if (not isinstance(url,str) or urlsplit(url).scheme!="https" or
            not urlsplit(url).hostname or len(url)>2048 or
            sha is not None and (not isinstance(sha,str) or len(sha)!=64 or
                                 any(c not in "0123456789abcdef" for c in sha))):
            raise ValueError("INVALID_APPLICATION_ORIGINAL_SOURCE")
        if url in app:raise ValueError("DUPLICATE_APPLICATION_ORIGINAL_SOURCE")
        app[url]=(sha,src.get("retrievalStatus"))
    return trials,app

def summarize(reassess:dict,run_id:str)->dict:
    if (not isinstance(reassess,dict) or reassess.get("clinicalWrites")!=0 or
        reassess.get("predictionReleaseAuthorized") is not False or
        not isinstance(reassess.get("reassessment"),list) or
        len(reassess["reassessment"])!=23 or not run_id.isdigit()):
        raise ValueError("NOT_EXACT_23_APPLICATION_RESEARCH_REVIEW")
    changed=[]; registry_changes=[];source_changes=defaultdict(set);source_states={}
    changed_ids=set();research_ids=set()
    by_state=defaultdict(int)
    for item in reassess["reassessment"]:
        cid=item.get("applicationCycleId")
        if not isinstance(cid,str) or cid in research_ids:
            raise ValueError("DUPLICATE_OR_INVALID_APPLICATION_ID")
        research_ids.add(cid)
        state=item.get("state")
        if (state not in STATES or
            item.get("materialScientificChangeAdjudicated") is not False or
            item.get("authorizedGradesOrPredictionsModified") is not False or
            type(item.get("reassessmentRequired")) is not bool):
            raise ValueError("REASSESSMENT_CANNOT_RELEASE_CLINICAL_CONCLUSIONS")
        by_state[state]+=1
        before=item.get("priorResearchRecord");after=item.get("currentResearchRecord")
        if not isinstance(after,dict) or after.get("applicationCycleId")!=cid or (
             before is not None and (
               not isinstance(before,dict) or before.get("applicationCycleId")!=cid)):
            raise ValueError("ORIGINAL_APPLICATION_RESEARCH_MISMATCH")
        a,b=_evidence_sources(before),_evidence_sources(after)
        if item["reassessmentRequired"]:
            changed_ids.add(cid)
            # Brand-new cases require initial review, not "changed source" claims.
            if before is None:
                if state!="INITIAL_REVIEW_REQUIRED":raise ValueError("INITIAL_REVIEW_STATE_MISMATCH")
                changed.append(cid);continue
            if state not in ("SOURCE_VERSION_CHANGED_REVIEW_REQUIRED",
                            "SOURCE_AVAILABILITY_CHANGED_REVIEW_REQUIRED"):
                raise ValueError("MISSING_SOURCE_CHANGE_REVIEW_STATE")
        elif state not in ("SOURCE_VERSIONS_UNCHANGED","INITIAL_REVIEW_REQUIRED"):
            raise ValueError("INCONSISTENT_REASSESSMENT_STATE")
        app_new=b[1];app_old=a[1]
        for url in sorted(app_old.keys()|app_new.keys()):
            old_sha,old_status=app_old.get(url,(None,None))
            new_sha,new_status=app_new.get(url,(None,None))
            if old_sha==new_sha and old_status==new_status:continue
            key=(url,old_sha,new_sha,old_status,new_status)
            source_changes[key].add(cid)
            source_states[key]="CONTENT_HASH_CHANGED_REQUIRES_REVIEW" if (
                old_sha is not None and new_sha is not None and old_sha!=new_sha
            ) else "SOURCE_AVAILABILITY_OR_METADATA_CHANGED_REQUIRES_REVIEW"
        reg_old,reg_new=a[0],b[0]
        for url in sorted(reg_old.keys()|reg_new.keys()):
            old_sha,new_sha=reg_old.get(url),reg_new.get(url)
            if old_sha==new_sha:continue
            registry_changes.append({
              "applicationCycleId":cid,"source":url,
              "previousSha256":old_sha,"currentSha256":new_sha,
              "changeKind":"REGISTRY_RAW_BYTES_CHANGED_REQUIRES_REVIEW" if (
                old_sha is not None and new_sha is not None
              ) else "REGISTRY_SOURCE_ACCESS_CHANGED_REQUIRES_REVIEW"
            })
        if item["reassessmentRequired"]:changed.append(cid)
    if len(research_ids)!=23:
        raise ValueError("APPLICATION_COUNT_INCOMPLETE")
    application_source_rows=[
      {"sourceUrl":key[0],"previousSha256":key[1],"currentSha256":key[2],
       "previousStatus":key[3],"currentStatus":key[4],
       "affectedApplicationResearchIds":sorted(apps),
       "changeKind":source_states[key],
       "materialClinicalImpactVerified":False}
      for key,apps in sorted(source_changes.items(),key=lambda x:repr(x[0]))
    ]
    # Current registry bytes, if any, remain subject to original-readout clock.
    return {
      "schema":"MAIN_R49_RESEARCH_ORIGINAL_SOURCE_BYTE_CHANGE_TRIAGE",
      "runId":run_id,"checkedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "applicationResearchRecords":23,
      "applicationsFlaggedForSourceReview":len(changed_ids),
      "sourceReviewStates":dict(sorted(by_state.items())),
      "uniqueSponsorSecOrFdaSourceChanges":len(application_source_rows),
      "registryNctSourceChangeReferences":len(registry_changes),
      "applicationSourceChangeReferences":application_source_rows,
      "registrySourceChangeReferences":registry_changes,
      "applicationsWithAnySourceReassessment":sorted(changed_ids),
      "scientificallyAdjudicatedMaterialChanges":0,
      "independentScientificReviewerSignoffs":0,
      "newValidatedApplicationPredictions":0,
      "realHistoricalBacktests":0,
      "calibratedAccuracy":None,
      "sourceReviewOnly":True,
      "automaticMaterialClinicalChangeInference":False,
      "automaticPredictionOrGradeWriteAuthorized":False,
      "productionWriteAuthorized":False,
      "notice":"A SHA-256 difference means retrieved bytes differ. It is not proof of a changed trial outcome, material medical effect, FDA decision, or independently validated grade. A shared source may affect multiple application research groups."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reassessment",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--run-id",required=True)
    a=p.parse_args()
    if a.reassessment.is_symlink() or not a.reassessment.is_file() or a.reassessment.stat().st_size>35_000_000:
        raise ValueError("INVALID_IMMUTABLE_REASSESSMENT_INPUT")
    if a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir():
        raise ValueError("IMMUTABLE_REVIEW_OUTPUT_REQUIRED")
    report=summarize(json.loads(a.reassessment.read_bytes()),a.run_id)
    with a.output.open("x") as stream:json.dump(report,stream,sort_keys=True,indent=2);stream.write("\n")
    print(json.dumps({k:report[k] for k in (
      "applicationResearchRecords","applicationsFlaggedForSourceReview",
      "uniqueSponsorSecOrFdaSourceChanges","registryNctSourceChangeReferences",
      "scientificallyAdjudicatedMaterialChanges","newValidatedApplicationPredictions"
    )},sort_keys=True))

if __name__=="__main__":main()
