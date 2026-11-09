#!/usr/bin/env python3
"""R52 read-only first-version primary endpoint probe for priority 3 FOCUS NCTs.

The ClinicalTrials.gov documented v2 endpoint returns CURRENT records.
For research only, ctrdata's published source points to the nonpublic-contract
/api/int/studies/<NCT>?history=true and /history/<version> routes. Probe without
relying on their stability, retain exact bytes, fail closed on structural drift,
and NEVER claim these are date-verified locked pre-unblinding SAPs.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from datetime import datetime,timezone,date
from pathlib import Path
from scripts.refresh_focus_public_sources_r40 import (
    ROSTER,APPS,_read_json,build_manifest,retrieve_url
)
NCTS=("NCT04544293","NCT05126758","NCT05208047")
HOST="https://www.clinicaltrials.gov"
CURRENT="https://clinicaltrials.gov"
MAX_BYTES=8_000_000

def meta(raw:bytes,nct:str,expected_version:int|None=None):
    try:obj=json.loads(raw)
    except (TypeError,ValueError):raise ValueError("HISTORICAL_REGISTRY_JSON_INVALID")
    if not isinstance(obj,dict):raise ValueError("INVALID_HISTORICAL_REGISTRY_RECORD")
    if expected_version is not None:
        if obj.get("studyVersion")!=expected_version or not isinstance(obj.get("study"),dict):
            raise ValueError("HISTORICAL_REGISTRY_VERSION_OR_BODY_MISMATCH")
        study=obj["study"]
    else:study=obj
    if (study.get("protocolSection",{}).get("identificationModule",{}).get("nctId")!=nct):
        raise ValueError("ORIGINAL_HISTORICAL_NCT_IDENTITY_MISMATCH")
    module=(study["protocolSection"].get("outcomesModule") or {})
    declared=module.get("primaryOutcomes") or []
    if not isinstance(declared,list) or len(declared)>100:
        raise ValueError("HISTORICAL_PRIMARY_OUTCOME_SCHEMA_MISMATCH")
    entries=[]
    for item in declared:
        if not isinstance(item,dict):
            raise ValueError("MALFORMED_HISTORICAL_PRIMARY_OUTCOME")
        outcome={key:item.get(key) for key in ("measure","timeFrame","description")}
        if any(value is not None and (not isinstance(value,str) or len(value)>8000)
               for value in outcome.values()):
            raise ValueError("UNTRUSTED_HISTORICAL_OUTCOME_TEXT")
        entries.append(outcome)
    return entries

def history_changes(raw:bytes):
    try:payload=json.loads(raw)
    except (TypeError,ValueError):raise ValueError("HISTORY_INDEX_JSON_INVALID")
    if not isinstance(payload,dict) or not isinstance(payload.get("history"),dict):
        raise ValueError("HISTORY_INDEX_WRAPPER_NOT_VERIFIED")
    changes=payload["history"].get("changes")
    if not isinstance(changes,list) or not 1<=len(changes)<=1000:
        raise ValueError("HISTORY_INDEX_CHANGES_NOT_VERIFIED")
    out=[]
    for v in changes:
        if not isinstance(v,dict) or not isinstance(v.get("version"),int) or type(v["version"]) is bool:
            raise ValueError("HISTORY_INDEX_VERSION_MALFORMED")
        version=v["version"]
        if not 0<=version<=3000:raise ValueError("HISTORY_VERSION_OUT_OF_BOUNDS")
        posted=v.get("date")
        if not isinstance(posted,str) or not re.fullmatch(r"20\d\d-\d\d-\d\d",posted):
            raise ValueError("HISTORY_POST_DATE_MALFORMED")
        try:date.fromisoformat(posted)
        except ValueError:raise ValueError("HISTORY_POST_DATE_INVALID")
        out.append({"version":version,"registryHistoryDateAsReported":posted})
    if len({v["version"] for v in out})!=len(out):
        raise ValueError("HISTORY_INDEX_DUPLICATE_VERSION")
    return sorted(out,key=lambda x:x["version"])

def safe_get(url,fetcher):
    receipt,body=fetcher(url)
    status=receipt.get("status")
    if status!="FETCHED":
        return {"status":status or "UNKNOWN_REGISTRY_FETCH_STATUS","sourceUrl":url},None
    if not isinstance(body,bytes) or not 0<len(body)<=MAX_BYTES:
        raise ValueError("REGISTRY_FETCHED_SOURCE_BODY_NOT_ARCHIVED_OR_TOO_LARGE")
    if receipt.get("sha256")!=hashlib.sha256(body).hexdigest() or receipt.get("bytes")!=len(body):
        raise ValueError("REGISTRY_HISTORY_ORIGINAL_BYTES_SHA_INVALID")
    if receipt.get("contentType")!="application/json":
        raise ValueError("UNEXPECTED_REGISTRY_HISTORY_CONTENT_TYPE")
    return {
      "status":"FETCHED","sourceUrl":url,
      "sourceSha256":receipt["sha256"],"sourceBytes":len(body),
      "contentType":"application/json"
    },body

def run(fetcher,raw_dir:Path)->dict:
    if not raw_dir.is_dir() or raw_dir.is_symlink() or any(raw_dir.iterdir()):
        raise ValueError("NEW_EMPTY_IMMUTABLE_ORIGINAL_ARCHIVE_REQUIRED")
    m=build_manifest(_read_json(ROSTER),_read_json(APPS))
    all_ncts={x["nct"] for x in m["trialRows"]}
    if m["trialCount"]!=29 or m["applicationCount"]!=23 or not set(NCTS).issubset(all_ncts):
        raise ValueError("PRIORITY_TRIALS_NOT_IN_ORIGINAL_29_23")
    def archive(nct,tag,payload):
        filepath=raw_dir/(nct+"-"+tag+".json")
        if not re.fullmatch(r"[a-z0-9-]+",tag):
            raise ValueError("UNSAFE_ARCHIVE_LABEL")
        with filepath.open("xb") as f:f.write(payload)
        return filepath.name
    results=[]
    for nct in NCTS:
        history_url=f"{HOST}/api/int/studies/{nct}?history=true"
        overview,overview_bytes=safe_get(history_url,fetcher)
        row={"nct":nct,"currentNctUrl":"https://clinicaltrials.gov/study/"+nct,
             "historyIndex":overview,"historicalVersionsCount":None,
             "firstVersionInfo":None,"firstVersionPrimaryOutcomes":None,
             "currentRegisteredPrimaryOutcomes":None,
             "firstVsCurrentPrimaryWordingExactMatch":None,
             "earliestHistoryDateFromRegistry":None,
             "originalPublicPriorToReadoutIndependentlyVerified":False,
             "preUnblindingLockedSapVerified":False,
             "qualifiedHistoricalFDAForecastInput":False,
             "scientificGrade":None,"officialFdaForecast":"ABSTAIN"}
        if overview_bytes is not None:
            overview["archiveFile"]=archive(nct,"history-index",overview_bytes)
            try:versions=history_changes(overview_bytes)
            except ValueError as exc:
                row["historyIndex"]["structureStatus"]=str(exc)
                results.append(row)
                continue
            row["historicalVersionsCount"]=len(versions)
            first=versions[0]
            row["earliestHistoryDateFromRegistry"]=first["registryHistoryDateAsReported"]
            version_url=f"{HOST}/api/int/studies/{nct}/history/{first['version']}"
            first_rec,first_raw=safe_get(version_url,fetcher)
            row["firstVersionInfo"]={**first_rec,"registryVersionAsReported":first["version"],
                                      "registryHistoryDateAsReported":first["registryHistoryDateAsReported"]}
            if first_raw is not None:
                row["firstVersionInfo"]["archiveFile"]=archive(nct,"first-record",first_raw)
                try:row["firstVersionPrimaryOutcomes"]=meta(first_raw,nct,first["version"])
                except ValueError as exc:row["firstVersionInfo"]["structureStatus"]=str(exc)
        current_url=f"{CURRENT}/api/v2/studies/{nct}?format=json"
        current_rec,current_raw=safe_get(current_url,fetcher)
        row["currentVersionInfo"]=current_rec
        if current_raw is not None:
            current_rec["archiveFile"]=archive(nct,"current-record",current_raw)
            try:row["currentRegisteredPrimaryOutcomes"]=meta(current_raw,nct)
            except ValueError as exc:row["currentVersionInfo"]["structureStatus"]=str(exc)
        if row["firstVersionPrimaryOutcomes"] is not None and row["currentRegisteredPrimaryOutcomes"] is not None:
            row["firstVsCurrentPrimaryWordingExactMatch"]=(
                row["firstVersionPrimaryOutcomes"]==row["currentRegisteredPrimaryOutcomes"]
            )
        results.append(row)
    return {
      "schema":"MAIN_R52_PRIORITY_3_ORIGINAL_REGISTRY_HISTORICAL_VERSION_PROBE",
      "observedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "canonicalNctRosterCount":29,"applicationCycleCount":23,
      "priorityTrialCount":3,"priorityTrials":results,
      "historyIndexesRetrieved":sum(x["historyIndex"]["status"]=="FETCHED" for x in results),
      "originalFirstVersionTextRecovered":sum(x["firstVersionPrimaryOutcomes"] is not None for x in results),
      "oldAndCurrentOutcomesCompared":sum(x["firstVsCurrentPrimaryWordingExactMatch"] is not None for x in results),
      "originalPreReadoutEndpointHierarchyVerified":0,"originalLockedStatisticalAnalysisPlansVerified":0,
      "applicationFdaOutcomePredictionsValidated":0,"independentHistoricalBacktests":0,
      "calibratedAccuracy":None,"modelTrainingAuthorized":False,
      "productionOrClinicalLedgerWrites":False,"officialFdaForecast":"ABSTAIN",
      "caution":"Undocumented internal API endpoints may change. A registry history date and first version text alone do not verify first-public availability before trial readout, signed locked SAP/multiplicity, clinical efficacy, regulatory CMC, or FDA approvability."
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir",type=Path,required=True)
    a=parser.parse_args()
    if not a.out_dir.is_dir() or a.out_dir.is_symlink() or any(a.out_dir.iterdir()):
        raise ValueError("EMPTY_ARCHIVE_DIRECTORY_REQUIRED")
    result=run(lambda url:retrieve_url(url,timeout=16,preserve_body=True),a.out_dir)
    with (a.out_dir/"research_history_probe.json").open("xb") as f:
        f.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
    print(json.dumps({k:result[k] for k in (
       "priorityTrialCount","historyIndexesRetrieved","originalFirstVersionTextRecovered",
       "oldAndCurrentOutcomesCompared","originalPreReadoutEndpointHierarchyVerified",
       "applicationFdaOutcomePredictionsValidated")},sort_keys=True),flush=True)

if __name__=="__main__":main()
