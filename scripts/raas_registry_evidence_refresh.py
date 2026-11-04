#!/usr/bin/env python3
"""Refresh the RAAS research cohort from the official ClinicalTrials.gov API.

Registry results are not issuer-public Phase 3 readout classification, clinical
benefit, PDUFA decisions, or scored/approved RAAS metrics. Preserve unavailable
NCTs as unknown, preserve previous source dates, and never backdate a capture.
"""
from __future__ import annotations
import datetime as dt
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"new-platform/frontend/data/raas-registry-evidence-census.json"
API="https://clinicaltrials.gov/api/v2/studies"
NCT=re.compile(r"^NCT\d{8}$")
BATCH_SIZE=40
MAX_RESPONSE_BYTES=15_000_000

def today_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def validate_manifest(manifest:dict)->list[dict]:
    if(manifest.get("schemaVersion")!=1 or manifest.get("scope")!="RAAS_REGISTRY_EVIDENCE_SOURCE_CENSUS" or not isinstance(manifest.get("records"),list)):
        raise ValueError("RAAS_REGISTRY_CENSUS_INVALID")
    rows=manifest["records"]
    if len(rows)!=762 or len({r.get("nctId") for r in rows})!=762 or any(
        not isinstance(r,dict) or not NCT.fullmatch(str(r.get("nctId",""))) or
        r.get("sourceUrl")!="https://clinicaltrials.gov/study/"+r["nctId"] or
        not r.get("ticker") for r in rows):
        raise ValueError("RAAS_REGISTRY_ROSTER_MISMATCH")
    return rows

def safe_date(value):
    if isinstance(value,dict):
        value=value.get("date")
    return value if isinstance(value,str) and re.fullmatch(r"20\d{2}-\d{2}-\d{2}",value) else None

def extract_study(study:dict, expected_nct:str, captured_at:str)->dict:
    if not isinstance(study,dict) or not NCT.fullmatch(expected_nct):
        raise ValueError("RAAS_REGISTRY_RESPONSE_INVALID")
    protocol=study.get("protocolSection")
    if not isinstance(protocol,dict):
        raise ValueError("RAAS_REGISTRY_MISSING_PROTOCOL")
    ident=protocol.get("identificationModule") or {}
    if ident.get("nctId")!=expected_nct:
        raise ValueError("RAAS_REGISTRY_CROSS_NCT_RESPONSE")
    status=protocol.get("statusModule") or {}
    design=protocol.get("designModule") or {}
    outcomes=protocol.get("outcomesModule") or {}
    sponsor=protocol.get("sponsorCollaboratorsModule") or {}
    primary=outcomes.get("primaryOutcomes") or []
    secondary=outcomes.get("secondaryOutcomes") or []
    if not isinstance(primary,list) or not isinstance(secondary,list):
        raise ValueError("RAAS_REGISTRY_OUTCOME_FORMAT_INVALID")
    has_results=study.get("hasResults")
    if not isinstance(has_results,bool):
        raise ValueError("RAAS_REGISTRY_RESULTS_FLAG_INVALID")
    result_measures=(study.get("resultsSection") or {}).get("outcomeMeasuresModule") or {}
    registered_measures=result_measures.get("outcomeMeasures") or []
    if not isinstance(registered_measures,list):
        raise ValueError("RAAS_REGISTRY_RESULTS_INVALID")
    analyses=sum(len(m.get("analyses") or []) for m in registered_measures if isinstance(m,dict))
    if not has_results and analyses:
        raise ValueError("RAAS_REGISTRY_RESULTS_CONTRADICTION")
    enrollment=design.get("enrollmentInfo") or {}
    sponsor_name=(sponsor.get("leadSponsor") or {}).get("name")
    return {
        "captureStatus":"LIVE_PRIMARY_REGISTRY_CAPTURE",
        "capturedAt":captured_at,
        "registryUpdatedAt":safe_date(status.get("lastUpdatePostDateStruct")),
        "registryStatus":status.get("overallStatus"),
        "hasPostedResults":has_results,
        "resultsFirstPosted":safe_date(status.get("resultsFirstPostDateStruct")),
        "primaryOutcomeCount":len(primary),
        "secondaryOutcomeCount":len(secondary),
        "analysisCount":analyses,
        "firstPrimaryEndpoint":(primary[0].get("measure") if primary and isinstance(primary[0],dict) else None),
        "documentsCount":len(((study.get("documentSection") or {}).get("largeDocumentModule") or {}).get("largeDocs") or []),
        "sponsor":sponsor_name,
        "participantCount":enrollment.get("count") if isinstance(enrollment.get("count"),int) else None,
        "startDate":safe_date(status.get("startDateStruct")),
        "primaryCompletionDate":safe_date(status.get("primaryCompletionDateStruct")),
        "studyCompletionDate":safe_date(status.get("completionDateStruct")),
        "issuerReadoutStage":None,
        "approvedRaasScore":None,
    }

