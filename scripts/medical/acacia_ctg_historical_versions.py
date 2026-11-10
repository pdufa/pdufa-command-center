#!/usr/bin/env python3
"""Single-trial original-version crosscheck. Local source artifacts only; no secrets, grades, or app writes."""
from __future__ import annotations
import argparse, hashlib, json, urllib.request, urllib.error, datetime
from pathlib import Path
from urllib.parse import urlsplit

NCT="NCT06081894"
HOSTS={"clinicaltrials.gov","www.clinicaltrials.gov"}
BASE=f"https://www.clinicaltrials.gov/api/int/studies/{NCT}"
# CT.gov public UI numbers versions starting at 1; API indexes zero based.
VERSIONS={25:("v26","2025-01-11"),26:("v27","2025-05-15"),28:("v29","2026-01-29"),29:("v30","2026-08-03")}
OUT=Path("acacia-original-ctg-versions")
MAX_BYTES=2_500_000
def fetch(url, *, artifact=None):
    req=urllib.request.Request(url,headers={"Accept":"application/json",
        "User-Agent":"MAIN-public-trial-version-crosscheck/1.0 (NCT06081894 only; no credentials)"})
    with urllib.request.urlopen(req,timeout=25) as response:
        final=urlsplit(response.url)
        if final.scheme!="https" or final.hostname not in HOSTS or final.username or final.password:
            raise ValueError("INVALID_SOURCE_OR_REDIRECT")
        data=response.read(MAX_BYTES+1)
        if len(data)>MAX_BYTES: raise ValueError("SOURCE_TOO_LARGE")
        if "json" not in response.headers.get("content-type","").lower():
            raise ValueError("NON_JSON_RESPONSE")
    parsed=json.loads(data)
    if artifact is not None:
        Path(artifact).write_bytes(data)
    return parsed,hashlib.sha256(data).hexdigest()

def safe_outcomes(study):
    if not isinstance(study,dict):raise ValueError("STUDY_NOT_RECORD")
    pm=study.get("protocolSection",{})
    if not isinstance(pm,dict):raise ValueError("NO_PROTOCOL_SECTION")
    ids=pm.get("identificationModule",{})
    if ids.get("nctId")!=NCT:raise ValueError("CROSS_STUDY_ID_MISMATCH")
    o=pm.get("outcomesModule",{})
    if not isinstance(o,dict):o={}
    def arr(field):
        values=o.get(field,[])
        if not isinstance(values,list):raise ValueError("OUTCOMES_NOT_ARRAY")
        if len(values)>30:raise ValueError("OUTCOME_LIMIT_REQUIRES_MANUAL_REVIEW")
        if any(not isinstance(x,dict) or not isinstance(x.get("measure"),str) or not x["measure"].strip()
               or not isinstance(x.get("timeFrame",""),str) or not isinstance(x.get("description",""),str)
               for x in values):raise ValueError("MALFORMED_ORIGINAL_ENDPOINT")
        # Original wording is evidence: never truncate or silently drop it.
        return [{"measure":x["measure"],"timeFrame":x.get("timeFrame",""),
                 "description":x.get("description","")} for x in values]
    dm=pm.get("designModule",{})
    if not isinstance(dm,dict):dm={}
    en=dm.get("enrollmentInfo",{})
    if not isinstance(en,dict):en={}
    date=pm.get("statusModule",{})
    return {"primary":arr("primaryOutcomes"),"secondary":arr("secondaryOutcomes"),
       "enrollment":en,"studyDesign":dm.get("designInfo"),
       "lastUpdateSubmitted":date.get("lastUpdateSubmitDate"),
       "lastUpdatePosted":date.get("lastUpdatePostDateStruct"),
       "phase":dm.get("phases"),"overallStatus":date.get("overallStatus")}


def validate_original_version(body, api_index, submitted_date):
    """Bind actual payload identity and date; a numbered URL alone is not proof."""
    if not isinstance(body,dict) or type(body.get("studyVersion")) is not int or body["studyVersion"]!=api_index:
        raise ValueError("ORIGINAL_VERSION_ID_MISMATCH")
    result=safe_outcomes(body.get("study"))
    if result["lastUpdateSubmitted"]!=submitted_date:
        raise ValueError("ORIGINAL_VERSION_SUBMISSION_DATE_MISMATCH")
    return result


