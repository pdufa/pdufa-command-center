#!/usr/bin/env python3
"""R42: source-reported primary outcome evidence for 29 FOCUS NCTs (not FDA forecasts)."""
from __future__ import annotations
import argparse,hashlib,json,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest,retrieve_url

NCT=re.compile(r"NCT\d{8}\Z")
def text(v,n=800):
    if v is None:return None
    if isinstance(v,(int,float,str)):
        x=str(v).strip()
        return x[:n] or None
    return None
def arr(v,n=200):return v[:n] if isinstance(v,list) else []
def extract(study:dict,nct:str,receipt:dict)->dict:
    if not isinstance(study,dict) or not NCT.fullmatch(nct) or \
       study.get("protocolSection",{}).get("identificationModule",{}).get("nctId")!=nct:
        raise ValueError("ORIGINAL_REGISTRY_IDENTITY_MISMATCH")
    protocol=study["protocolSection"]
    status=protocol.get("statusModule") or {}
    declared=arr((protocol.get("outcomesModule") or {}).get("primaryOutcomes"))
    section=study.get("resultsSection")
    has_results=isinstance(section,dict)
    outcome_mod=section.get("outcomeMeasuresModule",{}) if has_results else {}
    all_outcomes=arr(outcome_mod.get("outcomeMeasures"),120)
    primary=[p for p in all_outcomes if isinstance(p,dict) and p.get("type")=="PRIMARY"]
    outcomes=[]
    for p in primary:
        groups=[{"id":text(g.get("id"),80),"title":text(g.get("title"),150)}
                for g in arr(p.get("groups"),80) if isinstance(g,dict)]
        values=[]
        for cls in arr(p.get("classes"),120):
            if not isinstance(cls,dict):continue
            # API outcome classes may contain nested categories or direct measurements.
            categories=arr(cls.get("categories"),150) or [cls]
            for category in categories:
                if not isinstance(category,dict):continue
                for m in arr(category.get("measurements"),150):
                    if isinstance(m,dict):
                        values.append({"class":text(cls.get("title"),150),
                            "category":text(category.get("title"),150),
                            "groupId":text(m.get("groupId"),80),
                            "valueAsPublished":text(m.get("value"),100),
                            "spreadAsPublished":text(m.get("spread"),100),
                            "lowerLimitAsPublished":text(m.get("lowerLimit"),100),
                            "upperLimitAsPublished":text(m.get("upperLimit"),100)})
                    if len(values)>=250:break
                if len(values)>=250:break
            if len(values)>=250:break
        analysis=[]
        for a in arr(p.get("analyses"),80):
            if not isinstance(a,dict):continue
            analysis.append({"groupIds":arr(a.get("groupIds"),80),
                "pValueAsPublished":text(a.get("pValue"),100),
                "pValueCommentAsPublished":text(a.get("pValueComment"),250),
                "methodAsPublished":text(a.get("statisticalMethod"),200),
                "parameterAsPublished":text(a.get("paramValue"),100),
                "ciPercentAsPublished":text(a.get("ciPctValue"),100),
                "ciLowerAsPublished":text(a.get("ciLowerLimit"),100),
                "ciUpperAsPublished":text(a.get("ciUpperLimit"),100)})
        outcomes.append({"title":text(p.get("title"),400),
            "description":text(p.get("description"),800),
            "timeFrame":text(p.get("timeFrame"),300),
            "unitOfMeasure":text(p.get("unitOfMeasure"),100),
            "paramType":text(p.get("paramType"),100),
            "groups":groups,
            "denominators":[{"groupId":text(d.get("groupId"),80),
                "valueAsPublished":text(d.get("value"),100)}
                for d in arr(p.get("denoms"),150) if isinstance(d,dict)],
            "measurements":values,"statisticalAnalyses":analysis})
    return {"nct":nct,
        "sourceUrl":"https://clinicaltrials.gov/study/"+nct,
        "sourceApiUrl":receipt.get("url"),
        "sourceResponseSha256":receipt.get("sha256"),
        "sourceResponseBytes":receipt.get("bytes"),
        "currentRegistryResultsSectionPresent":has_results,
        "postedResultsDateAsReported":text((status.get("resultsFirstPostDateStruct") or {}).get("date"),40),
        "lastPostedUpdateAsReported":text((status.get("lastUpdatePostDateStruct") or {}).get("date"),40),
        "registeredPrimaryOutcomeCount":len(declared),
        "postedPrimaryOutcomeTableCount":len(primary),
        "primaryOutcomeTables":outcomes,
        "extractStatus":"PRIMARY_RESULTS_TABLE_EXTRACTED" if primary else
           ("RESULTS_SECTION_WITHOUT_POSTED_PRIMARY_TABLE" if has_results else
            "NO_CURRENT_REGISTRY_RESULTS_SECTION"),
        "lockedSapIndependentlyVerified":False,
        "originalSourcePostingClockIndependentlyVerified":False,
        "clinicalReviewerSignoff":False,
        "clinicalMethodGrade":None,
        "officialFdaForecast":"ABSTAIN",
        "caution":"Reported registry numerical fields and p-values, not recalculated, causally interpreted, multiplicity-adjusted or independently clinically adjudicated."}
