#!/usr/bin/env python3
"""Google Sheet evidence-discovery links, never an accepted Phase 3 survey grade."""
from __future__ import annotations
import json
from pathlib import Path
from sync_focus_survey_evidence_to_sheets import sync_tables
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/focus-survey"
TITLE="FOCUS Survey Auto Company Results"
COLUMNS=[("NCT ID","nctId"),("Ticker","ticker"),("Issuer","issuer"),
  ("Official Issuer Source Link","url"),("Release Title / Program","sourceTitle"),
  ("Source Publication Date (Discovery)","expectedPublicationDate"),
  ("Retrieval / Review Status","status"),("Evidence Match Strength","sourceMatch"),
  ("Possible Survey Ingredients (UNREVIEWED)","ingredientCandidates"),
  ("Fetched Text SHA256","sourceHash"),("Source Access Error / Next Action","error")]

def prepare():
    report=json.loads((OUT/"company-direct-source-summary.json").read_text(encoding="utf8"))
    doc=json.loads((OUT/"company-direct-source-ledger.json").read_text(encoding="utf8"))
    rows=doc.get("rows",[])
    if doc.get("schemaVersion")!=1 or report.get("schemaVersion")!=1 or \
       report.get("trials")!=29 or report.get("selectedLinks")!=29 or \
       len(rows)!=report.get("ledgerRows") or len({r["nctId"] for r in rows})!=29:
        raise ValueError("DIRECT_COMPANY_SOURCE_INCOMPLETE")
    if len({(r["nctId"],r["url"]) for r in rows})!=len(rows) or \
       any(x.get("status") not in (
           "SOURCE_CAPTURED_NEEDS_REVIEW","SOURCE_LINK_ONLY_CONTENT_UNAVAILABLE",
           "NO_DIRECT_ISSUER_RELEASE_INDEXED") for x in rows):
        raise ValueError("DIRECT_COMPANY_SOURCE_STATUS_INVALID")
    data=[]
    for r in rows:
        data.append(["; ".join(r.get(field,[])) if isinstance(r.get(field),list) else
                     (r.get(field) if r.get(field) is not None else "")
                     for _,field in COLUMNS])
    return [(TITLE,[h for h,_ in COLUMNS],data)]

if __name__=="__main__":
    print(json.dumps(sync_tables(prepare()),sort_keys=True))
