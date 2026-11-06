#!/usr/bin/env python3
"""Source-only 253-trial research. No fabricated FDA or clinical outcome scores."""
import argparse,concurrent.futures as cf,json,re,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"new-platform/frontend/data/phase3PreDataBatch20261105.json"
OUTPUT=ROOT/"new-platform/frontend/data/phase3PreDataOfficialResearch.json"
API="https://clinicaltrials.gov/api/v2/studies"
OMIT=re.compile(r"\b(placebo|vehicle|standard of care|sham|saline|no investigational)\b",re.I)
def get(url):
 for attempt in range(4):
  try:
   with urlopen(Request(url,headers={"User-Agent":"PDUFA-Research-Evidence/1.0","Accept":"application/json"}),timeout=25) as r:return json.load(r)
  except HTTPError as e:
   if e.code in (400,401,403,404) or attempt==3:raise
   h=e.headers.get("Retry-After","") if e.headers else ""
   time.sleep(min(45,int(h) if h.isdigit() else 2**(attempt+2)))
  except (URLError,OSError,TimeoutError):
   if attempt==3:raise
   time.sleep(2**(attempt+1))
def norm(s):return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",str(s or "").lower())).strip()
def dn(s):
 s=re.sub(r"\([^)]*\)","",str(s or ""))
 s=re.sub(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|ug|iu|%)(?:/\w+)?\b","",s,flags=re.I)
 s=re.sub(r"\b(?:open.label|oral|injection|tablet|capsule|dose|qd|bid|daily|weekly|sc|iv)\b","",s,flags=re.I)
 return norm(s)
def excerpt(study):
 p=study.get("protocolSection") or {}
 ident=p.get("identificationModule") or {}
 status=p.get("statusModule") or {}
 design=p.get("designModule") or {}
 arms=p.get("armsInterventionsModule") or {}
 outcomes=p.get("outcomesModule") or {}
 di=design.get("designInfo") or {}
 return {"nctId":ident.get("nctId",""),"title":ident.get("briefTitle","")[:320],
 "phase":design.get("phases") or [],"status":status.get("overallStatus",""),
 "firstPosted":(status.get("studyFirstPostDateStruct") or {}).get("date",""),
 "sourceUpdated":(status.get("lastUpdatePostDateStruct") or {}).get("date",""),
 "resultsFirstPosted":(status.get("resultsFirstPostDateStruct") or {}).get("date",""),
 "primaryCompletionDate":(status.get("primaryCompletionDateStruct") or {}).get("date",""),
 "enrollment":(design.get("enrollmentInfo") or {}).get("count"),
 "allocation":di.get("allocation",""),"masking":(di.get("maskingInfo") or {}).get("masking",""),
 "interventionModel":di.get("interventionModel",""),
 "interventions":[{"name":i.get("name",""),"type":i.get("type",""),"aliases":(i.get("otherNames") or [])[:6]} for i in (arms.get("interventions") or [])][:24],
 "arms":[{"type":a.get("type",""),"label":a.get("label","")} for a in (arms.get("armGroups") or [])][:12],
 "conditions":(p.get("conditionsModule") or {}).get("conditions") or [],
 "primaryOutcomes":[{"measure":x.get("measure","")[:500],"timeFrame":x.get("timeFrame","")[:250]} for x in (outcomes.get("primaryOutcomes") or [])][:8],
 "secondaryOutcomes":[{"measure":x.get("measure","")[:350],"timeFrame":x.get("timeFrame","")[:150]} for x in (outcomes.get("secondaryOutcomes") or [])][:16],
 "references":[{"pmid":x.get("pmid",""),"type":x.get("type",""),"citation":x.get("citation","")[:280]} for x in ((p.get("referencesModule") or {}).get("references") or [])][:20],
 "hasResults":bool(study.get("hasResults") or study.get("resultsSection"))}
