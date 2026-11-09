#!/usr/bin/env python3
"""MAIN R45: compare CURRENT registered vs CURRENT posted primary endpoint text.

This is source-consistency triage, not a locked-SAP check or proof of a
prespecified efficacy hierarchy. Current records may have changed after readout.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest,retrieve_url

NCT=re.compile(r"NCT[0-9]{8}\Z")

def norm(s):
    if not isinstance(s,str):return ""
    return "".join(ch for ch in s.casefold() if ch.isalnum())

def registered_and_posted(study:dict,nct:str,receipt:dict,cycles:list[str])->dict:
    if (not isinstance(study,dict) or not NCT.fullmatch(nct) or
        study.get("protocolSection",{}).get("identificationModule",{}).get("nctId")!=nct):
        raise ValueError("ORIGINAL_REGISTRY_IDENTITY_MISMATCH")
    if not isinstance(cycles,list) or not cycles:
        raise ValueError("MISSING_APPLICATION_CROSSWALK")
    p=study["protocolSection"]
    reg=(p.get("outcomesModule") or {}).get("primaryOutcomes") or []
    section=study.get("resultsSection")
    posted=(((section.get("outcomeMeasuresModule") or {}).get("outcomeMeasures")) or []
        if isinstance(section,dict) else [])
    if not isinstance(reg,list) or not isinstance(posted,list):
        raise ValueError("REGISTRY_OUTCOME_SHAPE_INVALID")
    reg=[x for x in reg if isinstance(x,dict)]
    posted=[x for x in posted if isinstance(x,dict) and x.get("type")=="PRIMARY"]
    available=list(range(len(reg)))
    comparisons=[]
    for x in posted:
        title=x.get("title")
        frame=x.get("timeFrame")
        exact=next((i for i in available if norm(title) and
            norm(reg[i].get("measure"))==norm(title) and
            norm(reg[i].get("timeFrame"))==norm(frame)),None)
        title_match=next((i for i in available if norm(title) and
            norm(reg[i].get("measure"))==norm(title)),None)
        idx=exact if exact is not None else title_match
        if idx is not None:available.remove(idx)
        comparisons.append({
          "postedTitle":title if isinstance(title,str) else None,
          "postedTimeFrame":frame if isinstance(frame,str) else None,
          "currentlyRegisteredTitle":reg[idx].get("measure") if idx is not None else None,
          "currentlyRegisteredTimeFrame":reg[idx].get("timeFrame") if idx is not None else None,
          "currentRecordTextComparison":(
             "EXACT_TITLE_AND_TIME_FRAME_IN_CURRENT_REGISTRY" if exact is not None else
             "TITLE_ONLY_TIME_FRAME_DIFFERENCE" if title_match is not None else
             "NO_TEXT_MATCH_IN_CURRENT_REGISTERED_PRIMARY"),
          "independentLockedSapMatch":False,
          "verifiedPriorVersionAndFreezeDate":False,
          "scientificEndpointPass":None})
    titles=sum(x["currentRecordTextComparison"]=="EXACT_TITLE_AND_TIME_FRAME_IN_CURRENT_REGISTRY"
               for x in comparisons)
    only_title=sum(x["currentRecordTextComparison"]=="TITLE_ONLY_TIME_FRAME_DIFFERENCE"
               for x in comparisons)
    unmatch=len(posted)-titles-only_title
    status="NO_POSTED_PRIMARY_IN_CURRENT_REGISTRY" if not posted else (
       "CURRENT_SNAPSHOT_TEXT_MATCH_ONLY" if titles==len(posted) else
       "CURRENT_SNAPSHOT_TEXT_DISCREPANCY_REQUIRES_REVIEW")
    return {
      "nct":nct,"applicationCycleIds":list(cycles),
      "currentRegistryUrl":"https://clinicaltrials.gov/study/"+nct,
      "sourceApiUrl":receipt.get("url"),
      "sourceResponseSha256":receipt.get("sha256"),
      "registeredPrimaryCountInCurrentVersion":len(reg),
      "postedPrimaryCountInCurrentVersion":len(posted),
      "exactCurrentTitleAndTimeFrameCount":titles,
      "titleOnlyTimeFrameDifferenceCount":only_title,
      "unmatchedPostedPrimaryCount":unmatch,
      "currentlyRegisteredWithoutExactPostedMatchCount":len(reg)-titles,
      "currentResultsSectionPresent":isinstance(section,dict),
      "sourceSnapshotStatus":status,
      "postedPrimaryTextComparisons":comparisons,
      "currentPrimaryTitles":[x.get("measure") for x in reg],
      "lastRegistryUpdatePostDate":(p.get("statusModule",{}).get("lastUpdatePostDateStruct") or {}).get("date"),
      "lockedSapVerified":False,
      "preReadoutRegistryVersionVerified":False,
      "originalMultiplicityHierarchyVerified":False,
      "scientificMethodGrade":None,
      "officialFdaForecast":"ABSTAIN"}
def run(manifest:dict,fetcher=retrieve_url,raw_dir:Path|None=None)->dict:
    if (manifest.get("trialCount")!=29 or manifest.get("applicationCount")!=23 or
       len(manifest.get("trialRows",[]))!=29 or len(manifest.get("applicationGroups",[]))!=23):
        raise ValueError("FOCUS_29_23_MANIFEST_REQUIRED")
    links={x["nct"]:[] for x in manifest["trialRows"]}
    if len(links)!=29:raise ValueError("NCT_DUPLICATES")
    for g in manifest["applicationGroups"]:
        for n in g["ncts"]:
            if n not in links:raise ValueError("APPLICATION_NCT_MISMATCH")
            links[n].append(g["cycleId"])
    if any(not x for x in links.values()):raise ValueError("APPLICATION_LINKS_MISSING")
    if raw_dir is not None and (not raw_dir.is_dir() or raw_dir.is_symlink()):
        raise ValueError("IMMUTABLE_ARCHIVE_DIR_REQUIRED")
    def get(row):
        n=row["nct"];obs,raw=fetcher(row["registryUrl"])
        if obs.get("status")!="FETCHED" or raw is None:
            return n,{"nct":n,"applicationCycleIds":links[n],
                "sourceSnapshotStatus":"SOURCE_UNAVAILABLE",
                "scientificMethodGrade":None,"officialFdaForecast":"ABSTAIN"},None
        if hashlib.sha256(raw).hexdigest()!=obs.get("sha256"):
            raise ValueError("ORIGINAL_SOURCE_BYTES_SHA256_MISMATCH")
        try: rec=registered_and_posted(json.loads(raw),n,obs,links[n])
        except (ValueError,KeyError,TypeError):
            return n,{"nct":n,"applicationCycleIds":links[n],
                "sourceSnapshotStatus":"UNVERIFIED_REGISTRY_SHAPE_OR_IDENTITY",
                "scientificMethodGrade":None,"officialFdaForecast":"ABSTAIN"},None
        return n,rec,raw
    found={}
    with ThreadPoolExecutor(max_workers=5) as pool:
        for fut in as_completed([pool.submit(get,row) for row in manifest["trialRows"]]):
            n,rec,raw=fut.result()
            found[n]=rec
            if raw is not None and raw_dir is not None:
                with (raw_dir/(n+".json")).open("xb") as f:f.write(raw)
    records=[found[row["nct"]] for row in manifest["trialRows"]]
    if len(records)!=29 or len({r["nct"] for r in records})!=29:
        raise ValueError("ROSTER_INTEGRITY_FAILURE")
    return {
      "schema":"MAIN_R45_CURRENT_REGISTRY_PRIMARY_TEXT_RECONCILIATION",
      "rosterAsOf":manifest["asOf"],
      "capturedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "nctCount":29,"applicationCount":23,
      "sourceFetched":sum(r.get("sourceResponseSha256") is not None for r in records),
      "trialsWithResults":sum(r.get("currentResultsSectionPresent") is True for r in records),
      "currentRegisteredPrimaryCount":sum(r.get("registeredPrimaryCountInCurrentVersion",0) for r in records),
      "postedPrimaryCount":sum(r.get("postedPrimaryCountInCurrentVersion",0) for r in records),
      "currentExactTitleTimeFrameCount":sum(r.get("exactCurrentTitleAndTimeFrameCount",0) for r in records),
      "titleOnlyTimeFrameDifferences":sum(r.get("titleOnlyTimeFrameDifferenceCount",0) for r in records),
      "unmatchedPostedPrimary":sum(r.get("unmatchedPostedPrimaryCount",0) for r in records),
      "records":records,
      "qualifiedClinicalSignoffs":0,"scientificGrades":0,
      "independentlyValidatedFdaForecasts":0,
      "historicalIndependentBacktests":0,
      "calibratedAccuracy":None,"numericalFdaProbability":None,
      "officialFutureOutcome":"ABSTAIN","officialFutureReviewTiming":"ABSTAIN",
      "modelTrainingAuthorized":False,"productionOrReviewerWrites":False,
      "caution":"A match in the CURRENT registry is NOT a locked SAP, originally prespecified endpoint, multiplicity control, clinically meaningful effect, or FDA efficacy validation. Absence of posted registry results does not mean absent published Phase 3 data."}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--raw-dir",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        raise ValueError("IMMUTABLE_OUTPUT_REQUIRED")
    m=build_manifest(_read_json(ROSTER),_read_json(APPS))
    result=run(m,raw_dir=args.raw_dir)
    with args.output.open("xb") as f:f.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
    print(json.dumps({k:v for k,v in result.items() if k in (
      "nctCount","applicationCount","sourceFetched","trialsWithResults",
      "currentRegisteredPrimaryCount","postedPrimaryCount","currentExactTitleTimeFrameCount",
      "titleOnlyTimeFrameDifferences","unmatchedPostedPrimary","independentlyValidatedFdaForecasts")}),flush=True)
if __name__=="__main__":main()
