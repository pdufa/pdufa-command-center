#!/usr/bin/env python3
"""Protected Google Sheets sync of *research leads*, never approved indications."""
from __future__ import annotations
import json
from pathlib import Path
from sync_focus_survey_evidence_to_sheets import sync_tables
from collect_focus_additional_indications import STATUS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/focus-survey"
LEADS="FOCUS Survey Auto Indication Leads"
STATUS_TAB="FOCUS Survey Auto Indication Coverage"
FIELDS=[
 ("FOCUS NCT","sourceFocusNct"),("Ticker","ticker"),("Company","company"),
 ("Drug Candidate","drugCandidate"),("FOCUS Registered Conditions","registeredSourceConditions"),
 ("Other Trial NCT","otherNct"),("Other Trial Condition Candidates","otherConditions"),
 ("Other Trial Phase","otherPhases"),("Other Trial Registry Status","otherTrialStatus"),
 ("Other Trial Sponsor","otherTrialSponsor"),("Registered Other-Trial Intervention","registeredIntervention"),
 ("Exact Other Trial URL","sourceUrl"),("Other Trial Updated","sourceLastUpdated"),
 ("Registry Search Truncated","searchTruncated"),("Evidence Status","evidenceStatus"),
 ("Required Validation","nextStep"),("Possible Indication Synonym Warning","warning")
]
COVERAGE=[
 ("FOCUS NCT","nctId"),("Ticker","ticker"),("Active Drug Candidate","drugCandidate"),
 ("Research Search Status","searchStatus"),("Candidate Trial Count","candidateOtherIndicationTrials"),
 ("Search Truncated","searchTruncated"),("Registry Search Result Count","searchResultCount"),
 ("Note","sourceNote")
]
def rows(cols,data):
 return [[("; ".join(map(str,v)) if isinstance(v,list) else
            (v if v is not None else "")) for _,k in cols for v in [obj.get(k)]]
             for obj in data]
def tables():
 research=json.loads((OUT/"additional-indication-research.json").read_text(encoding="utf-8"))
 summary=json.loads((OUT/"additional-indication-coverage.json").read_text(encoding="utf-8"))
 lead=research.get("candidates",[])
 coverage=research.get("byTrial",[])
 if research.get("schemaVersion")!=1 or summary.get("schemaVersion")!=1 or \
    not 20<=summary.get("focusTrials",0)<=100 or \
    len(coverage)!=summary["focusTrials"] or \
    len(lead)!=summary["candidateOtherIndicationLinks"] or \
    len({x["nctId"] for x in coverage})!=len(coverage):
  raise ValueError("INVALID_ADDITIONAL_INDICATION_RESEARCH_UNIVERSE")
 ids={x["nctId"] for x in coverage}
 if any(x.get("sourceFocusNct") not in ids or
        x.get("evidenceStatus")!=STATUS or
        x.get("sourceUrl")!="https://clinicaltrials.gov/study/"+x.get("otherNct","") or
        x.get("sourceFocusNct")==x.get("otherNct")
        for x in lead):
  raise ValueError("UNTRUSTED_ADDITIONAL_INDICATION_ROW")
 return [(LEADS,[x[0] for x in FIELDS],rows(FIELDS,lead)),
         (STATUS_TAB,[x[0] for x in COVERAGE],rows(COVERAGE,coverage))]
if __name__=="__main__":
 print(json.dumps(sync_tables(tables()),sort_keys=True))