def results(study):
 r=study.get("resultsSection") or {}
 m=(r.get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []
 ev=r.get("adverseEventsModule") or {}
 return {"primary":[{"title":x.get("title","")[:220],"timeFrame":x.get("timeFrame","")[:150],
  "analyses":[{"pValue":a.get("pValue"),"pValueModifier":a.get("pValueModifier",""),"groupIds":a.get("groupIds") or [],"method":a.get("statisticalMethod","")} for a in (x.get("analyses") or [])[:7]]} for x in m if x.get("type")=="PRIMARY"][:8],
  "seriousEventCount":len(ev.get("seriousEvents") or []),"otherEventCount":len(ev.get("otherEvents") or []),
  "seriousEventExamples":[{"term":x.get("term",""),"stats":(x.get("stats") or [])[:5]} for x in (ev.get("seriousEvents") or [])[:5]]}
def fetch_target(rec):
 n=rec["nctId"]
 try:
  raw=get(API+"/"+n);e=excerpt(raw)
  if e["nctId"]!=n:raise ValueError("NCT_MISMATCH")
  return n,{"sourceState":"FETCHED","registry":e,"sourceUrl":"https://clinicaltrials.gov/study/"+n}
 except Exception as ex:
  return n,{"sourceState":"ERROR","error":type(ex).__name__+":"+str(ex)[:140]}
def key_for(source):
 p=source.get("registry") or {}
 active=[i for i in p.get("interventions",[]) if i["type"] in ("DRUG","BIOLOGICAL","GENETIC") and not OMIT.search(i["name"])]
 if len(active)!=1:return None
 drug=active[0]["name"];conditions=p.get("conditions") or []
 if len(dn(drug))<4 or not conditions:return None
 return (drug,tuple(conditions))
def fetch_prior(q):
 drug,conditions=q
 try:
  obj=get(API+"?"+urlencode({"query.intr":drug,"filter.advanced":"AREA[Phase]PHASE2","pageSize":100}))
  candidates=[]
  for raw in obj.get("studies") or []:
   x=excerpt(raw)
   if "PHASE2" not in x["phase"]:continue
   if not set(norm(c) for c in conditions).intersection(norm(c) for c in x["conditions"]):continue
   if not any(dn(drug)==dn(i["name"]) for i in x["interventions"] if i["type"] in ("DRUG","BIOLOGICAL","GENETIC")):continue
   x["registeredResults"]=results(raw) if x["hasResults"] else None
   candidates.append(x)
  return {"state":"SEARCHED","query":drug,"truncated":bool(obj.get("nextPageToken")),"matches":candidates[:12]}
 except Exception as ex:return {"state":"ERROR","query":drug,"error":type(ex).__name__+":"+str(ex)[:150],"matches":[]}
def run(workers):
 data=json.loads(SOURCE.read_text());targets=data["trials"]
 if len(targets)!=253 or len({x["nctId"] for x in targets})!=253:raise ValueError("SOURCE_ROSTER_MISMATCH")
 found={}
 with cf.ThreadPoolExecutor(max_workers=workers) as pool:
  for n,res in pool.map(fetch_target,targets):found[n]=res
 query_by_key={};links={}
 for row in targets:
  n=row["nctId"];q=key_for(found[n])
  if q:
   k=(dn(q[0]),tuple(sorted(norm(x) for x in q[1])))
   query_by_key.setdefault(k,q);links[n]=k
 results_by_key={}
 with cf.ThreadPoolExecutor(max_workers=min(5,workers)) as pool:
  futures={pool.submit(fetch_prior,q):k for k,q in query_by_key.items()}
  for future in cf.as_completed(futures):results_by_key[futures[future]]=future.result()
 output=[]
 for t in targets:
  n=t["nctId"];v={"nctId":n,"ticker":t["ticker"],**found[n]}
  matched=results_by_key.get(links.get(n))
  if matched:
   past=[]
   for p in matched["matches"]:
    if p["nctId"]==n:continue
    start=v.get("registry",{}).get("firstPosted","")
    if p["firstPosted"] and start and p["firstPosted"]>start:continue
    if p["resultsFirstPosted"] and p["resultsFirstPosted"]>"2026-11-05":
     p={**p,"registeredResults":None,"hasResults":False,"afterCutoffExcluded":True}
    past.append(p)
   v["priorPhase2"]={"state":matched["state"],"query":matched["query"],"truncated":matched.get("truncated",False),"matches":past}
  else:v["priorPhase2"]={"state":"NO_UNAMBIGUOUS_SAME_DRUG_QUERY","matches":[]}
  output.append(v)
 def hasp(v):
  for p in v["priorPhase2"]["matches"]:
   for e in (p.get("registeredResults") or {}).get("primary") or []:
    if any(a.get("pValue") not in (None,"") for a in e["analyses"]):return True
  return False
 count={"candidates":253,"officialRegistryRecords":sum(x["sourceState"]=="FETCHED" for x in output),
  "errors":sum(x["sourceState"]=="ERROR" for x in output),
  "registryPostedResults":sum(x.get("registry",{}).get("hasResults",False) for x in output),
  "priorStudyQueries":len(query_by_key),
  "sameDrugSameConditionPhase2Leads":sum(bool(x["priorPhase2"]["matches"]) for x in output),
  "matchedPhase2ResultsPosted":sum(any(p.get("registeredResults") for p in x["priorPhase2"]["matches"]) for x in output),
  "matchedPhase2PrimaryPValues":sum(hasp(x) for x in output)}
 result={"schemaVersion":1,"scope":"SOURCE_ONLY_PHASE3_AND_STRICT_SAME_DRUG_SAME_CONDITION_PHASE2",
  "asOf":datetime.now(timezone.utc).isoformat(),"sourceCutoff":"2026-11-05",
  "limitations":"Issuer readout absence not established. Phase 2 source links are conservative exact-drug exact-condition research leads, not verified drug-indication clinical efficacy, patient-population similarity or FDA probabilities. Registered data are not full medical literature. Never infer statistical significance or treatment benefit from p-values alone.",
  "counts":count,"records":output}
 if len(output)!=253 or len({v["nctId"] for v in output})!=253:raise ValueError("OUTPUT_COHORT_MISMATCH")
 OUTPUT.parent.mkdir(parents=True,exist_ok=True)
 OUTPUT.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n")
 print(json.dumps(count,indent=2),flush=True)
 return 0 if count["officialRegistryRecords"] else 1
if __name__=="__main__":
 arg=argparse.ArgumentParser();arg.add_argument("--workers",type=int,default=6)
 opts=arg.parse_args();raise SystemExit(run(opts.workers))
