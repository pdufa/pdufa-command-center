#!/usr/bin/env python3
"""Publish only unreviewed source-observation and bibliography triage queues.

Never overwrites the canonical FOCUS, POOL, taxonomy, RAAS, or existing
FOCUS Survey Auto Evidence/Auto Coverage/Auto Gaps/Auto Sources tables.
"""
from __future__ import annotations
import json
from pathlib import Path
from sync_focus_survey_evidence_to_sheets import sync_tables

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"reports/focus-survey"
REVIEW_NAME="FOCUS Survey Auto Review"
LITERATURE_NAME="FOCUS Survey Auto Literature"

REVIEW_COLUMNS=[
 ("NCT ID","nctId"),("Ticker","ticker"),("Company","company"),
 ("Source Type","sourceType"),("Observation Kind","observationKind"),
 ("Related Ingredient","relatedIngredient"),("Treatment Group","treatmentGroup"),
 ("Measure","measure"),("Observed Value","observedValue"),("Units","unit"),
 ("Time Frame","timeFrame"),("Context","context"),
 ("ClinicalTrials.gov URL","sourceUrl"),("Retrieved UTC","retrievedAt"),
 ("Source Fingerprint","sourceHash"),("Review Status","status"),
 ("Review Instruction","reviewNote")]
LITERATURE_COLUMNS=[
 ("NCT ID","nctId"),("Ticker","ticker"),("Company","company"),
 ("Publication Title","articleTitle"),("Source URL","url"),("DOI","doi"),
 ("Publication Date","publicationDate"),("Open Access","openAccess"),
 ("Source Match Type","matchClass"),("Matched Terms","matchedTerms"),
 ("Possible Surveys (Unverified)","suggestedSurveyNumbers"),
 ("Review Status","status"),("Review Instruction","reviewNote")]

def read_json(file):
    return json.loads(file.read_text(encoding="utf-8"))

def prepare_tables():
    summary=read_json(REPORT/"triage-summary.json")
    observations=read_json(REPORT/"review-queue.json").get("observations")
    literature=read_json(REPORT/"publication-triage.json").get("articles")
    if summary.get("surveyCategories")!=20 or summary.get("surveyIngredients")!=38:
        raise ValueError("SURVEY_TAXONOMY_INVALID")
    if not 20<=summary.get("trials",0)<=100 or summary["ingredientSlots"]!=38*summary["trials"]:
        raise ValueError("PARTIAL_FOCUS_COLLECTION")
    if not isinstance(observations,list) or not isinstance(literature,list):
        raise ValueError("REVIEW_QUEUE_UNAVAILABLE")
    if len(observations)!=summary["registryFactObservations"] or \
       len(literature)!=summary["distinctTrialPublicationLeads"]:
        raise ValueError("REVIEW_QUEUE_SUMMARY_MISMATCH")
    ncts={row["nctId"] for row in summary["perTrial"]}
    if len(ncts)!=summary["trials"] or \
       any(x["nctId"] not in ncts for x in observations+literature):
        raise ValueError("REVIEW_QUEUE_SOURCE_IDENTITY_MISMATCH")
    if any(x.get("status")!="SOURCE_OBSERVED_REVIEW_REQUIRED" or \
           x.get("sourceType")!="CLINICALTRIALS_GOV_REGISTRY" or \
           not x.get("sourceHash") or not x.get("sourceUrl","").startswith(
               "https://clinicaltrials.gov/study/"+x["nctId"])
           for x in observations):
        raise ValueError("REVIEW_QUEUE_PROVENANCE_INVALID")
    if any(x.get("status")!="PUBLICATION_RESEARCH_LEAD_NOT_VALIDATED" or \
           not x.get("url","").startswith("https://europepmc.org/article/") or \
           x.get("matchClass") not in (
               "EXACT_NCT_LEAD","DRUG_TITLE_LEAD",
               "INDICATION_CONTEXT_ONLY","UNLINKED_SEARCH_LEAD")
           for x in literature):
        raise ValueError("PUBLICATION_PROVENANCE_INVALID")
    def table(columns,rows):
        return [label for label,_ in columns],[
            [row.get(field) if row.get(field) is not None else "" for _,field in columns]
            for row in rows
        ]
    review_h,review_rows=table(REVIEW_COLUMNS,observations)
    literature_h,literature_rows=table(LITERATURE_COLUMNS,literature)
    return [(REVIEW_NAME,review_h,review_rows),(LITERATURE_NAME,literature_h,literature_rows)]

def main():
    tables=prepare_tables()
    result=sync_tables(tables)
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":
    main()
