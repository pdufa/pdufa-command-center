"""Verify ABTECT source-reported remission and discontinuation provenance."""
import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
RELEASE="https://ir.abivax.com/news-releases/news-release-details/abivax-announces-positive-phase-3-results-both-abtect-8-week/"
EXPECT={
"NCT05507203":{"50mg":69,"placebo":4,"control":158,"active":318,
 "adjusted":"19.3","discontinued":"17/318 (5.3%)","placeboDiscontinued":"6/158 (3.8%)"},
"NCT05507216":{"50mg":63,"placebo":10,"control":159,"active":318,
 "adjusted":"13.4","discontinued":"15/318 (4.7%)","placeboDiscontinued":"9/159 (5.7%)"},
}
class AbtectPrimarySourceReviews(unittest.TestCase):
 def test_two_trial_source_receipts(self):
  d=json.loads(FEED.read_text(encoding="utf8"))
  records={r["nctId"]:r for r in d["records"]}
  for nct,expected in EXPECT.items():
   self.assertIn(nct,records)
   rec=records[nct]
   self.assertEqual(rec["ticker"],"ABVX")
   self.assertEqual(rec["drug"],"ABX464")
   self.assertEqual(rec["indication"],"Ulcerative Colitis")
   self.assertEqual(set(rec["facts"]),{"responseRemission","discontinuation"})
   self.assertEqual(rec["advantages"],[])
   registry=json.loads((PACKETS/(nct+".json")).read_text(encoding="utf8"))["registry"]
   groups=registry["reportedOutcomeMeasures"][0]
   self.assertIn("Clinical Remission",groups["title"])
   self.assertEqual(groups["timeFrame"],"8 weeks")
   numeric={str(x["groupId"]):int(x["value"]) for x in groups["measurements"]}
   self.assertEqual(numeric["OG000"],expected["50mg"])
   self.assertEqual(numeric["OG002"],expected["placebo"])
   ae={x["title"]:x for x in registry["adverseEventGroups"]}
   self.assertEqual(ae["ABX464 50mg"]["seriousAtRisk"],expected["active"])
   self.assertEqual(ae["Placebo"]["seriousAtRisk"],expected["control"])
   for key,fact in rec["facts"].items():
    self.assertEqual(fact["status"],"VERIFIED")
    self.assertEqual(fact["confidence"],"MODERATE")
    self.assertEqual(fact["sourceUrl"],RELEASE)
    self.assertEqual(fact["sourceDate"],"2025-07-22")
    self.assertIn(nct,fact["method"])
    self.assertNotIn("raasScore",fact)
   self.assertIn(expected["adjusted"],rec["facts"]["responseRemission"]["value"])
   self.assertIn(f'{expected["50mg"]}/{expected["active"]}',rec["facts"]["responseRemission"]["value"])
   self.assertIn(f'{expected["placebo"]}/{expected["control"]}',rec["facts"]["responseRemission"]["value"])
   self.assertIn(expected["discontinued"],rec["facts"]["discontinuation"]["value"])
   self.assertIn(expected["placeboDiscontinued"],rec["facts"]["discontinuation"]["value"])
   self.assertIn("not a causal",rec["facts"]["discontinuation"]["value"])
 def test_non_abvx_records_not_deleted(self):
  recs=json.loads(FEED.read_text())["records"]
  self.assertGreaterEqual(len(recs),10)
  self.assertEqual(len(recs),len({x["nctId"] for x in recs}))
  self.assertTrue({"ACHV","CYTK","CORT","APMD","SVRA"}<=
    {x["ticker"] for x in recs})

if __name__=="__main__":
 unittest.main()