def run(manifest,fetcher=retrieve_url,raw_dir:Path|None=None):
    if manifest.get("trialCount")!=29 or manifest.get("applicationCount")!=23:
        raise ValueError("FOCUS_29_23_MANIFEST_REQUIRED")
    def read(t):
        nct=t["nct"];obs,body=fetcher(t["registryUrl"])
        if obs.get("status")!="FETCHED" or body is None:
            return nct,{"nct":nct,"extractStatus":"UNAVAILABLE","fetchStatus":obs.get("status"),
                "clinicalMethodGrade":None,"officialFdaForecast":"ABSTAIN"},None
        if hashlib.sha256(body).hexdigest()!=obs.get("sha256"):
            raise ValueError("ORIGINAL_SOURCE_BYTES_SHA256_MISMATCH")
        try:
            return nct,extract(json.loads(body),nct,obs),body
        except (ValueError,TypeError,KeyError):
            return nct,{"nct":nct,"extractStatus":"INVALID_OR_MISMATCHED_ORIGINAL",
                "clinicalMethodGrade":None,"officialFdaForecast":"ABSTAIN"},None
    found={}
    with ThreadPoolExecutor(max_workers=5) as executor:
        for f in as_completed([executor.submit(read,t) for t in manifest["trialRows"]]):
            nct,rec,body=f.result()
            found[nct]=rec
            if body is not None and raw_dir is not None:
                if not raw_dir.is_dir() or raw_dir.is_symlink():
                    raise ValueError("ARCHIVE_DIR_NOT_READY")
                with (raw_dir/(nct+".json")).open("xb") as output:output.write(body)
    ordered=[found[t["nct"]] for t in manifest["trialRows"]]
    if len(ordered)!=29 or len({r["nct"] for r in ordered})!=29:
        raise ValueError("INCOMPLETE_FOCUS_ROSTER")
    good=sum(r["extractStatus"] not in ("INVALID_OR_MISMATCHED_ORIGINAL","UNAVAILABLE") for r in ordered)
    return {"schema":"MAIN_R42_29_TRIAL_REGISTRY_PRIMARY_EVIDENCE",
        "snapshotAsOf":manifest["asOf"],
        "observedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nctCount":29,"applicationGroupCount":23,"registryFetched":good,
        "registryWithResultsSection":sum(r.get("currentRegistryResultsSectionPresent") is True for r in ordered),
        "registryWithPrimaryTables":sum(r.get("postedPrimaryOutcomeTableCount",0)>0 for r in ordered),
        "postedPrimaryOutcomeTableCount":sum(r.get("postedPrimaryOutcomeTableCount",0) for r in ordered),
        "records":ordered,
        "independentClinicalGrades":0,"validatedApplicationPredictions":0,
        "realHistoricalBacktests":0,"calibratedAccuracy":None,
        "futureFdaApprovalCrlForecast":"ABSTAIN",
        "futureReviewDelayForecast":"ABSTAIN",
        "trainedFdaModelAuthorized":False,
        "evidenceLimitations":"Current CT.gov posted outcomes do not replace original Phase 3 publication, full locked SAP, registered endpoint hierarchy, safety, CMC, or independent review; absence from the registry does not imply absence of published Phase 3 data."}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--raw-dir",required=True,type=Path)
    args=p.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        raise ValueError("IMMUTABLE_OUTPUT_FILE_REQUIRED")
    manifest=build_manifest(_read_json(ROSTER),_read_json(APPS))
    result=run(manifest,raw_dir=args.raw_dir)
    with args.output.open("xb") as f:f.write((json.dumps(result,indent=2,sort_keys=True)+"\n").encode())
    print(json.dumps({k:result[k] for k in (
        "nctCount","applicationGroupCount","registryFetched","registryWithResultsSection",
        "registryWithPrimaryTables","postedPrimaryOutcomeTableCount",
        "independentClinicalGrades","validatedApplicationPredictions",
        "realHistoricalBacktests","futureFdaApprovalCrlForecast")}),flush=True)
if __name__=="__main__":main()
