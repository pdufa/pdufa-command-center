#!/usr/bin/env python3
"""MAIN R44: exact-NCT original registry safety research, never clinical verdicts."""
from __future__ import annotations
import argparse, hashlib, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from scripts.refresh_focus_public_sources_r40 import ROSTER, APPS, _read_json, build_manifest, retrieve_url

def rows(v, maximum=50000):
    return v[:maximum] if isinstance(v, list) else []

def reported(v, limit=450):
    if v is None: return None
    if isinstance(v, (str,int,float)) and not isinstance(v,bool):
        return (str(v).strip() or None)[:limit]
    return None

def extract(study:dict, nct:str, receipt:dict, application_ids:list[str])->dict:
    if not isinstance(study,dict) or study.get("protocolSection",{}).get(
            "identificationModule",{}).get("nctId")!=nct:
        raise ValueError("ORIGINAL_REGISTRY_IDENTITY_MISMATCH")
    if not isinstance(application_ids,list) or not application_ids:
        raise ValueError("MISSING_APPLICATION_CROSSWALK")
    sec=study.get("resultsSection")
    has_results=isinstance(sec,dict)
    ae=sec.get("adverseEventsModule") if has_results else None
    has_ae=isinstance(ae,dict)
    ae=ae if has_ae else {}
    status=study["protocolSection"].get("statusModule") or {}
    groups=[]
    for item in rows(ae.get("eventGroups"),300):
        if not isinstance(item,dict): continue
        group={"id":reported(item.get("id"),90),
               "title":reported(item.get("title"),250),
               "description":reported(item.get("description"),450)}
        for key in ("deathsNumAffected","deathsNumAtRisk",
                    "seriousNumAffected","seriousNumAtRisk",
                    "otherNumAffected","otherNumAtRisk"):
            group[key+"AsReported"]=reported(item.get(key),90)
        groups.append(group)
    allowed={g["id"] for g in groups}
    def events(field):
        output=[]
        for item in rows(ae.get(field)):
            if not isinstance(item,dict):continue
            stats=[]
            for row in rows(item.get("stats"),300):
                if not isinstance(row,dict):continue
                gid=reported(row.get("groupId"),90)
                if gid not in allowed:
                    raise ValueError("EVENT_GROUP_MISMATCH")
                stats.append({"groupId":gid,
                    "numAffectedAsReported":reported(row.get("numAffected"),90),
                    "numAtRiskAsReported":reported(row.get("numAtRisk"),90),
                    "numEventsAsReported":reported(row.get("numEvents"),90)})
            output.append({"term":reported(item.get("term"),350),
              "organSystem":reported(item.get("organSystem"),200),
              "assessmentType":reported(item.get("assessmentType"),120),
              "stats":stats})
        return output
    serious=events("seriousEvents")
    other=events("otherEvents")
    result={
        "nct":nct,"applicationCycleIds":list(application_ids),
        "sourceUrl":"https://clinicaltrials.gov/study/"+nct,
        "sourceApiUrl":receipt.get("url"),"sourceResponseSha256":receipt.get("sha256"),
        "sourceResponseBytes":receipt.get("bytes"),
        "currentRegistryResultsSectionPresent":has_results,
        "currentRegistryAdverseEventsModulePresent":has_ae,
        "postedResultsDateAsReported":reported((status.get("resultsFirstPostDateStruct") or {}).get("date"),40),
        "lastPostedUpdateAsReported":reported((status.get("lastUpdatePostDateStruct") or {}).get("date"),40),
        "timeFrameAsReported":reported(ae.get("timeFrame"),550),
        "descriptionAsReported":reported(ae.get("description"),700),
        "frequencyThresholdAsReported":reported(ae.get("frequencyThreshold"),90),
        "eventGroups":groups,
        "seriousEventTerms":serious,
        "otherEventTerms":other,
        "seriousEventTermCount":len(serious),
        "otherEventTermCount":len(other),
        "eventGroupCount":len(groups),
        "extractStatus":("POSTED_ADVERSE_EVENT_MODULE_EXTRACTED" if has_ae else
            "RESULTS_SECTION_NO_ADVERSE_EVENT_MODULE" if has_results else
            "NO_CURRENT_REGISTRY_RESULTS_SECTION"),
        "fatalEventsAndSeriousAEsAreNotIdentical":True,
        "allArmStatsAreSourceReportedNotPooled":True,
        "originalAsPublishedClockVerified":False,
        "independentlyAdjudicatedSafety":False,
        "authorizedScientificGrade":None,
        "officialFdaApprovalCrlPrediction":"ABSTAIN",
        "reviewDelayPrediction":"ABSTAIN",
        "caution":"Registry event groups can overlap or reflect crossover arms; no pooled trial risk percentages or causal interpretation. Source does not replace full CSR/ISS, final SAP, FDA CMC and clinical review."}
    if has_ae and (any(x["id"] is None for x in groups) or len(allowed)!=len(groups)):
        raise ValueError("INVALID_OR_DUPLICATE_EVENT_GROUPS")
    return result

