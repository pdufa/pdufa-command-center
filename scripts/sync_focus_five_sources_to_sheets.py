#!/usr/bin/env python3
"""Publish public-source leads to two new automation-owned review tabs.

This is NOT a survey answer write; the existing FOCUS/POOL/RAAS data,
reviewed facts, scores and prior six survey research tabs are unchanged.
"""
from __future__ import annotations
import json
from pathlib import Path
from sync_focus_survey_evidence_to_sheets import sync_tables

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/focus-survey"
LEADS_TITLE="FOCUS Survey Auto Multi Source"
SUMMARY_TITLE="FOCUS Survey Auto Five Sources"
LEAD_COLS=[
 ("NCT ID","nctId"),("Ticker","ticker"),("Issuer","company"),
 ("Public Source Type","sourceType"),("Source Match Strength","sourceMatch"),
 ("Candidate Ingredient IDs","ingredientCandidates"),("Source Title","sourceTitle"),
 ("Source URL","sourceUrl"),("Source Date","sourceDate"),
 ("Research Excerpt","excerpt"),("Registered Drug Candidates","candidateDrugs"),
 ("Registry Indications","registryIndications"),("Source Details","sourceDetails"),
 ("Review Status","status"),("Independently Reviewed","reviewed"),
 ("Source Limitation","notice"),
]
SUMMARY_HEADERS=["NCT ID","Ticker","ClinicalTrials.gov","Company Website",
 "FDA Search Results","Published Literature","SEC Document Pointers",
 "Strong Program Context Leads","Ingredient Candidates With Strong Leads",
 "Unverified Data Notice"]

def prep():
 doc=json.loads((OUT/"five-source-leads.json").read_text(encoding="utf8"))
 summary=json.loads((OUT/"five-source-summary.json").read_text(encoding="utf8"))
 rows=doc.get("records",[])
 per_trial=summary.get("perTrial",[])
 if summary.get("schemaVersion")!=1 or doc.get("schemaVersion")!=1 or \
    summary.get("focusTrials")!=29 or summary.get("surveyGroups")!=20 or \
    summary.get("surveyIngredients")!=38 or len(per_trial)!=29 or \
    len(rows)!=summary.get("newSourceLeads") or \
    len({x["nctId"] for x in per_trial})!=29:
    raise ValueError("FOCUS_FIVE_SOURCE_LEDGER_NOT_VALID")
 known={x["nctId"] for x in per_trial}
 if any(x.get("nctId") not in known or x.get("sourceType") not in
        ("COMPANY","REGISTRY","FDA","LITERATURE","SEC") or \
        x.get("status")!="SOURCE_CAPTURED_NEEDS_REVIEW" or \
        x.get("reviewed") is not False or \
        not x.get("sourceUrl","").startswith("https://")
        for x in rows):
    raise ValueError("FOCUS_SOURCE_OR_REVIEW_STATUS_NOT_VALID")
 # Safe maximum for Sheets changes even when a public API becomes noisy.
 if len(rows)>2800:
    raise ValueError("MULTI_SOURCE_REVIEW_QUEUE_EXCEEDS_BOUNDED_BATCH")
 lead_table=[]
 for r in rows:
    line=[]
    for _,k in LEAD_COLS:
        v=r.get(k)
        if isinstance(v,list):v="; ".join(str(x) for x in v)
        elif isinstance(v,dict):v=json.dumps(v,sort_keys=True,ensure_ascii=False)
        line.append(v if v is not None else "")
    lead_table.append(line)
 summary_table=[]
 for p in per_trial:
    c=p.get("sourceCounts",{})
    summary_table.append([
       p["nctId"],p["ticker"],"Recorded in official registry",
       c.get("COMPANY",0),c.get("FDA",0),c.get("LITERATURE",0),
       c.get("SEC",0),p.get("strongSourceContext",0),
       "; ".join(p.get("candidateIngredientIds",[])),
       "All non-registry source references are leads pending exact program verification",
    ])
 return [(LEADS_TITLE,[h for h,_ in LEAD_COLS],lead_table),
         (SUMMARY_TITLE,SUMMARY_HEADERS,summary_table)]

if __name__=="__main__":
 print(json.dumps(sync_tables(prep()),sort_keys=True))
