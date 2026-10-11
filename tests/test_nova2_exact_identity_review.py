"""Exact-NCT LBRX identity review and production score joins are fail closed."""
import json
import unittest
from datetime import date,datetime,timezone
from pathlib import Path

from pre_phase3_pilot_scores import reviewed_program_identity
from step7_live import build_snapshot


ROOT=Path(__file__).resolve().parents[1]
LEDGER=json.loads((ROOT/"data/pre_phase3_pilot_clinical_reviews.json").read_text())
LBRX=next(r for r in LEDGER["records"] if r["ticker"]=="LBRX")
NOVA2={
    "ticker":"LBRX",
    "nct_id":"NCT07363577",
    "sponsor":"LB Pharmaceuticals Inc.",
    "drug":"LB-102 (100 mg tablet) | LB-102 (50 mg tablet)",
    "indication":"Schizophrenia",
    "source_url":"https://clinicaltrials.gov/study/NCT07363577",
}


class ReviewedIdentityTests(unittest.TestCase):
    def test_exact_study_and_issuer_identity_review_is_source_limited(self):
        link=reviewed_program_identity(NOVA2,LBRX,date(2026,10,10))
        self.assertTrue(link.startswith("https://ir.lbpharma.us/"))
        self.assertIn("nova-2",link)
        self.assertFalse(reviewed_program_identity(NOVA2,LBRX,date(2026,3,25)))
        for col,value in (
            ("ticker","WRONG"), ("nct_id","NCT07369154"),
            ("drug","LB-102"), ("indication","Bipolar disorder"),
            ("sponsor","Other sponsor"),
            ("source_url","https://clinicaltrials.gov/study/NCT07369154"),
        ):
            tampered={**NOVA2,col:value}
            self.assertFalse(reviewed_program_identity(tampered,LBRX,date(2026,10,10)),col)

    def test_bad_or_future_identity_source_is_rejected(self):
        for field,value in (
            ("source_url","https://untrusted.invalid"),
            ("source_date","2026-10-10"),
            ("registry_url","https://clinicaltrials.gov/study/NCT07369154"),
            ("sponsor","Different Company"),
            ("status","REVIEW"),
        ):
            changed={**LBRX,"program_identity_review":{**LBRX["program_identity_review"],field:value}}
            self.assertFalse(reviewed_program_identity(NOVA2,changed,date(2026,10,10)),field)

    def test_prod_snapshot_scores_only_exact_nova2_and_expires(self):
        now=datetime(2026,10,11,5,30,tzinfo=timezone.utc)
        trials,_,_=build_snapshot(ROOT/"data",now=now)
        lbrx={x["NCT ID"]:x for x in trials if x["Ticker"]=="LBRX"}
        pivotal=lbrx["NCT07363577"]
        safety=lbrx["NCT07369154"]
        self.assertEqual(pivotal["Company/program identity"],"VERIFIED")
        self.assertIn("nova-2",pivotal["Company identity review source"])
        self.assertEqual(pivotal["Pre-readout research score /100"],72.0)
        self.assertEqual(pivotal["Score status"],"100-POINT RESEARCH SCORE — UNCALIBRATED")
        self.assertIn("NCT06179108 p=0.0009",pivotal["Linked Phase 2 PRIMARY p"])
        self.assertFalse(safety["Company identity review source"])
        self.assertIsNone(safety["Pre-readout research score /100"])
        self.assertIsNone(safety["Preliminary clinical score /100"])
        later,_,_=build_snapshot(ROOT/"data",now=datetime(2026,10,11,8,30,tzinfo=timezone.utc))
        pivotal_later=next(x for x in later if x["Ticker"]=="LBRX" and x["NCT ID"]=="NCT07363577")
        self.assertIsNone(pivotal_later["Pre-readout research score /100"],
                          "Issuer review from Oct 10 must expire in Pacific on Oct 11")


if __name__=="__main__":
    unittest.main()