def run(manifest:dict,fetcher=retrieve_url,raw_dir:Path|None=None)->dict:
    if (manifest.get("trialCount")!=29 or manifest.get("applicationCount")!=23 or
        len(manifest.get("trialRows",[]))!=29 or len(manifest.get("applicationGroups",[]))!=23):
        raise ValueError("FOCUS_29_23_MANIFEST_REQUIRED")
    by_nct={x["nct"]:[] for x in manifest["trialRows"]}
    for g in manifest["applicationGroups"]:
        for n in g["ncts"]:
            if n not in by_nct: raise ValueError("APPLICATION_NCT_MISMATCH")
            by_nct[n].append(g["cycleId"])
    if any(not ids for ids in by_nct.values()):raise ValueError("APPLICATION_CROSSWALK_INCOMPLETE")
    if raw_dir is not None and (not raw_dir.is_dir() or raw_dir.is_symlink()):
        raise ValueError("ARCHIVE_DIR_NOT_READY")
    def one(t):
        n=t["nct"]
        obs,body=fetcher(t["registryUrl"])
        if obs.get("status")!="FETCHED" or body is None:
            return n,{"nct":n,"applicationCycleIds":by_nct[n],
                "extractStatus":"SOURCE_NOT_FETCHED","sourceStatus":obs.get("status"),
                "authorizedScientificGrade":None,"officialFdaApprovalCrlPrediction":"ABSTAIN"},None
        if hashlib.sha256(body).hexdigest()!=obs.get("sha256"):
            raise ValueError("ORIGINAL_SOURCE_BYTES_SHA256_MISMATCH")
        try: result=extract(json.loads(body),n,obs,by_nct[n])
        except (ValueError,KeyError,TypeError):
            result={"nct":n,"applicationCycleIds":by_nct[n],
                "extractStatus":"INVALID_OR_MISMATCHED_ORIGINAL",
                "authorizedScientificGrade":None,"officialFdaApprovalCrlPrediction":"ABSTAIN"}
            body=None
        return n,result,body
    found={}
    with ThreadPoolExecutor(max_workers=5) as pool:
        for future in as_completed([pool.submit(one,t) for t in manifest["trialRows"]]):
            n,record,body=future.result()
            found[n]=record
            if body is not None and raw_dir is not None:
                with (raw_dir/(n+".json")).open("xb") as out:out.write(body)
    ordered=[found[t["nct"]] for t in manifest["trialRows"]]
    if len(ordered)!=29 or len({r["nct"] for r in ordered})!=29:
        raise ValueError("INCOMPLETE_FOCUS_ROSTER")
    return {"schema":"MAIN_R44_EXACT_NCT_POSTED_SAFETY_SOURCE_V1",
      "rosterSnapshotAsOf":manifest["asOf"],
      "capturedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "nctCount":29,"provisionalApplicationCount":23,
      "registryFetched":sum(x.get("sourceResponseSha256") is not None for x in ordered),
      "trialsWithRegistryResultsSection":sum(x.get("currentRegistryResultsSectionPresent") is True for x in ordered),
      "trialsWithPostedAeModule":sum(x.get("currentRegistryAdverseEventsModulePresent") is True for x in ordered),
      "seriousEventTermRows":sum(x.get("seriousEventTermCount",0) for x in ordered),
      "otherEventTermRows":sum(x.get("otherEventTermCount",0) for x in ordered),
      "eventGroupRows":sum(x.get("eventGroupCount",0) for x in ordered),
      "records":ordered,
      "independentClinicalGrades":0,"validatedApplicationPredictions":0,
      "realHistoricalBacktests":0,"calibratedAccuracy":None,"numericalFdaProbability":None,
      "officialFutureFdaOutcomeForecast":"ABSTAIN","officialFutureDelayForecast":"ABSTAIN",
      "trainingAuthorized":False,"productionOrScientificLedgerWrites":False,
      "caution":"Present registry AE data are source-reported groups/terms, not adjudicated complete safety or pooled event rates. Absent registry results are not evidence of absent sponsor or journal safety results."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--raw-dir",required=True,type=Path)
    args=p.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        raise ValueError("IMMUTABLE_OUTPUT_FILE_REQUIRED")
    m=build_manifest(_read_json(ROSTER),_read_json(APPS))
    report=run(m,raw_dir=args.raw_dir)
    with args.output.open("xb") as out:
        out.write((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
    keys=["nctCount","provisionalApplicationCount","registryFetched",
          "trialsWithRegistryResultsSection","trialsWithPostedAeModule",
          "seriousEventTermRows","otherEventTermRows","eventGroupRows",
          "independentClinicalGrades","validatedApplicationPredictions",
          "realHistoricalBacktests"]
    print(json.dumps({k:report[k] for k in keys},sort_keys=True),flush=True)

if __name__=="__main__":main()
