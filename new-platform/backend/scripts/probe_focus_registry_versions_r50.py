#!/usr/bin/env python3
"""R50 source-only probe: registry's record-history interface for three exact FOCUS NCTs.

The /api/int history route is an undocumented ClinicalTrials.gov browser endpoint:
report HTTP failures and schema changes explicitly; never infer historical text
from the present-day registry. No model training, FDA outcome, clinical grade.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest,retrieve_url
NCTS=("NCT04544293","NCT05126758","NCT05208047")
def probe():
    m=build_manifest(_read_json(ROSTER),_read_json(APPS))
    names={r["nct"] for r in m["trialRows"]}
    if m["trialCount"]!=29 or m["applicationCount"]!=23 or not set(NCTS)<=names:
        raise ValueError("ORIGINAL_29_23_REGISTRY_VERSION_ROSTER_CHANGED")
    for nct in NCTS:
        for label,path in [("www-history-query",f"/api/int/studies/{nct}?history=true"),
                           ("www-first-version",f"/api/int/studies/{nct}/history/0"),
                           ("www-history-index",f"/api/int/studies/{nct}/history")]:
            url="https://www.clinicaltrials.gov"+path
            receipt,payload=retrieve_url(url)
            result={"nct":nct,"kind":label,"http":receipt.get("status"),
                    "bytes":receipt.get("bytes"),"sha256":receipt.get("sha256"),
                    "registryUrl":"https://clinicaltrials.gov/study/"+nct+"?tab=history"}
            if payload is not None:
                try:
                    o=json.loads(payload)
                    result["jsonRootType"]=type(o).__name__
                    if isinstance(o,dict):
                        result["topLevelKeys"]=sorted(o)[:35]
                        for k in ("changes","versions","history","protocolSection","study"):
                            v=o.get(k)
                            if isinstance(v,dict):result[k+"Keys"]=sorted(v)[:25]
                            elif isinstance(v,list):
                                result[k+"Count"]=len(v)
                                if v and isinstance(v[0],dict):result[k+"FirstKeys"]=sorted(v[0])[:30]
                        p=o.get("protocolSection")
                        if isinstance(p,dict):
                            result["idFromVersion"]=p.get("identificationModule",{}).get("nctId")
                            result["statusKeys"]=sorted(p.get("statusModule",{}))[:25]
                            result["primaryOutcomeCount"]=len((p.get("outcomesModule") or {}).get("primaryOutcomes") or [])
                    elif isinstance(o,list):
                        result["topLevelCount"]=len(o)
                        if o and isinstance(o[0],dict):result["firstKeys"]=sorted(o[0])[:30]
                except (json.JSONDecodeError,TypeError) as e:
                    result["jsonParsing"]="NOT_JSON"
            print(json.dumps(result,sort_keys=True),flush=True)

if __name__=="__main__":probe()
