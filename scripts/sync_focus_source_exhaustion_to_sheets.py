#!/usr/bin/env python3
"""Publish detailed source-route audits without modifying FOCUS survey answers."""
from __future__ import annotations
import json
from pathlib import Path
from sync_focus_survey_evidence_to_sheets import sync_tables
from audit_focus_source_exhaustion import ALL, OUT

NAME="FOCUS Survey Auto Source Audit"
SUMMARY_NAME="FOCUS Survey Auto Exhaustion"
HEADERS=[
 "NCT ID","Ticker","Survey #","Survey","Ingredient ID","Ingredient",
 "Original Evidence Status","Source Families Required","Source Families Attempted",
 "Company","ClinicalTrials.gov","FDA","Literature","SEC EDGAR",
 "NIH Epidemiology","Clinical Guidelines","CMS Payer","Patents / Exclusivity",
 "Blocked Families","Unsearched Families","Lead Families","Next Research Action",
 "Fallback Research Instructions","Research Exhausted","Verified Ingredient"
]
SUMMARY_HEADERS=["Metric","Value"]
def prepare():
 report=json.loads((OUT/"source-exhaustion-summary.json").read_text(encoding="utf-8"))
 data=json.loads((OUT/"source-exhaustion-audit.json").read_text(encoding="utf-8"))
 items=data.get("records",[])
 if report.get("schemaVersion")!=1 or data.get("schemaVersion")!=1 or \
    report.get("trials")!=29 or report.get("surveys")!=20 or \
    report.get("ingredients")!=38 or report.get("surveySlots")!=1102 or \
    len(items)!=1102 or len({(x["nctId"],x["ingredientId"]) for x in items})!=1102:
  raise ValueError("EXHAUSTION_SOURCE_AUDIT_INCOMPLETE")
 if sum(len(x["requiredSourceFamilies"]) for x in items)!=report["sourceReceipts"] or \
    any(x["isResearchExhausted"] for x in items):
  raise ValueError("PREMATURE_EXHAUSTION_OR_RECEIPT_MISMATCH")
 rows=[]
 for item in items:
  receipts=item["sourceReceipts"]
  row=[
   item["nctId"],item["ticker"],item["surveyNumber"],item["surveyName"],
   item["ingredientId"],item["ingredientName"],item["evidenceStatus"],
   " | ".join(item["requiredSourceFamilies"]),item["sourcesAttempted"]
  ]
  row += [receipts.get(source,{}).get("status","NOT_REQUIRED") for source in ALL]
  row += [" | ".join(item["blockedFamilies"])," | ".join(item["unsearchedFamilies"]),
          " | ".join(item["evidenceLeadFamilies"]),item["nextAction"],
          " | ".join(item["suggestedFallbacks"]),False,item["isVerifiedIngredient"]]
  if len(row)!=len(HEADERS):
   raise ValueError("SOURCE_AUDIT_SHEET_COLUMN_MISMATCH")
  rows.append(row)
 summary=[["Trial roster",report["trials"]],["Surveys",report["surveys"]],
          ["Ingredients",report["ingredients"]],["Assessment slots",report["surveySlots"]],
          ["Required source-family checks",report["sourceReceipts"]],
          ["Source avenues attempted",report["sourceAttempts"]],
          ["Slots with blocked sources",report["blockedSourceSlots"]],
          ["Slots with unsearched sources",report["unsearchedSourceSlots"]],
          ["Slots with evidence leads",report["slotsWithEvidenceLeads"]],
          ["Verified ingredient inputs",report["verifiedIngredientInputs"]],
          ["Research proven exhausted",report["researchExhausted"]]]
 return [(NAME,HEADERS,rows),(SUMMARY_NAME,SUMMARY_HEADERS,summary)]
if __name__=="__main__":
 print(json.dumps(sync_tables(prepare()),sort_keys=True))
