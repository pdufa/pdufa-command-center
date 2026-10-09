#!/usr/bin/env python3
"""Full tracked-company ClinicalTrials.gov phase inventory. Never certifies nonclinical sources."""
import argparse
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
API = "https://clinicaltrials.gov/api/v2/studies"
PHASES = ("EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA")
FIELDS = ["ticker","company","nct_id","phase","status","drug","indication","start_date","primary_completion","study_completion","results_posted","source_updated","source_url","checked_at"]
def stamp():
    return datetime.now(timezone.utc).isoformat()
def sponsor_query_name(v):
    # SEC issuer names can end with a jurisdiction marker such as \DE\.
    # Those backslashes are query syntax, not part of the trial sponsor name.
    return re.sub(r"\s*\\[A-Za-z]{2}\\\s*$", "", str(v or "")).strip()
def normalized(v):
    return re.sub(r"[^a-z0-9]+"," ",sponsor_query_name(v).lower()).strip()
def rows(path):
    if not path.exists(): return []
    with path.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
def save(path, obj):
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
    temp.replace(path)
def save_csv(path, records):
    temp=path.with_suffix(path.suffix+".tmp")
    with temp.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction="ignore");w.writeheader();w.writerows(records)
    temp.replace(path)
def collect(session, company, ticker):
    token=None;found={}; pages=0
    while True:
        params={"query.spons":sponsor_query_name(company),"pageSize":100,"format":"json"}
        if token:params["pageToken"]=token
        for attempt in range(4):
            try:
                resp=session.get(API,params=params,timeout=(10,45));resp.raise_for_status()
                payload=resp.json();break
            except (requests.RequestException,ValueError):
                if attempt==3:raise
                time.sleep(2**attempt)
        if not isinstance(payload.get("studies"),list):raise ValueError("Missing studies list")
        for study in payload["studies"]:
            p=study.get("protocolSection",{})
            sponsor=p.get("sponsorCollaboratorsModule",{}).get("leadSponsor",{}).get("name","")
            if normalized(sponsor)!=normalized(company):continue
            ident=p.get("identificationModule",{}).get("nctId","")
            if not re.fullmatch(r"NCT\d{8}",ident):continue
            design=p.get("designModule",{});status=p.get("statusModule",{})
            arms=p.get("armsInterventionsModule",{})
            drugs=sorted({x.get("name","") for x in arms.get("interventions",[]) if x.get("type") in ("DRUG","BIOLOGICAL") and x.get("name")})
            found[ident]={"ticker":ticker,"company":company,"nct_id":ident,"phase":"|".join(design.get("phases",[]) or ["NA"]),
                "status":status.get("overallStatus",""),"drug":" | ".join(drugs),
                "indication":" | ".join(p.get("conditionsModule",{}).get("conditions",[])),
                "start_date":status.get("startDateStruct",{}).get("date",""),
                "primary_completion":status.get("primaryCompletionDateStruct",{}).get("date",""),
                "study_completion":status.get("completionDateStruct",{}).get("date",""),
                "results_posted":status.get("resultsFirstPostDateStruct",{}).get("date",""),
                "source_updated":status.get("lastUpdatePostDateStruct",{}).get("date",""),
                "source_url":"https://clinicaltrials.gov/study/"+ident,"checked_at":stamp()}
        pages+=1;token=payload.get("nextPageToken")
        if not token:break
        if pages>=200:raise RuntimeError("Company pagination safety limit reached")
    return found

def scan(data_dir):
    data_dir.mkdir(parents=True,exist_ok=True)
    registry=rows(data_dir/"company_registry.csv")
    companies={(r.get("ticker","").strip(),r.get("company","").strip()) for r in registry if r.get("ticker","").strip() and r.get("company","").strip()}
    if not companies:raise RuntimeError("Company registry empty or missing")
    today=datetime.now(timezone.utc).date().isoformat()
    state_path=data_dir/"all_phase_scan_state.json"; ledger_path=data_dir/"all_phase_trials.csv"
    previous=json.loads(state_path.read_text()) if state_path.exists() else {}
    same_day=previous.get("run_date")==today and previous.get("registry_companies")==len(companies)
    checks=previous.get("checks",{}) if same_day else {}
    existing={r["nct_id"]:r for r in rows(ledger_path)}
    session=requests.Session()
    try:
        for ticker,company in sorted(companies):
            key=ticker+"|"+company
            if checks.get(key,{}).get("status")=="COMPLETE":continue
            try:
                found=collect(session,company,ticker)
                existing.update(found)
                checks[key]={"status":"COMPLETE","checked_at":stamp(),"matched_trials":len(found)}
            except Exception as exc:
                checks[key]={"status":"WARNING","checked_at":stamp(),"error":str(exc)[:350]}
            save_csv(ledger_path,list(existing.values()))
            save(state_path,{"run_date":today,"started_at":previous.get("started_at",stamp()) if same_day else stamp(),
                "finished_at":stamp(),"registry_companies":len(companies),"companies_checked":len(checks),
                "checks":checks,"status":"RUNNING"})
            time.sleep(0.15)
    finally:session.close()
    attempted=len(checks);warn=sum(x["status"]!="COMPLETE" for x in checks.values())
    status="PARTIAL" if attempted<len(companies) else "COMPLETE WITH WARNINGS" if warn else "COMPLETE"
    final={"run_date":today,"finished_at":stamp(),"registry_companies":len(companies),
           "companies_checked":attempted,"companies_with_warnings":warn,
           "trials_stored":len(existing),"status":status,"complete":status=="COMPLETE",
           "scope":"All registered phases, all registry companies; exact lead-sponsor matching only",
           "limitations":"Does not cover subsidiary/alternate sponsors or FDA/SEC/market sources",
           "checks":checks}
    save(state_path,final);print(json.dumps({k:v for k,v in final.items() if k!="checks"},indent=2))
    return 0 if status!="PARTIAL" else 1
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--data-dir",type=Path,default=ROOT/"data")
    args=p.parse_args();raise SystemExit(scan(args.data_dir))
