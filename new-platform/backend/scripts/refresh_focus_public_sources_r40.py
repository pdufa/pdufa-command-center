#!/usr/bin/env python3
"""MAIN Rev40: read-only public FDA-application-source and 29 NCT registry audit.

Rechecks accessibility and cryptographic *retrieval* receipts, not clinical truth.
No automatic FDA efficacy/CMC judgement, historical grade or model release.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import hashlib,ipaddress,json,re,sys
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler

ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"app/data/focus_snapshot.json"
APPS=ROOT/"app/data/focus_application_snapshot.json"
NCT=re.compile(r"NCT[0-9]{8}\Z")
MAX_BYTES=5_000_000
MAX_EXTERNAL_DOCUMENT_BYTES=50_000_000
ALTERNATE_APPLICATION_SOURCES={
  # Exact original 2026-08-11 ACHV 10-Q from official SEC filing index.
  # Keep issuer redirect and alternative evidence as distinct receipts.
  "achv-cytisinicline":"https://www.sec.gov/Archives/edgar/data/949858/000119312526344624/achv-20260630.htm"
}

# Strictly known public hosts used by *this snapshot*; never fetch arbitrary
# user-supplied URLs or internal/service endpoints, even after a redirect.
ALLOWED_HOSTS=frozenset({
 "clinicaltrials.gov","www.clinicaltrials.gov","www.sec.gov",
 "abivax.gcs-web.com","ir.achievelifesciences.com",
 "ir.apnimed.com","www.axsome.com","www.capricor.com",
 "ir.capricor.com","investors.belitebio.com","belitebio.gcs-web.com",
 "investors.cogentbio.com","investorrelations.sarepta.com",
 "celldex.gcs-web.com","ir.corcept.com","www.corcept.com",
 "ir.cytokinetics.com","investors.immunome.com",
 "ir.moonlaketx.com","ir.mineralystx.com",
 "ir.pharvaris.com","ir.praxismedicines.com",
 "investors.savarapharma.com","investors.urogen.com",
 "veratherapeutics.gcs-web.com","zenasbio.gcs-web.com",
})
SUPPORTED_TYPES=("text/html","text/plain","application/json","application/pdf","application/xhtml+xml")
def _valid_url(url:str)->bool:
    if not isinstance(url,str) or len(url)>2048 or any(x.isspace() for x in url):
        return False
    try:
        o=urlsplit(url)
        if o.scheme!="https" or o.username is not None or o.password is not None or o.port not in (None,443) or o.fragment:
            return False
        h=(o.hostname or "").lower().rstrip(".")
        if not h or h not in ALLOWED_HOSTS or not o.path.strip("/"):
            return False
        try: ipaddress.ip_address(h);return False
        except ValueError: pass
        return True
    except ValueError:
        return False

class SafeRedirect(HTTPRedirectHandler):
    def __init__(self):self.depth=0
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        self.depth+=1
        if self.depth>3 or not _valid_url(newurl):
            raise HTTPError(req.full_url,code,"PUBLIC_SOURCE_REDIRECT_NOT_ALLOWED",headers,fp)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def _read_json(path:Path)->dict:
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,dict):raise ValueError("INVALID_SNAPSHOT_OBJECT")
    return obj

def build_manifest(roster:dict,application:dict)->dict:
    if (roster.get("asOf")!="2026-11-08" or
        application.get("asOf")!="2026-11-07" or
        not isinstance(roster.get("records"),list) or len(roster["records"])!=29 or
        not isinstance(application.get("records"),list) or len(application["records"])!=29 or
        application.get("sourceVerifiedByFda") is not False or
        application.get("clinicalSignoff") is not False):
        raise ValueError("FOCUS_ROSTER_SNAPSHOT_OR_CERTIFICATION_CHANGED")
    ids=[x.get("nct") for x in roster["records"]]
    if len(set(ids))!=29 or any(not isinstance(n,str) or not NCT.fullmatch(n) for n in ids):
        raise ValueError("FOCUS_INVALID_OR_DUPLICATE_NCT")
    by_id={x["nct"]:x for x in roster["records"]}
    app_ids=set()
    groups={}
    for row in application["records"]:
        nct=row.get("nct")
        if nct not in by_id or nct in app_ids:
            raise ValueError("MISSING_OR_DUPLICATED_FOCUS_APPLICATION_CROSSWALK")
        app_ids.add(nct)
        candidates=row.get("candidateApplications")
        if not isinstance(candidates,list) or not candidates:
            raise ValueError("EMPTY_APPLICATION_CYCLE_FOR_TRIAL")
        for c in candidates:
            cid=c.get("cycleId")
            if not isinstance(cid,str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+",cid):
                raise ValueError("INVALID_CYCLE_ID")
            if c.get("ticker")!=by_id[nct]["ticker"] or c.get("sourceDate","")>"2026-11-09" or not _valid_url(c.get("sourceUrl")):
                raise ValueError("UNTRUSTED_APPLICATION_SOURCE_OR_IDENTITY")
            if c.get("stage") not in (
                "PLANNED","PRIOR_CRL_RESUBMISSION_PLANNED","SUBMITTED_PENDING_ACCEPTANCE",
                "UNDER_REVIEW","SUPPLEMENT_UNDER_REVIEW","APPROVED_ALREADY"):
                raise ValueError("UNKNOWN_APPLICATION_STAGE")
            key={k:c.get(k) for k in ("cycleId","ticker","drug","indication","applicationType","stage","reportedGoal","sourceDate","sourceUrl")}
            if cid not in groups:
                groups[cid]={**key,"ncts":[]}
            elif any(groups[cid].get(k)!=v for k,v in key.items()):
                raise ValueError("CONFLICTING_APPLICATION_CYCLE_DETAILS")
            groups[cid]["ncts"].append(nct)
    if app_ids!=set(ids) or len(groups)!=23:
        raise ValueError("FOCUS_GROUP_COUNTS_NOT_29_23")
    ordered=[groups[k] for k in sorted(groups)]
    return {
        "schema":"MAIN_FOCUS_29_23_SOURCE_MANIFEST_R40",
        "asOf":"2026-11-09",
        "sourceRosters":{"focus":"2026-11-08","applications":"2026-11-07"},
        "trialRows":[{"nct":x["nct"],"ticker":x["ticker"],
             "registryUrl":"https://clinicaltrials.gov/api/v2/studies/"+x["nct"]+"?format=json",
             "recordedReadoutDate":x.get("recordedReleaseDate"),
             "reportedPdufaDate":x.get("recordedPdufaDate")} for x in roster["records"]],
        "applicationGroups":ordered,
        "trialCount":29,"applicationCount":23,
        "qualifiedScientificReviews":0,
        "validatedFdaForecasts":0,
        "modelTrainingAuthorized":False,
    }

def retrieve_url(url:str,*,timeout:int=15)->tuple[dict,bytes|None]:
    if not _valid_url(url):
        return {"status":"UNSAFE_URL_REJECTED","url":url},None
    opener=build_opener(SafeRedirect())
    req=Request(url,headers={"Accept":"text/html,application/json,application/pdf,*/*;q=0.5",
                  "User-Agent":"PDUFA-FOCUS-public-source-audit/1.0"})
    try:
        with opener.open(req,timeout=timeout) as reply:
            content_type=reply.headers.get("Content-Type","").split(";")[0].lower().strip()
            if content_type not in SUPPORTED_TYPES:
                return {"status":"UNSUPPORTED_CONTENT_TYPE","url":url,"contentType":content_type},None
            is_registry="/api/v2/studies/" in url
            limit=MAX_BYTES if is_registry else MAX_EXTERNAL_DOCUMENT_BYTES
            digest=hashlib.sha256()
            consumed=0
            body=[] if is_registry else None
            while True:
                part=reply.read(65536)
                if not part:break
                consumed+=len(part)
                if consumed>limit:
                    return {"status":"SOURCE_OVER_SIZE_LIMIT","url":url,
                         "contentType":content_type,"byteLimit":limit},None
                digest.update(part)
                if body is not None:body.append(part)
            final=reply.geturl()
            if not _valid_url(final):
                return {"status":"UNSAFE_REDIRECT_REJECTED","url":url},None
            return {"status":"FETCHED","url":url,"resolvedUrl":final,
                    "contentType":content_type,"bytes":consumed,
                    "sha256":digest.hexdigest(),
                    "sourceBodyPreserved":False},b"".join(body) if body is not None else None
    except HTTPError as exc:
        return {"status":"HTTP_UNAVAILABLE","url":url,"httpStatus":exc.code},None
    except (OSError,URLError,TimeoutError,ValueError) as exc:
        return {"status":"FETCH_BLOCKED","url":url,"errorClass":type(exc).__name__},None

def _registry_read(nct:str,obs:dict,body:bytes|None)->dict:
    fields={"registryPhase":None,"registryStatus":None,"lastPostedUpdate":None,
        "registryResultsPresent":False,"registryIdentityMatches":False}
    if obs.get("status")!="FETCHED" or body is None:
        return {**obs,"nct":nct,**fields,"scientificPhaseIndependentlyVerified":False}
    try:
        v=json.loads(body)
        p=v["protocolSection"]
        ident=p["identificationModule"]["nctId"]
        if ident!=nct:
            return {**obs,"status":"REGISTRY_IDENTITY_MISMATCH","nct":nct,
                    **fields,"scientificPhaseIndependentlyVerified":False}
        s=p.get("statusModule",{})
        d=p.get("designModule",{})
        fields.update(registryPhase=d.get("phases",[]),
            registryStatus=s.get("overallStatus"),
            lastPostedUpdate=s.get("lastUpdatePostDateStruct",{}).get("date"),
            registryResultsPresent=isinstance(v.get("resultsSection"),dict),
            registryIdentityMatches=True)
    except (ValueError,KeyError,TypeError):
        return {**obs,"status":"UNPARSEABLE_OFFICIAL_REGISTRY","nct":nct,
                **fields,"scientificPhaseIndependentlyVerified":False}
    return {**obs,"nct":nct,**fields,"scientificPhaseIndependentlyVerified":False}

def perform_capture(manifest:dict,fetcher=retrieve_url)->dict:
    groups=manifest["applicationGroups"];trials=manifest["trialRows"]
    sources={g["sourceUrl"] for g in groups}
    fallback={k:v for k,v in ALTERNATE_APPLICATION_SOURCES.items()
              if any(g["cycleId"]==k for g in groups)}
    if any(not _valid_url(url) for url in fallback.values()):
        raise ValueError("UNSAFE_ALTERNATIVE_FDA_SOURCE")
    all_sources=sources|set(fallback.values())
    registry={t["registryUrl"]:t["nct"] for t in trials}
    jobs=sorted(all_sources|set(registry))
    observations={}
    def one(url):
        obs,body=fetcher(url)
        if url in registry:
            return url,_registry_read(registry[url],obs,body)
        return url,{**obs,"sourceDocumentDateIndependentlyVerified":False,
            "originalAsPublishedVersionIndependentlyVerified":False,
            "regulatoryStatusIndependentlyConfirmed":False,
            "scientificConclusionsIndependentlyAdjudicated":False}
    with ThreadPoolExecutor(max_workers=7) as pool:
        for fut in as_completed([pool.submit(one,url) for url in jobs]):
            url,record=fut.result()
            observations[url]=record
    app_out=[{
       "cycleId":g["cycleId"],"ticker":g["ticker"],
       "ncts":g["ncts"],"reportedStage":g["stage"],
       "reportedGoal":g["reportedGoal"],
       "sourceDateFromSnapshot":g["sourceDate"],
       "applicationSource":observations[g["sourceUrl"]],
       "alternateOfficialSecSource":observations[fallback[g["cycleId"]]]
         if g["cycleId"] in fallback else None,
       "atLeastOneApplicationSourceFetched":
         observations[g["sourceUrl"]]["status"]=="FETCHED" or
         (g["cycleId"] in fallback and
          observations[fallback[g["cycleId"]]]["status"]=="FETCHED"),
       "supportingNctRegistryReceipts":[{
           "nct":n,"status":observations["https://clinicaltrials.gov/api/v2/studies/"+n+"?format=json"]["status"]
       } for n in g["ncts"]],
       "independentlyVerifiedClinicalEvidence":False,
       "qualifiedReviewerSignoff":False,
       "formalFdaActionPrediction":"ABSTAIN" if g["stage"]!="APPROVED_ALREADY" else "NOT_APPLICABLE_ALREADY_OBSERVED",
       "formalReviewDelayPrediction":"ABSTAIN" if g["stage"]!="APPROVED_ALREADY" else "NOT_APPLICABLE_ALREADY_OBSERVED",
       "originalRegulatorReviewCycleVerified":False
    } for g in groups]
    trial_out=[observations[t["registryUrl"]] for t in trials]
    fetched_sources=sum(r["status"]=="FETCHED" for r in observations.values() if r["url"] in all_sources)
    fetched_trials=sum(r["status"]=="FETCHED" for r in trial_out)
    app_groups_fetched=sum(a["atLeastOneApplicationSourceFetched"] for a in app_out)
    return {"schema":"MAIN_FOCUS_PUBLIC_SOURCE_RECAPTURE_R40",
        "status":"PUBLIC_LINK_BYTES_RECOVERED_RESEARCH_ONLY_NO_CLINICAL_SIGNOFF",
        "asOf":manifest["asOf"],
        "capturedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trialRoster":29,"provisionalApplicationGroups":23,
        "canonicalApplicationSourceUrls":len(sources),
        "additionalOfficialSecSourceUrls":len(fallback),
        "uniqueApplicationSourceUrls":len(all_sources),
        "applicationSourceUrlsFetched":fetched_sources,
        "applicationGroupsWithAvailablePublicSource":app_groups_fetched,
        "clinicalTrialsGovRecordsFetched":fetched_trials,
        "clinicalTrialsGovRecordsAttempted":29,
        "originalPublicSourceVersionsIndependentlyAuthenticated":0,
        "qualifiedClinicalReviews":0,"scientificMethodGradesWritten":0,
        "independentlyValidatedApplicationForecasts":0,
        "historicalBacktests":0,
        "calibratedAccuracy":None,"numericalApprovalProbability":None,
        "modelTrainingAuthorized":False,
        "applicationGroups":app_out,"trialSources":trial_out,
        "limitations":"HTTP bytes and registry identity prove only retrieval and record matching, not historic as-published source timing, FDA application identity, CMC adequacy, efficacy, safety or independent clinical adjudication",
        "noClinicalOrProductionWrites":True
    }

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    manifest=build_manifest(_read_json(ROSTER),_read_json(APPS))
    result=perform_capture(manifest)
    if a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir():
        raise ValueError("OUTPUT_MUST_BE_NEW_FILE_IN_EXISTING_DIRECTORY")
    output=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with a.output.open("xb") as f:f.write(output)
    print(json.dumps({"status":result["status"],
        "trials":29,"applications":23,
        "uniqueApplicationSourceUrls":result["uniqueApplicationSourceUrls"],
        "applicationSourceUrlsFetched":result["applicationSourceUrlsFetched"],
        "applicationGroupsWithAvailablePublicSource":result["applicationGroupsWithAvailablePublicSource"],
        "clinicalTrialsGovRecordsFetched":result["clinicalTrialsGovRecordsFetched"],
        "sourceDigest":hashlib.sha256(output).hexdigest(),
        "independentlyValidatedForecasts":0,"clinicalGradesWritten":0,
        "approvalProbability":None},sort_keys=True),flush=True)
    return 0

if __name__=="__main__":sys.exit(main())
