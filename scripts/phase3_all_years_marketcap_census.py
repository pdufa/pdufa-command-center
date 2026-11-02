#!/usr/bin/env python3
"""All-years Phase 3 census for currently $300M-$10B US-listed biotech/pharma.
Strict lead-sponsor name matching; report unmatched and unavailable cap separately.
"""
import csv,json,re,time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];D=ROOT/"data"
def read(p):
 with (D/p).open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def norm(s):
 s=re.sub(r"[^a-z0-9]+"," ",str(s or "").lower())
 return " ".join(x for x in s.split() if x not in {"inc","incorporated","corporation","corp","company","co","plc","ltd","limited","llc","nv","ag","sa"})
registry=read("company_registry.csv");caps=read("phase_pipeline_market_caps.csv")
byname={}
for r in registry:
 if r.get("status")!="OK":continue
 key=norm(r.get("company"))
 if key:byname.setdefault(key,set()).add(r["ticker"].upper())
capmap={r["ticker"].upper():r for r in caps}
eligible=set();unknown=set()
for r in registry:
 ticker=r["ticker"].upper();c=capmap.get(ticker,{})
 try:cap=float(c.get("market_cap") or "")
 except ValueError:cap=None
 if c.get("market_cap_status")=="VERIFIED" and cap is not None:
  if 300_000_000<=cap<=10_000_000_000:eligible.add(ticker)
 else:unknown.add(ticker)
params={"filter.advanced":"AREA[Phase]PHASE3 AND AREA[StudyType]INTERVENTIONAL AND AREA[LeadSponsorClass]INDUSTRY","pageSize":1000,"format":"json","fields":"NCTId,Phase,LeadSponsorName,LeadSponsorClass,OverallStatus"}
page=0;seen=set();matched={};unknown_rows={};ambiguous=0;total=0
while True:
 for attempt in range(5):
  try:
   req=Request("https://clinicaltrials.gov/api/v2/studies?"+urlencode(params),headers={"User-Agent":"PDUFA-Census/1.0 research"})
   with urlopen(req,timeout=90) as f:payload=json.load(f)
   break
  except Exception:
   if attempt==4:raise
   time.sleep(2**attempt)
 studies=payload.get("studies",[])
 for s in studies:
  p=s.get("protocolSection",{})
  nct=p.get("identificationModule",{}).get("nctId","")
  if not re.fullmatch(r"NCT\d{8}",nct) or nct in seen:continue
  seen.add(nct);total+=1
  sponsor=p.get("sponsorCollaboratorsModule",{}).get("leadSponsor",{}).get("name","")
  ticks=byname.get(norm(sponsor),set())
  if len(ticks)>1:ambiguous+=1;continue
  if not ticks:continue
  ticker=next(iter(ticks))
  row={"nct_id":nct,"ticker":ticker,"company":sponsor,"status":p.get("statusModule",{}).get("overallStatus",""),"source_url":"https://clinicaltrials.gov/study/"+nct}
  if ticker in eligible:matched[nct]=row
  elif ticker in unknown:unknown_rows[nct]=row
 page+=1
 token=payload.get("nextPageToken")
 if not token:break
 params["pageToken"]=token
 if page>300:raise RuntimeError("Unexpected pagination; refusing incomplete count")
out=D/"phase3_all_years_300m_10b_trials.csv"
with out.open("w",newline="",encoding="utf-8") as f:
 w=csv.DictWriter(f,fieldnames=["nct_id","ticker","company","status","source_url"],lineterminator="\n");w.writeheader();w.writerows(sorted(matched.values(),key=lambda x:(x["ticker"],x["nct_id"])))
status={"generated_at":datetime.now(timezone.utc).isoformat(),"scope":"All years, Phase 3 interventional trials, industry lead sponsor matched exactly to currently US-listed company, market cap $300M-$10B","market_cap_snapshot":"data/phase_pipeline_market_caps.csv","registry_companies":len(registry),"market_cap_eligible_tickers":len(eligible),"market_cap_unavailable_tickers":len(unknown),"registry_phase3_industry_trials_examined":total,"pages":page,"unique_phase3_trials_in_verified_market_cap_range":len(matched),"unique_companies_with_matching_trials":len({r["ticker"] for r in matched.values()}),"trial_records_with_unavailable_market_cap":len(unknown_rows),"ambiguous_sponsor_records":ambiguous,"complete_registry_pagination":True,"coverage_note":"Conservative lower bound: exact lead-sponsor matching only. Collaborator/licensing trials, renamed subsidiaries, and missing market caps not included; not a fully exhaustive company-associated census."}
(D/"phase3_all_years_300m_10b_status.json").write_text(json.dumps(status,indent=2)+"\n")
print(json.dumps(status,indent=2))
