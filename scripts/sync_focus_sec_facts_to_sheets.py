#!/usr/bin/env python3
"""Publish SEC source facts in separately owned FOCUS survey research tabs."""
from __future__ import annotations
import json
from pathlib import Path
from sync_focus_survey_evidence_to_sheets import sync_tables

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/focus-survey"
FACT_NAME="FOCUS Survey Auto SEC Facts"
FILING_NAME="FOCUS Survey Auto SEC Filings"
FACT_HEADER=["Ticker","CIK","SEC Issuer","Identity / Source Status",
 "Reported Financial Metric","Reported Value","Units","Financial Period End",
 "Period Start","Filing Date","Filing Form","Official Filing URL",
 "SEC Fact API","Status","Product Rights Verified"]
FILING_HEADER=["Ticker","CIK","SEC Issuer","Filing Type","Filing Date",
 "Official SEC Filing Document","Document Review Status","Product Rights Verified"]
def tables(payload=None,summary=None):
 if payload is None:
  payload=json.loads((OUT/"sec-companyfacts.json").read_text(encoding="utf-8"))
 if summary is None:
  summary=json.loads((OUT/"sec-companyfacts-summary.json").read_text(encoding="utf-8"))
 issuers=payload.get("issuers",[])
 if payload.get("schemaVersion")!=1 or summary.get("schemaVersion")!=1 or \
    not 10<=summary.get("issuerCount",0)<=100 or len(issuers)!=summary["issuerCount"] or \
    len({x["ticker"] for x in issuers})!=len(issuers):
  raise ValueError("SEC_REPORT_INCOMPLETE_OR_AMBIGUOUS")
 facts=[]
 filings=[]
 for issuer in issuers:
  base=[issuer["ticker"],issuer.get("cik",""),issuer.get("secCompanyName",""),
        issuer.get("status","")]
  if not issuer.get("facts"):
   facts.append(base+["No source-validated metric","","","","","","","","",
     issuer.get("sourceError") or issuer.get("factsError") or "NO_FINANCIAL_FACT_ACCEPTED",False])
  for f in issuer.get("facts",[]):
   facts.append(base+[
     f.get("metric",""),f.get("value",""),f.get("unit",""),
     f.get("periodEnd",""),f.get("periodStart",""),f.get("filed",""),
     f.get("form",""),f.get("filingUrl",""),f.get("sourceUrl",""),
     f.get("status",""),False])
  for f in issuer.get("filingLeads",[]):
   filings.append([issuer["ticker"],issuer.get("cik",""),
      issuer.get("secCompanyName",""),f.get("form",""),f.get("filed",""),
      f.get("url",""),f.get("status",""),False])
 # Fail if report claims more evidence than the rows we will display.
 if sum(len(x.get("facts",[])) for x in issuers)!=summary["financialFactRows"] or \
    len(filings)!=summary["filingDocumentLeads"]:
  raise ValueError("SEC_FACT_LEDGER_MISMATCH")
 return [(FACT_NAME,FACT_HEADER,facts),(FILING_NAME,FILING_HEADER,filings)]
if __name__=="__main__":
 print(json.dumps(sync_tables(tables()),sort_keys=True))
