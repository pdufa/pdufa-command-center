"""Exact NCT/source constraints for two company-published Phase 3 HAE studies."""
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect_focus_survey_evidence as collector

FEED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
EXPECTED={
 "NCT06343779":{"ids":{"clinicalBenefit","timeToResponse"},
   "drug":"Deucrictibant","indication":"Hereditary Angioedema",
   "date":"2025-12-03","fragments":["1.28","12 hours","p<0.0001"]},
 "NCT06669754":{"ids":{"clinicalBenefit"},
   "drug":"Deucrictibant","indication":"Hereditary Angioedema (HAE)",
   "date":"2026-09-08","fragments":["83%","24 weeks","p<0.0001"]},
}
class PharvarisSourceChecks(unittest.TestCase):
 def test_only_exact_nct_issuer_results_are_promoted(self):
  feed=json.loads(FEED.read_text(encoding="utf8"))
  records={r["nctId"]:r for r in feed["records"]}
  self.assertEqual(len(records),len(feed["records"]))
  self.assertGreaterEqual(len(records),12)
  for nct,wanted in EXPECT.items():
   r=records[nct]
   self.assertEqual(r["ticker"],"PHVS")
   self.assertEqual(r["drug"],wanted["drug"])
   self.assertEqual(r["indication"],wanted["indication"])
   self.assertEqual(set(r["facts"]),wanted["ids"])
   self.assertFalse(r["advantages"])
   packet=json.loads((PACKETS/(nct+".json")).read_text(encoding="utf8"))
   reg=packet["registry"]
   self.assertEqual(packet["nctId"],nct)
   self.assertIn(wanted["indication"],reg["indications"])
   self.assertIn("deucrictibant"," ".join(x["name"] for x in reg["interventions"]).lower())
   self.assertEqual(reg["reportedOutcomeMeasures"],[])
   for key,f in r["facts"].items():
    self.assertEqual(f["sourceDate"],wanted["date"])
    self.assertTrue(f["sourceUrl"].startswith("https://ir.pharvaris.com/news-releases/"))
    self.assertEqual(f["status"],"VERIFIED")
    self.assertEqual(f["confidence"],"MODERATE")
    self.assertTrue(all(t in f["value"] for t in wanted["fragments"]))
    self.assertIn(nct,f["method"])
    match=collector.reviewed_fact([r],{"ticker":"PHVS"},packet,key)
    self.assertIsNotNone(match,("NCT rejection",nct,key))
    self.assertEqual(match["value"],f["value"])
 def test_no_issuer_ticker_only_or_placebo_identity(self):
  feed=json.loads(FEED.read_text(encoding="utf8"))
  r=next(x for x in feed["records"] if x["nctId"]=="NCT06343779")
  packet=json.loads((PACKETS/"NCT06343779.json").read_text(encoding="utf8"))
  self.assertIsNone(collector.reviewed_fact([r],{"ticker":"WRONG"},packet,"clinicalBenefit"))
  wrong={**r,"drug":"DeucrictibantXYZ"}
  self.assertIsNone(collector.reviewed_fact([wrong],{"ticker":"PHVS"},packet,"clinicalBenefit"))
  placebo={**r,"drug":"Placebo"}
  self.assertIsNone(collector.reviewed_fact([placebo],{"ticker":"PHVS"},packet,"clinicalBenefit"))
  study_b={**r,"nctId":"NCT00000001"}
  self.assertIsNone(collector.reviewed_fact([study_b],{"ticker":"PHVS"},packet,"nonexistent"))

if __name__=="__main__":
 unittest.main()
