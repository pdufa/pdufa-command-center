"""Offline SEC source facts: no invented rights, forecasts or currency conversions."""
from __future__ import annotations
import unittest
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect_focus_sec_financial_facts as sec
import sync_focus_sec_facts_to_sheets as sync

class TestFocusSec(unittest.TestCase):
 def test_roster_has_unique_ticker_cik_candidates(self):
  entries=sec.index()
  self.assertEqual(len(entries),len({x[0] for x in entries}))
  self.assertGreaterEqual(len(entries),15)
  self.assertLessEqual(len(entries),100)
  self.assertEqual(next(x[1]["cik"] for x in entries if x[0]=="ABVX"),"0001956827")
 def test_submissions_prove_issuer_ticker_not_product_ownership(self):
  example={"cik":1956827,"name":"Abivax S.A.","tickers":["ABVX"],
    "filings":{"recent":{"accessionNumber":["0001956827-26-000001"],
      "form":["20-F"],"filingDate":["2026-10-10"],
      "primaryDocument":["abvx2026.htm"]}}}
  filings=sec.parse_submissions(example,"0001956827","ABVX","2026-11-07")
  self.assertEqual(len(filings),1)
  self.assertTrue(filings[0]["url"].startswith("https://www.sec.gov/Archives/edgar/data/"))
  with self.assertRaisesRegex(ValueError,"SEC_ISSUER_TICKER"):
   sec.parse_submissions(example,"0001956827","WRONG","2026-11-07")
 def test_companyfacts_respects_asof_and_source_units(self):
  financial={"cik":1956827,"facts":{"us-gaap":{
     "CashAndCashEquivalentsAtCarryingValue":{"units":{"USD":[
        {"val":1000000,"end":"2026-06-30","filed":"2026-08-05",
         "form":"10-Q","accn":"0001956827-26-000001"},
        {"val":2000000,"end":"2026-09-30","filed":"2026-12-01",
         "form":"10-Q","accn":"0001956827-26-000002"}]}}}}}
  rows=sec.parse_companyfacts(financial,"0001956827","2026-11-07")
  cash=next(x for x in rows if x["metric"]=="Cash and cash equivalents")
  self.assertEqual(cash["value"],1000000)
  self.assertEqual(cash["periodEnd"],"2026-06-30")
  self.assertEqual(cash["unit"],"USD")
  self.assertEqual(cash["status"],"SEC_REPORTED_ISSUER_FACT_NEEDS_PROGRAM_RECONCILIATION")
  with self.assertRaisesRegex(ValueError,"SEC_COMPANYFACTS_CIK"):
   sec.parse_companyfacts(financial,"0000000001","2026-11-07")
 def test_issuer_financial_tabs_are_separate_and_bounded(self):
  roster=sec.index()
  issuers=[{"ticker":x[0],"cik":x[1]["cik"] if x[1] else "",
    "status":"SEC_SOURCE_UNAVAILABLE","facts":[],"filingLeads":[],
    "issuerRightsVerified":False} for x in roster]
  summary={"schemaVersion":1,"issuerCount":len(issuers),
    "financialFactRows":0,"filingDocumentLeads":0}
  tables=sync.tables({"schemaVersion":1,"issuers":issuers},summary)
  self.assertEqual(len(tables[0][1]),15)
  self.assertEqual(len(tables[0][2]),len(issuers))
  self.assertTrue(all(len(row)==15 for row in tables[0][2]))
  self.assertTrue(all(tab[0].startswith("FOCUS Survey Auto SEC")
                      for tab in tables))
  self.assertEqual({x[0] for x in tables},{"FOCUS Survey Auto SEC Facts",
                                           "FOCUS Survey Auto SEC Filings"})

if __name__=="__main__":
 unittest.main()