def validate_history_index(overview):
    if not isinstance(overview,dict):raise ValueError("HISTORY_NOT_RECORD")
    safe_outcomes(overview.get("study"))
    changes=overview.get("history",{}).get("changes",[])
    if not isinstance(changes,list):raise ValueError("HISTORY_NOT_LIST")
    dates={}
    for item in changes:
        if not isinstance(item,dict) or type(item.get("version")) is not int or item["version"] in dates:
            raise ValueError("INVALID_OR_DUPLICATE_HISTORY_VERSION")
        dates[item["version"]]=item.get("date")
    for index,(_,expected) in VERSIONS.items():
        if dates.get(index)!=expected:raise ValueError("HISTORY_VERSION_DATE_DRIFT")
    return dates


def reconcile_public_browser_capture(directory):
    """Validate raw ordinary-public-UI captures using the same scientific guard."""
    directory=Path(directory)
    receipt=json.loads((directory/"public_browser_receipt.json").read_text())
    if (receipt.get("nct")!=NCT or receipt.get("accessMethod")!="STANDARD_PUBLIC_HISTORY_UI"
            or receipt.get("clinicalSignoff") is not False or receipt.get("gradedMethods")!=0):
        raise ValueError("INVALID_PUBLIC_UI_RECEIPT")
    def original(entry,name,url):
        if (entry.get("artifact")!=name or entry.get("sourceUrl")!=url or entry.get("httpStatus")!=200):
            raise ValueError("UNVERIFIED_ORIGINAL_SOURCE_RECEIPT")
        raw=(directory/name).read_bytes()
        if len(raw)!=entry.get("bytes") or hashlib.sha256(raw).hexdigest()!=entry.get("sha256"):
            raise ValueError("ORIGINAL_SOURCE_DIGEST_MISMATCH")
        return json.loads(raw)
    index=original(receipt.get("index",{}),"original_history_index.json",
                   f"https://clinicaltrials.gov/api/int/studies/{NCT}?history=true")
    validate_history_index(index)
    versions={}
    entries=receipt.get("versions",[])
    if len(entries)!=4 or len({e.get("version") for e in entries})!=4:
        raise ValueError("ORIGINAL_FOUR_VERSION_COVERAGE_REQUIRED")
    for api_index,(label,expected) in VERSIONS.items():
        matches=[e for e in entries if e.get("version")==api_index+1]
        if len(matches)!=1:raise ValueError("ORIGINAL_VERSION_COVERAGE_MISMATCH")
        entry=matches[0]
        body=original(entry,label+"_original_registry.json",
                      f"https://clinicaltrials.gov/api/int/studies/{NCT}/history/{api_index}")
        versions[label]={"apiIndex":api_index,"submitted":expected,"sourceUrl":entry["sourceUrl"],
            "sourceSha256":entry["sha256"],"outcomes":validate_original_version(body,api_index,expected)}
    result={"schema":"MAIN_OFFICIAL_PUBLIC_UI_HISTORY_RECONCILIATION_V1","nct":NCT,
        "retrievedAt":receipt["retrievedAt"],"accessMethod":receipt["accessMethod"],
        "officialHistoryDatesVerified":True,"sourceVersionCompleteness":True,"versionData":versions,
        "directV26V27":verified_primary_endpoint_delta(versions["v26"]["outcomes"],versions["v27"]["outcomes"]),
        "directV29V30":verified_primary_endpoint_delta(versions["v29"]["outcomes"],versions["v30"]["outcomes"]),
        "clinicalSignoff":False,"gradedMethods":0,"phaseReviewerVerified":False,
        "fdaPredictions":{"APPROVAL":"ABSTAIN","CRL":"ABSTAIN","REVIEW_DELAY":"ABSTAIN"},
        "accuracy":"NOT_CALIBRATED"}
    (directory/"validated_comparison.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    return result


def verified_primary_endpoint_delta(before, after):
    """Compare exact official version texts, never infer causal or clinical validity."""
    if not isinstance(before,dict) or not isinstance(after,dict):
        raise ValueError("MISSING_ORIGINAL_VERSION_DATA")
    old,new=before.get("primary"),after.get("primary")
    if not isinstance(old,list) or not isinstance(new,list):
        raise ValueError("MISSING_ORIGINAL_PRIMARY_OUTCOMES")
    def keys(items):
        result=[]
        for item in items:
            if not isinstance(item,dict) or not isinstance(item.get("measure"),str) or not item["measure"].strip():
                raise ValueError("UNVERIFIED_ENDPOINT_DEFINITION")
            key=(item["measure"].strip(),str(item.get("timeFrame","")).strip())
            if key in result:raise ValueError("DUPLICATE_ENDPOINT")
            result.append(key)
        return result
    b,a=keys(old),keys(new)
    added=[{"measure":n,"timeFrame":t} for (n,t) in a if (n,t) not in b]
    removed=[{"measure":n,"timeFrame":t} for (n,t) in b if (n,t) not in a]
    descriptions_before={key:item.get("description","") for key,item in zip(b,old)}
    descriptions_after={key:item.get("description","") for key,item in zip(a,new)}
    description_changes=[{"measure":name,"timeFrame":time,"before":descriptions_before[(name,time)],
                          "after":descriptions_after[(name,time)]}
                         for name,time in b if (name,time) in descriptions_after
                         and descriptions_before[(name,time)]!=descriptions_after[(name,time)]]
    return {
        "primaryBefore":len(old),"primaryAfter":len(new),
        "primaryBeforeDefinitions":old,"primaryAfterDefinitions":new,
        "primaryMeasureAdded":added,"primaryMeasureRemoved":removed,
        "primaryDescriptionChanges":description_changes,
        "enrollmentBefore":before.get("enrollment"),
        "enrollmentAfter":after.get("enrollment"),
        "originalVersionTextsVerifiedByApi":True,
        "clinicalIntegrityJudgment":"AWAITING_FULL_PROTOCOL_SAP_TIMELINE_ADJUDICATION",
        "interpretation":"OFFICIAL_HISTORICAL_TEXT_DIFF_NOT_A_POST_HOC_INTEGRITY_VERDICT"
    }

def main():
    OUT.mkdir(exist_ok=True)
    final={"schema":"MAIN_OFFICIAL_CLINICALTRIALS_VERSION_CROSSWALK_V1",
        "nct":NCT,"recordedDate":"2026-11-08","researchOnly":True,
        "clinicalSignoff":False,"gradedMethods":0,"phaseReviewerVerified":False,
        "fdaPredictions":{"APPROVAL":"ABSTAIN","CRL":"ABSTAIN","REVIEW_DELAY":"ABSTAIN"},
        "versionData":{},"overviewStatus":"NOT_RETRIEVED","sourceVersionCompleteness":False}
    try:
        overview,sha=fetch(BASE+"?history=true",artifact=OUT/"original_history_index.json")
        dates=validate_history_index(overview)
        final["overviewStatus"]="OFFICIAL_HISTORY_RETRIEVED"
        final["overviewSha256"]=sha
        final["observedApiIndices"]=len(dates)
        print("CTGV_INFO history API indices="+str(len(dates))+" sample="+repr(list(dates.items())[-5:]))
        final["overviewTargets"]={}
        for version,(label,expected) in VERSIONS.items():
            listed=dates.get(version)
            final["overviewTargets"][label]={"apiIndex":version,"expectedSubmitted":expected,"apiDate":listed,
                "dateMatched":listed==expected}
            if listed!=expected:
                raise ValueError("HISTORY_VERSION_DATE_DRIFT_"+label)
    except (urllib.error.HTTPError, urllib.error.URLError,TimeoutError,ValueError,KeyError,TypeError,AttributeError,
            json.JSONDecodeError) as error:
        final["overviewStatus"]="NOT_VERIFIED"
        final["overviewErrorClass"]=type(error).__name__
        if isinstance(error,urllib.error.HTTPError): final["overviewHttpStatus"]=error.code
        print("CTGV_INFO overview unavailable or date mismatch:",type(error).__name__,str(error)[:100])
    for version,(label,expected) in VERSIONS.items():
        try:
            body,sha=fetch(BASE+"/history/"+str(version),artifact=OUT/(label+"_original_registry.json"))
            if not isinstance(body,dict):raise ValueError("NOT_RECORD")
            reported=body.get("studyVersion")
            if isinstance(reported,(int,str)) and str(reported)!=str(version):
                raise ValueError("UNEXPECTED_API_VERSION")
            study=body.get("study")
            data=validate_original_version(body,version,expected)
            final["versionData"][label]={"apiIndex":version,"submitted":expected,
                "sourceUrl":BASE+"/history/"+str(version),
                "sourceSha256":sha,"status":"OFFICIAL_VERSION_RETRIEVED",
                "reportedApiVersion":reported,"outcomes":data}
            print("CTGV_VERSION "+label+" #primary="+str(len(data["primary"]))+
                  " #secondary="+str(len(data["secondary"]))+
                  " enrollment="+repr(data["enrollment"])+
                  " titles="+repr([o["measure"][:100] for o in data["primary"]]))
            # fetch persisted exact response bytes, matching sourceSha256 (no JSON reformatting).
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError,KeyError,TypeError,AttributeError,
                json.JSONDecodeError) as error:
            final["versionData"][label]={"apiIndex":version,"status":"NOT_VERIFIED",
                "errorClass":type(error).__name__}
            if isinstance(error,urllib.error.HTTPError):final["versionData"][label]["httpStatus"]=error.code
            print("CTGV_VERSION "+label+" unavailable "+type(error).__name__)
    final["originalV26V27ComparisonVerified"]=False
    final["originalV26V27Status"]="NOT_VERIFIED"
    # A direct original v26/v27 comparison is useful independently of whether
    # later v29/v30 endpoints are retrievable. Require the official version index
    # and exact submitted-date crosswalk for both versions first.
    index=final.get("overviewTargets",{})
    version_check=(final["overviewStatus"]=="OFFICIAL_HISTORY_RETRIEVED" and
        all(index.get(name,{}).get("dateMatched") is True for name in ["v26","v27"]) and
        all(final["versionData"].get(name,{}).get("status")=="OFFICIAL_VERSION_RETRIEVED"
            for name in ["v26","v27"]))
    if version_check:
        try:
            before=final["versionData"]["v26"]["outcomes"]
            after=final["versionData"]["v27"]["outcomes"]
            delta=verified_primary_endpoint_delta(before,after)
            final["directV26V27"]=delta
            final["originalV26V27ComparisonVerified"]=True
            final["originalV26V27Status"]="OFFICIAL_PRIMARY_OUTCOME_TEXT_COMPARED"
            print("CTGV_ORIGINAL_DIFF official v26 to v27, primary="+
                  str(delta["primaryBefore"])+" -> "+str(delta["primaryAfter"])+
                  "; added="+str(len(delta["primaryMeasureAdded"]))+
                  "; removed="+str(len(delta["primaryMeasureRemoved"])))
        except (KeyError,TypeError,ValueError) as exc:
            final["originalV26V27Status"]="ORIGINAL_OUTCOME_VALIDATION_FAILED"
            final["originalV26V27ErrorClass"]=type(exc).__name__
    if all(final["versionData"].get(name,{}).get("status")=="OFFICIAL_VERSION_RETRIEVED"
           for name in ["v26","v27","v29","v30"]):
        final["sourceVersionCompleteness"]=final["overviewStatus"]=="OFFICIAL_HISTORY_RETRIEVED"
    # Even a verified official endpoint change is not evidence of post hoc
    # manipulation, alpha error, or a defensible regulatory prediction.
    (OUT/"source_receipt.json").write_text(json.dumps(final,indent=2)+"\n",encoding="utf-8")
    return 0

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-browser-capture",type=Path,
                        help="Validate preserved original responses delivered by the standard public history UI")
    args=parser.parse_args()
    if args.public_browser_capture:
        result=reconcile_public_browser_capture(args.public_browser_capture)
        print(json.dumps({"originalVersionsVerified":result["sourceVersionCompleteness"],
            "v26Primary":result["directV26V27"]["primaryBefore"],
            "v27Primary":result["directV26V27"]["primaryAfter"],"clinicalGrades":0,"fda":"ABSTAIN"}))
    else:
        raise SystemExit(main())
