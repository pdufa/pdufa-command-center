#!/usr/bin/env python3
"""Sync 100%-enumerated FOCUS research dispositions, NOT clinical survey results.

Only writes new automation-owned tabs; protects the existing FOCUS, original
20-survey definitions, raw data, RAAS and review queues.
"""
from __future__ import annotations
import json
from pathlib import Path
from sync_focus_survey_evidence_to_sheets import sync_tables

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"reports/focus-survey"
DATA_TABLE="FOCUS Survey Auto Resolution"
SUMMARY_TABLE="FOCUS Survey Auto Resolution Summary"
FIELDS=[
 ("NCT ID","nctId"),("Ticker","ticker"),("Company","company"),
 ("Survey #","surveyNumber"),("Survey Name","surveyName"),
 ("Ingredient ID","ingredientId"),("Ingredient Name","ingredientName"),
 ("Original Evidence Status","priorEvidenceStatus"),
 ("Research Disposition","researchDisposition"),
 ("Reviewed Value (if any)","reviewedAnswer"),
 ("Registry Indications","registryIndications"),
 ("Drug Candidates","drugCandidates"),
 ("Registry Field Pointers","supportingRegistryPointers"),
 ("Observed Facts","primaryObservationCount"),
 ("Relevant Publication Leads","publicationReviewLeads"),
 ("Next Research URL","recommendedSource"),
 ("Missing Evidence Requirement","missingEvidenceRequirement"),
 ("Next Evidence Research Step","nextEvidenceStep"),
 ("Needs Model Assumptions","requiresModelAssumptions"),
 ("Applicability","applicability"),
 ("Verified Survey Answer","isSurveyAnswerVerified"),
 ("Registry Evidence Fingerprint","sourcePacketHash")
]
SUMMARY=[
 ("Survey #","surveyNumber"),("Survey","survey"),("Slots","slots"),
 ("Source Context","sourceContext"),
 ("Registry Interpretation Required","sourceInterpretationRequired"),
 ("Independently Verified Answers","verified"),
 ("Additional Research Gaps","researchGaps")
]

def load(path):
 return json.loads(path.read_text(encoding="utf-8"))
def table(columns,items):
 headers=[name for name,_ in columns]
 rows=[]
 for x in items:
  record=[]
  for _,field in columns:
   v=x.get(field)
   record.append("; ".join(str(z) for z in v) if isinstance(v,list) else
                 (v if v is not None else ""))
  rows.append(record)
 return headers,rows

def prepare_tables():
 details=load(OUTPUT/"resolution-worklist.json")
 summary=load(OUTPUT/"resolution-summary.json")
 items=details.get("items",[])
 if details.get("schemaVersion")!=1 or summary.get("schemaVersion")!=1 or \
    summary.get("surveys")!=20 or summary.get("ingredients")!=38 or \
    not 20<=summary.get("trials",0)<=100 or \
    summary.get("slots")!=38*summary["trials"] or \
    len(items)!=summary["slots"] or summary["dispositionCount"]!=summary["slots"]:
  raise ValueError("FOCUS_DISPOSITION_AUDIT_FAILED")
 if len({(x["nctId"],x["ingredientId"]) for x in items})!=len(items) or \
    sum(bool(x["isSurveyAnswerVerified"]) for x in items)!=summary["verifiedSurveyAnswers"]:
  raise ValueError("FOCUS_DISPOSITION_IDENTITY_FAILED")
 if any(x.get("applicability")!="NOT_YET_ADJUDICATED" or \
       x.get("researchDisposition") not in
       ("REVIEWED_ANSWER_PRESENT","PRIMARY_SOURCE_INTERPRETATION_REQUIRED",
        "PUBLICATION_CONTENT_REVIEW_REQUIRED","MODELING_INPUTS_UNAVAILABLE",
        "ADDITIONAL_PRIMARY_RESEARCH_REQUIRED","EXTERNAL_PRIMARY_SOURCE_CONTENT_REVIEW_REQUIRED")
       for x in items):
  raise ValueError("REVIEW_STATUS_MUST_NOT_IMPLY_UNVERIFIED_COMPLETION")
 h1,r1=table(FIELDS,items)
 h2,r2=table(SUMMARY,summary["bySurvey"])
 return [(DATA_TABLE,h1,r1),(SUMMARY_TABLE,h2,r2)]

if __name__=="__main__":
 print(json.dumps(sync_tables(prepare_tables()),sort_keys=True))
