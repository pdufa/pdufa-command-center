#!/usr/bin/env python3
"""One-study, public ClinicalTrials.gov record and history receipt. No secrets and no writes to app data."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
import urllib.request
import urllib.error
import datetime

NCT = "NCT06081894"
ROOT = "https://clinicaltrials.gov"
OUT = Path("acacia-clinicaltrials-gov-sap-audit")
URLS = {
    "current": f"{ROOT}/api/v2/studies/{NCT}",
    "version_index": f"{ROOT}/api/int/studies/{NCT}/history",
}

def get_document(url):
    req=urllib.request.Request(url,headers={
        "Accept":"application/json",
        "User-Agent":"PDUFA-MAIN-Research-Source-Verification/1.0 (one public trial; no credentials)",
    })
    with urllib.request.urlopen(req,timeout=24) as resp:
        final=urlsplit(resp.url)
        if final.scheme!="https" or final.hostname!="clinicaltrials.gov" or final.username or final.password:
            raise ValueError("NOT_OFFICIAL_CT_GOV_HOST")
        buf=resp.read(3_000_001)
        if len(buf)>3_000_000: raise ValueError("SOURCE_TOO_LARGE")
        if "json" not in resp.headers.get("content-type",""):raise ValueError("NOT_JSON_RESPONSE")
    return json.loads(buf),hashlib.sha256(buf).hexdigest()

def main():
    OUT.mkdir(exist_ok=True)
    receipt={
        "schema":"MAIN_ACACIA_OFFICIAL_PUBLIC_CTG_SAP_HISTORY_CHECK_V1",
        "nct":NCT,"sourceURLs":URLS,
        "recordedDate":"2026-11-08",
        "mode":"SOURCE_DISCOVERY_ONLY_NOT_MEDICAL_REVIEW",
        "finalSapCaptured":False,"independentPhaseVerified":False,
        "gradesWritten":0,"prediction":"ABSTAIN",
        "resultsInformationPosted":"UNKNOWN",
        "registryEndpoints":{},
    }
    try:
        current,sha=get_document(URLS["current"])
        pm=current.get("protocolSection",{})
        idm=pm.get("identificationModule",{})
        if idm.get("nctId")!=NCT: raise ValueError("EXACT_NCT_MISMATCH")
        out=pm.get("outcomesModule",{})
        result=current.get("resultsSection",None)
        fm=current.get("documentSection",{})
        if not isinstance(fm,dict):fm={}
        docs=fm.get("largeDocumentModule",{}).get("largeDocs",[]) if isinstance(fm.get("largeDocumentModule"),dict) else []
        if not isinstance(docs,list):docs=[]
        primary=out.get("primaryOutcomes",[]) if isinstance(out.get("primaryOutcomes"),list) else []
        receipt["registryEndpoints"]["current"]={"status":"VALID_EXACT_NCT",
            "sha256":sha,
            "overallStatus":pm.get("statusModule",{}).get("overallStatus","UNKNOWN"),
            "updated":pm.get("statusModule",{}).get("studyFirstPostDateStruct",{}),
            "lastUpdatePosted":pm.get("statusModule",{}).get("studyFirstPostDateStruct",{}), # replaced below when possible
            "primaryOutcomeTitles":[v.get("measure","")[:240] for v in primary if isinstance(v,dict)][:16],
            "primaryOutcomeCount":len(primary),
            "documentTitles":[{"type":v.get("type"),"filename":str(v.get("filename") or v.get("fileName") or "")[:150]} for v in docs if isinstance(v,dict)][:40],
            "largeDocumentRecords":len(docs),
            "resultsSectionPresent":isinstance(result,dict),
            "hasResultsField":current.get("hasResults"),
        }
        receipt["registryEndpoints"]["current"]["lastUpdatePosted"]=pm.get("statusModule",{}).get("studyFirstPostDateStruct",{})
        v=pm.get("statusModule",{}).get("lastUpdatePostDateStruct")
        if v:receipt["registryEndpoints"]["current"]["lastUpdatePosted"]=v
        receipt["resultsInformationPosted"] = "YES" if isinstance(result,dict) else "NOT_IN_PUBLIC_API_AS_OF_CHECK"
        receipt["publicSAPDocumentListed"]=any("statistical" in str(v).lower() or "sap" in str(v).lower() for v in docs)
        print("CTG_PUBLIC current: NCT validated; resultSection="+str(receipt["resultsInformationPosted"])+
              ", largeDocumentRecords="+str(len(docs))+", SAP-listed="+str(receipt["publicSAPDocumentListed"]))
    except (ValueError, KeyError, urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
            json.JSONDecodeError) as exc:
        receipt["registryEndpoints"]["current"]={"status":"UNAVAILABLE_OR_UNVERIFIED","errorClass":type(exc).__name__}
        print("CTG_PUBLIC current unavailable: "+type(exc).__name__)
    try:
        history,sha=get_document(URLS["version_index"])
        if not isinstance(history,(dict,list)):raise ValueError("BAD_HISTORY_FORMAT")
        receipt["registryEndpoints"]["version_index"]={
            "status":"PUBLIC_HISTORY_METADATA_RETRIEVED",
            "sha256":sha,"shape":type(history).__name__,
            "historicalPrimaryOutcomeTextVerified":False,
        }
        entries=history.get("changes",[]) if isinstance(history,dict) else history
        if not isinstance(entries,list):entries=[]
        receipt["registryEndpoints"]["version_index"]["entryCount"]=len(entries)
        safe=[]
        for v in entries[:150]:
            if not isinstance(v,dict):continue
            m=v.get("moduleLabels",[])
            if not isinstance(m,list):m=[]
            safe.append({"date":str(v.get("date",""))[:50],
                         "status":str(v.get("status",""))[:50],
                         "modules":[str(x)[:80] for x in m][:25]})
        receipt["registryEndpoints"]["version_index"]["entries"]=safe
        print("CTG_PUBLIC history metadata found: "+str(len(safe))+
              "; earlier outcome text NOT recovered from module-change metadata")
    except (ValueError,KeyError,urllib.error.HTTPError,urllib.error.URLError,TimeoutError,json.JSONDecodeError) as exc:
        receipt["registryEndpoints"]["version_index"]={"status":"UNAVAILABLE","errorClass":type(exc).__name__}
        print("CTG_PUBLIC historical version index unavailable: "+type(exc).__name__)
    receipt["sourceCheckComplete"]=True
    (OUT/"source_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("CTG_PUBLIC receipts written. No clinical phase or grades changed.")

if __name__=="__main__":
    main()
