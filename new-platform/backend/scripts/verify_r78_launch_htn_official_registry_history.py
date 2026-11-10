#!/usr/bin/env python3
"""MAIN R78: official ClinicalTrials.gov historical protocol record provenance.

Research receipt ONLY. No source record implies database-lock, signatures,
unblinding, pre-outcome SAP authority, FDA outcome or approval probability.
No third-party unofficial history service and no private research API keys.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, re, urllib.error, urllib.parse, urllib.request
from pathlib import Path

NCT="NCT06153693"
HOSTS={"clinicaltrials.gov","www.clinicaltrials.gov"}
LATEST="https://clinicaltrials.gov/api/v2/studies/"+NCT
HISTORY=("https://clinicaltrials.gov/api/int/studies/"+NCT+"?history=true",
         "https://clinicaltrials.gov/api/int/studies/"+NCT+"/history")
VERSION_BASE="https://clinicaltrials.gov/api/int/studies/"+NCT+"/history/"
MAX_BYTES=5_000_000
RECEIPT_SCHEMA="MAIN_R78_ORIGINAL_NCT_LAUNCH_HTN_AS_OF_HISTORY_RESEARCH_NOT_SAP_LOCK"
PRE_COMPLETION_CUTOFF="2025-01-24"
SAP_SIGNING_CUTOFF="2025-02-13"

def fail(message):
    raise ValueError("R78_"+message)

def fetch_json(url,timeout=18):
    allowed={LATEST,*HISTORY}
    if re.fullmatch(r"0|[1-9][0-9]{0,2}",url.removeprefix(VERSION_BASE)) and url.startswith(VERSION_BASE):
        allowed.add(url)
    if url not in allowed:fail("URL_NOT_ALLOWLISTED")
    req=urllib.request.Request(url,headers={
        "Accept":"application/json",
        "User-Agent":"PDUFA-Command-Center-Research/1.0 (official registry history only)"
    })
    with urllib.request.urlopen(req,timeout=timeout) as response:
        final=urllib.parse.urlsplit(response.geturl())
        if final.scheme!="https" or final.hostname not in HOSTS or final.port is not None:
            fail("REGISTRY_REDIRECT_OUTSIDE_OFFICIAL_HOST")
        if int(response.headers.get("Content-Length") or 0)>MAX_BYTES:
            fail("OFFICIAL_REGISTRY_RESPONSE_TOO_BIG")
        raw=response.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:fail("OFFICIAL_REGISTRY_RESPONSE_TOO_BIG")
    if not raw.lstrip().startswith(b"{"):fail("OFFICIAL_REGISTRY_RESPONSE_NOT_JSON")
    return json.loads(raw)

def module(doc):
    if not isinstance(doc,dict):fail("HISTORY_VERSION_NOT_OBJECT")
    if isinstance(doc.get("study"),dict):doc=doc["study"]
    ps=doc.get("protocolSection")
    if not isinstance(ps,dict):fail("PROTOCOL_SECTION_NOT_PRESENT")
    idv=ps.get("identificationModule",{}).get("nctId")
    if idv!=NCT:fail("CROSS_TRIAL_IDENTITY")
    return ps

def status_publication(ps):
    data=ps.get("statusModule",{})
    return {k:data.get(k) for k in ("studyFirstPostDateStruct","lastUpdatePostDateStruct",
      "primaryCompletionDateStruct","completionDateStruct","resultsFirstPostDateStruct")}

def study_outcomes(ps):
    om=ps.get("outcomesModule",{})
    primary=om.get("primaryOutcomes",[])
    secondary=om.get("secondaryOutcomes",[])
    if not isinstance(primary,list) or not isinstance(secondary,list):fail("UNEXPECTED_OUTCOME_FORMAT")
    def clean(items):
        results=[]
        for item in items:
            if not isinstance(item,dict) or not isinstance(item.get("measure"),str):
                fail("OUTCOME_WITHOUT_MEASURE")
            # Preserve an observed original measure, not a source-altered claim of locking.
            results.append({"measure":item["measure"][:450],
                           "timeFrame":str(item.get("timeFrame",""))[:200]})
        return results[:40]
    return {"primary":clean(primary),"secondary":clean(secondary)}

def parsed_history(data):
    if not isinstance(data,dict):fail("HISTORY_OVERVIEW_NOT_OBJECT")
    history=data.get("history",data)
    if not isinstance(history,dict):fail("HISTORY_STRUCTURE_INVALID")
    changes=history.get("changes",[])
    if not isinstance(changes,list):fail("HISTORY_CHANGES_NOT_LIST")
    out=[]
    seen=set()
    for x in changes:
        if not isinstance(x,dict):fail("HISTORY_CHANGE_NOT_OBJECT")
        v=x.get("version");date=str(x.get("date",""))[:10]
        if type(v) is not int or not 0<=v<=999 or not re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}",date):
            fail("HISTORY_CHANGE_MISSING_NUMBER_OR_DATE")
        if v in seen:fail("DUPLICATE_HISTORY_VERSION")
        seen.add(v)
        out.append({"version":v,"publicChangeDate":date,
            "modifiedModuleLabels":x.get("moduleLabels",[]) if isinstance(x.get("moduleLabels",[]),list) else [],
            "changeStatus":str(x.get("status",""))[:50]})
    return sorted(out,key=lambda x:x["version"])

def run(get=fetch_json):
    data={"schema":RECEIPT_SCHEMA,"asOfUtc":dt.datetime.now(dt.timezone.utc).isoformat(),
       "nct":NCT,"officialCurrentSource":LATEST,"officialHistoryIndexSources":list(HISTORY),
       "historyDatesListed":0,"earliestOfficialHistoryDate":None,
       "registryVersionsAccessible":0,"earliestPreCompletionVersion":None,
       "lastVersionAtOrBeforeCompletion":None,"lastVersionAtOrBeforeSapSignature":None,
       "originalRegisteredPrimaryOutcomeChangedBySapSignature":None,
       "sourceErrors":[],"versions":[],"historyVersionIndex":[],
       "originalSignedSapAuthenticityConfirmed":False,
       "databaseLockDateAuthenticated":False,"firstTreatmentUnblindingAuthenticated":False,
       "preUnblindingOriginalPlanLockProven":False,
       "qualifiedIndependentScienceSignatures":0,
       "independentlyValidatedFDAForecasts":0,"FDAOutcome":"ABSTAIN","futureFDATiming":"UNKNOWN",
       "noProductionOrModelTrainingWrites":True}
    current=None
    try:
        current=get(LATEST);ps=module(current)
        data["currentRecord"]={"recordStatus":ps.get("statusModule",{}).get("overallStatus"),
           "sourceDates":status_publication(ps),
           "reportedPrimaryOutcomes":study_outcomes(ps)["primary"],
           "notHistoricalPrespecificationProof":True}
    except Exception as err:
        data["sourceErrors"].append("CURRENT_STUDY_NOT_RETRIEVABLE_OR_WRONG_NCT")
    overview=None
    for url in HISTORY:
        try:
            candidate=get(url)
            changes=parsed_history(candidate)
            if changes:
                overview=(candidate,changes)
                break
        except Exception:
            continue
    if overview is None:
        data["sourceErrors"].append("OFFICIAL_HISTORY_INDEX_NOT_AVAILABLE")
        data["state"]="REGISTRY_HISTORY_UNVERIFIED"
        return data
    _,changes=overview
    data["historyVersionIndex"]=changes[:100]
    data["historyDatesListed"]=len(changes)
    data["earliestOfficialHistoryDate"]=min(x["publicChangeDate"] for x in changes)
    before_completion=[x for x in changes if x["publicChangeDate"]<=PRE_COMPLETION_CUTOFF]
    before_sap=[x for x in changes if x["publicChangeDate"]<=SAP_SIGNING_CUTOFF]
    chosen=[changes[0]]
    if before_completion:chosen.append(before_completion[-1])
    if before_sap:chosen.append(before_sap[-1])
    for choice in sorted({x["version"]:x for x in chosen}.values(),key=lambda x:x["version"]):
        try:
            versionDoc=get(VERSION_BASE+str(choice["version"]))
            ps=module(versionDoc)
            record={"version":choice["version"],"versionHistoryDate":choice["publicChangeDate"],
                "sourceDates":status_publication(ps),"registeredOutcomes":study_outcomes(ps),
                "observedVersionRecordSha256":hashlib.sha256(json.dumps(versionDoc,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
                "sourceUri":VERSION_BASE+str(choice["version"]),
                "beforeCompletion":choice["publicChangeDate"]<=PRE_COMPLETION_CUTOFF,
                "beforeMainSapSignature":choice["publicChangeDate"]<=SAP_SIGNING_CUTOFF,
                "notProofOfSponsorOriginalSAPLock":True}
            data["versions"].append(record)
        except Exception:
            data["sourceErrors"].append("REGISTRY_VERSION_"+str(choice["version"])+"_NOT_RETRIEVABLE")
    data["registryVersionsAccessible"]=len(data["versions"])
    if data["versions"]:
        data["earliestPreCompletionVersion"]=next((x["version"] for x in data["versions"] if x["beforeCompletion"]),None)
        data["lastVersionAtOrBeforeCompletion"]=before_completion[-1]["version"] if before_completion else None
        data["lastVersionAtOrBeforeSapSignature"]=before_sap[-1]["version"] if before_sap else None
        originals=[x for x in data["versions"] if x["version"]==changes[0]["version"]]
        lasts=[x for x in data["versions"] if x["version"]==data["lastVersionAtOrBeforeSapSignature"]]
        if originals and lasts:
            data["originalRegisteredPrimaryOutcomeChangedBySapSignature"]=(originals[0]["registeredOutcomes"]["primary"]!=lasts[0]["registeredOutcomes"]["primary"])
    data["state"]="OFFICIAL_HISTORICAL_REGISTRY_VERSIONS_READ_RESEARCH_ONLY" if data["versions"] else "HISTORY_INDEX_ONLY"
    return data

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);args=p.parse_args()
    report=run()
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"nct":NCT,"state":report["state"],
      "historicalIndexVersions":report["historyDatesListed"],
      "historicalFullRecordsRead":report["registryVersionsAccessible"],
      "versionIds":[x["version"] for x in report["versions"]],
      "changedPrimaryAsOfSapDate":report["originalRegisteredPrimaryOutcomeChangedBySapSignature"],
      "errors":report["sourceErrors"],
      "authenticatedOriginalSapLock":False,"FDAOutcome":"ABSTAIN"},sort_keys=True))
if __name__=="__main__":main()