def fetch_batch(ids:list[str])->list[dict]:
    if not ids or len(ids)>BATCH_SIZE or len(ids)!=len(set(ids)) or any(not NCT.fullmatch(v) for v in ids):
        raise ValueError("RAAS_REGISTRY_BATCH_INVALID")
    params=urllib.parse.urlencode({"filter.ids":",".join(ids),"pageSize":BATCH_SIZE,"format":"json"})
    url=API+"?"+params
    last=None
    for attempt in range(3):
        try:
            request=urllib.request.Request(url,headers={
                "Accept":"application/json","User-Agent":"PDUFA-RAAS-Research-Collector/1.0"
            })
            with urllib.request.urlopen(request,timeout=45) as response:
                raw=response.read(MAX_RESPONSE_BYTES+1)
            if len(raw)>MAX_RESPONSE_BYTES: raise ValueError("RAAS_REGISTRY_OVERSIZED_RESPONSE")
            result=json.loads(raw)
            if not isinstance(result,dict) or not isinstance(result.get("studies"),list) or result.get("nextPageToken"):
                raise ValueError("RAAS_REGISTRY_BATCH_RESPONSE_INVALID")
            return result["studies"]
        except (OSError,ValueError) as error:
            last=error
            if attempt<2:time.sleep(2*(attempt+1))
    raise RuntimeError("RAAS_REGISTRY_BATCH_UNAVAILABLE") from last

def refresh(manifest:dict, fetcher=fetch_batch, captured_at:str|None=None)->dict:
    rows=validate_manifest(manifest)
    recorded=captured_at or today_utc()
    by_nct={r["nctId"]:dict(r) for r in rows}
    failures=[];found=set();requests_ok=0
    # All 762 records, not merely the five staged pilot trials.
    for start in range(0,len(rows),BATCH_SIZE):
        wanted=[r["nctId"] for r in rows[start:start+BATCH_SIZE]]
        try:
            studies=fetcher(wanted)
            if not isinstance(studies,list):raise ValueError("RAAS_REGISTRY_BATCH_INVALID")
            batch={}
            for study in studies:
                identity=(((study or {}).get("protocolSection") or {}).get("identificationModule") or {}).get("nctId")
                if identity not in wanted or identity in batch:
                    raise ValueError("RAAS_REGISTRY_UNEXPECTED_OR_DUPLICATE_NCT")
                batch[identity]=extract_study(study,identity,recorded)
            requests_ok+=1
            for nct,updates in batch.items():
                previous=by_nct[nct]
                by_nct[nct]={**previous,**updates}
                found.add(nct)
            # A missing API entry cannot erase earlier dated evidence.
        except (ValueError,RuntimeError,OSError) as error:
            failures.extend(wanted)
            print("Source refresh unavailable for a batch of "+str(len(wanted))+" NCTs: "+str(error),file=sys.stderr)
    if requests_ok==0:
        raise RuntimeError("RAAS_REGISTRY_TOTAL_SOURCE_OUTAGE")
    final=[by_nct[r["nctId"]] for r in rows]
    counts={
        "total":len(final),
        "cachedRegistry":sum(x["captureStatus"] in ("CACHED_REGISTRY_CAPTURE","LIVE_PRIMARY_REGISTRY_CAPTURE") for x in final),
        "missingRegistry":sum(x["captureStatus"]=="REGISTRY_NOT_IN_CACHE" for x in final),
        "postedResults":sum(x.get("hasPostedResults") is True for x in final),
        "resultAnalyses":sum((x.get("analysisCount") or 0)>0 for x in final),
        "primaryOutcomeDefined":sum((x.get("primaryOutcomeCount") or 0)>0 for x in final),
        "livePrimaryRegistry":sum(x["captureStatus"]=="LIVE_PRIMARY_REGISTRY_CAPTURE" for x in final),
        "apiMatchedThisRun":len(found),
        "apiBatchesSucceeded":requests_ok,
        "apiBatchesFailed":(len(rows)+BATCH_SIZE-1)//BATCH_SIZE-requests_ok
    }
    return {**manifest,"sourceAsOf":recorded,"counts":counts,"records":final,
        "note":"Direct ClinicalTrials.gov API as-of evidence; source may contain registry posted results but does NOT confirm issuer-public Phase 3 readout, FDA application, PDUFA, medical benefit, or RAAS predictive scores. Incomplete and unavailable entries are not zero."}

def main():
    original=json.loads(MANIFEST.read_text(encoding="utf-8"))
    updated=refresh(original)
    MANIFEST.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    counts=updated["counts"]
    print("RAAS registry collection: "+str(counts["total"])+" source roster; "+
          str(counts["livePrimaryRegistry"])+" now with direct source captures; "+
          str(counts["missingRegistry"])+" missing from the combined cache; "+
          str(counts["postedResults"])+" posted registry results; "+
          str(counts["resultAnalyses"])+" with statistical analyses; 0 overall RAAS scores inferred.")

if __name__=="__main__":
    main()
