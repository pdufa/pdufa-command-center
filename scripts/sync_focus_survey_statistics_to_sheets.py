#!/usr/bin/env python3
"""Only source-derived unreviewed statistics into a separate FOCUS auto tab."""
from __future__ import annotations
import json
from pathlib import Path
from sync_focus_survey_evidence_to_sheets import sync_tables

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/focus-survey"
NAME="FOCUS Survey Auto Statistics"
HEADERS=[
 ("NCT ID","nctId"),("Ticker","ticker"),("Observed Data Type","kind"),
 ("Endpoint Type","outcomeType"),("Outcome / Endpoint","endpoint"),
 ("Time Frame","timeFrame"),("Analysis Population","analysisPopulation"),
 ("Treatment Group","group"),("Source Observation","value"),
 ("Units","unit"),("Statistical Details (Original Fields)","parameters"),
 ("Official Trial URL","sourceUrl"),("Retrieved At","sourceAsOf"),
 ("Review Status","status"),("Caution","disclaimer")
]

def table():
 summary=json.loads((OUT/"statistical-coverage.json").read_text(encoding="utf-8"))
 document=json.loads((OUT/"statistical-evidence.json").read_text(encoding="utf-8"))
 values=document.get("observations",[])
 if summary.get("schemaVersion")!=1 or not 20<=summary.get("trials",0)<=100 or \
    summary.get("officialRegistryRetrieved")!=summary["trials"] or \
    summary.get("savedObservations")!=len(values):
  raise ValueError("FOCUS_STATS_SOURCE_INCOMPLETE_NO_SHEET_WRITE")
 valid_ids=set(json.loads((ROOT/"new-platform/frontend/data/p3PostDataActive.json").read_text())
               .get("records",[])[i]["nct"] for i in range(summary["trials"]))
 if any(x["nctId"] not in valid_ids or \
        x["sourceUrl"]!="https://clinicaltrials.gov/study/"+x["nctId"] or \
        x["status"]!="REGISTRY_SOURCE_RETRIEVED_REVIEW_REQUIRED"
        for x in values):
  raise ValueError("SOURCE_IDENTITY_OR_REVIEW_STATUS_INVALID")
 out=[]
 for row in values:
  out.append([
   json.dumps(row.get(field),sort_keys=True,ensure_ascii=False)
    if isinstance(row.get(field),(dict,list)) else
   (row.get(field) if row.get(field) is not None else "")
   for _,field in HEADERS])
 return [(NAME,[k for k,_ in HEADERS],out)]

if __name__=="__main__":
 print(json.dumps(sync_tables(table()),sort_keys=True))
