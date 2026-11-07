#!/usr/bin/env python3
"""Collect exact-NCT posted outcome tables, analyzed denominators and analyses.

These are PRIMARY-SOURCE OBSERVATIONS and unreviewed arithmetic, not efficacy,
noninferiority, safety advantage or FDA probabilities. The ClinicalTrials.gov
results module may be absent even when issuer Phase 3 readouts exist elsewhere.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from collections import Counter
import csv,json,re
from collect_focus_survey_evidence import request_json,load,fingerprint,utcnow

ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"
OUT=ROOT/"reports/focus-survey"
STATS=OUT/"statistical-evidence.json"
SUMMARY=OUT/"statistical-coverage.json"
NCT=re.compile(r"^NCT[0-9]{8}$")

def obj(value):
 return value if isinstance(value,dict) else {}
def arr(value):
 return value if isinstance(value,list) else []
def clean(value,maxlen=450):
 return " ".join(str(value or "").split())[:maxlen]
def num(value):
 try:
  f=float(str(value))
  if f==f and abs(f)<1e16:return f
 except (TypeError,ValueError,OverflowError):pass
 return None
def atomic(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_suffix(path.suffix+".tmp")
 tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
 tmp.replace(path)

def make_row(nct,ticker,source,as_of,kind,outcome,group="",value="",unit="",extra=None):
 return {"nctId":nct,"ticker":ticker,"kind":kind,
   "outcomeType":clean(outcome.get("type"),50),"endpoint":clean(outcome.get("title"),400),
   "timeFrame":clean(outcome.get("timeFrame"),100),
   "analysisPopulation":clean(outcome.get("populationDescription"),400),
   "group":clean(group,150),"value":clean(value,200),"unit":clean(unit,90),
   "parameters":extra or {},"sourceUrl":source,"sourceAsOf":as_of,
   "status":"REGISTRY_SOURCE_RETRIEVED_REVIEW_REQUIRED",
   "disclaimer":"Not an independently reviewed benefit/risk assessment."}

def extract(nct,ticker,data,retrieved):
 if obj(obj(data).get("protocolSection")).get("identificationModule",{}).get("nctId")!=nct:
  raise ValueError("FOCUS_REGISTRY_NCT_MISMATCH:"+nct)
 results=obj(obj(data).get("resultsSection"))
 outcomes=arr(obj(results.get("outcomeMeasuresModule")).get("outcomeMeasures"))
 source="https://clinicaltrials.gov/study/"+nct
 rows=[]
 for outcome in outcomes[:150]:
  o=obj(outcome)
  groups={str(g.get("id")):clean(g.get("title"),200) for g in arr(o.get("groups")) if isinstance(g,dict)}
  unit=o.get("unitOfMeasure")
  for cls in arr(o.get("classes")):
   c=obj(cls)
   for category in arr(c.get("categories")) or [{}]:
    cat=obj(category)
    measurements=arr(cat.get("measurements"))
    if not measurements:continue
    numeric={}
    for m in measurements:
     measurement=obj(m)
     gid=str(measurement.get("groupId",""))
     value=measurement.get("value")
     if value in (None,""):continue
     info={"groupId":gid,"groupName":groups.get(gid,gid),
         "classTitle":clean(c.get("title"),120),"categoryTitle":clean(cat.get("title"),120),
         "spread":clean(measurement.get("spread"),90),
         "upperLimit":clean(measurement.get("upperLimit"),90),
         "lowerLimit":clean(measurement.get("lowerLimit"),90)}
     rows.append(make_row(nct,ticker,source,retrieved,"REPORTED_GROUP_OUTCOME",
       o,groups.get(gid,gid),value,unit,info))
     numeric.setdefault(gid,[]).append(num(value))
    # Calculate strictly descriptive A-B for a *single* two-arm table.
    # Never compute a percent/benefit from counts without denominators.
    if len(groups)==2 and set(numeric)==set(groups) and \
       all(len(values)==1 and values[0] is not None for values in numeric.values()):
     ids=list(groups)
     delta=numeric[ids[0]][0]-numeric[ids[1]][0]
     rows.append(make_row(nct,ticker,source,retrieved,"ARITHMETIC_GROUP_DIFFERENCE_UNREVIEWED",
       o,groups[ids[0]]+" − "+groups[ids[1]],format(delta,".10g"),unit,
       {"groups":ids,"classTitle":clean(c.get("title"),120),
        "categoryTitle":clean(cat.get("title"),120),
        "calculation":"numeric value of first listed group minus second listed group",
        "directionNotInterpreted":True,"requiresComparatorValidation":True}))
  for den in arr(o.get("denoms")):
   d=obj(den)
   for count in arr(d.get("counts")):
    p=obj(count);gid=str(p.get("groupId",""))
    if p.get("value") in ("",None):continue
    rows.append(make_row(nct,ticker,source,retrieved,
      "ANALYSIS_DENOMINATOR",o,groups.get(gid,gid),p.get("value"),
      d.get("units"),{"groupId":gid}))
  for ana in arr(o.get("analyses")):
   a=obj(ana)
   selected=[groups.get(str(g),str(g)) for g in arr(a.get("groupIds"))]
   keys=("pValue","pValueComment","paramType","paramValue","ciNumSides",
        "ciPctValue","ciLowerLimit","ciUpperLimit","ciUpperLimitComment",
        "method","otherAnalysisDescription","statisticalAnalysisPlan",
        "groupDescription","dispersionType","dispersionValue",
        "nonInferiorityType","nonInferiorityMargin")
   info={k:a.get(k) for k in keys if a.get(k) is not None}
   if not info:continue
   info["groupIds"]=arr(a.get("groupIds"))
   rows.append(make_row(nct,ticker,source,retrieved,
      "POSTED_STATISTICAL_ANALYSIS",o," versus ".join(selected),
      a.get("paramValue") or a.get("pValue") or "see parameters",
      a.get("paramType") or "",info))
 flow=obj(results.get("participantFlowModule"))
 for period in arr(flow.get("periods")):
  p=obj(period)
  for milestone in arr(p.get("milestones")):
   m=obj(milestone)
   for achievement in arr(m.get("achievements")):
    ac=obj(achievement)
    if not re.search(r"withdraw|discontinu|complete|started|not complete",
       str(m.get("title","")),re.I):continue
    title={"type":"FLOW","title":str(m.get("title","")),"timeFrame":str(p.get("title",""))}
    rows.append(make_row(nct,ticker,source,retrieved,
      "PARTICIPANT_FLOW",title,str(ac.get("groupId","")),ac.get("numSubjects",""),
      "participants",{"groupId":ac.get("groupId"),"comment":ac.get("comment","")}))
 return rows

def collect_one(item):
 nct,ticker=item["nct"],item["ticker"]
 retrieved=utcnow()
 raw=request_json("https://clinicaltrials.gov/api/v2/studies/"+nct)
 rows=extract(nct,ticker,raw,retrieved)
 return {"nctId":nct,"ticker":ticker,"sourceHash":fingerprint(raw),
         "retrievedAt":retrieved,"rows":rows,"hasResultsSection":bool(raw.get("resultsSection"))}

def run():
 active=load(ROSTER).get("records",[])
 if not 20<=len(active)<=100 or len({x.get("nct") for x in active})!=len(active) or \
    any(not NCT.fullmatch(x.get("nct","")) for x in active):
  raise ValueError("FOCUS_ROSTER_INVALID")
 packets={}
 failed={}
 with ThreadPoolExecutor(max_workers=3) as pool:
  requests={pool.submit(collect_one,item):item for item in active}
  for future in as_completed(requests):
   r=requests[future]
   try:
    record=future.result()
    packets[r["nct"]]=record
   except Exception as e:
    failed[r["nct"]]=type(e).__name__+":"+clean(str(e),160)
 observations=[]
 for item in active:
  data=packets.get(item["nct"])
  if data:observations+=data["rows"]
 counts=Counter(x["kind"] for x in observations)
 report={"schemaVersion":1,"trials":len(active),
   "officialRegistryRetrieved":len(packets),"registryErrors":failed,
   "savedObservations":len(observations),
   "postedResultTrials":sum(v["hasResultsSection"] for v in packets.values()),
   "counts":dict(counts),
   "reviewedStatisticalFindings":0,
   "warning":"No extracted source statistics have been independently validated; A−B arithmetic is only a descriptive draft."}
 atomic(STATS,{"schemaVersion":1,"observations":observations})
 atomic(SUMMARY,report)
 headers=["nctId","ticker","kind","outcomeType","endpoint","timeFrame",
   "analysisPopulation","group","value","unit","parameters","sourceUrl",
   "sourceAsOf","status","disclaimer"]
 with (OUT/"statistical-evidence.csv").open("w",encoding="utf-8",newline="") as f:
  writer=csv.DictWriter(f,fieldnames=headers,extrasaction="ignore")
  writer.writeheader()
  for row in observations:
   item={**row,"parameters":json.dumps(row["parameters"],sort_keys=True,ensure_ascii=False)}
   writer.writerow(item)
 print(json.dumps({"trials":report["trials"],
  "retrieved":report["officialRegistryRetrieved"],
  "records":len(observations),"counts":dict(counts),"errors":len(failed)}))
 return report

if __name__=="__main__":
 run()
