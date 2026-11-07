"""Validate source-reviewed PEAK and ORIGIN 3 report facts against exact NCTs."""
from __future__ import annotations
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
REQUIRED={
 "NCT05208047":{
  "ticker":"COGT","drug":"CGT9486",
  "indication":"Advanced Gastrointestinal Stromal Tumors",
  "source":"https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-reports-positive-results-bezuclastinib-peak",
  "date":"2025-11-10","facts":("clinicalBenefit","magnitude","headToHead"),
  "phrases":("16.5","9.2","0.50","0.39","0.65","46%","26%")
 },
 "NCT04716231":{
  "ticker":"VERA","drug":"Atacicept",
  "indication":"IgA Nephropathy",
  "source":"https://veratherapeutics.gcs-web.com/news-releases/news-release-details/vera-therapeutics-announces-trutaknatm-atacicept-vymj-stabilized",
  "date":"2026-09-15","facts":("clinicalBenefit","magnitude"),
  "phrases":("5.6","3.7","7.5","5.0","3.6","6.5","0.24","0.12","0.48")
 }
}
class SourceReviewedTrials(unittest.TestCase):
 def test_exact_identity_and_source_parameters(self):
  records=json.loads(FEED.read_text())["records"]
  by={r["nctId"]:r for r in records}
  roster={r["nct"]:r for r in json.loads(ROSTER.read_text())["records"]}
  self.assertEqual(len(by),len(records))
  for nct,expected in REQUIRED.items():
   self.assertIn(nct,by)
   self.assertIn(nct,roster)
   r=by[nct]
   self.assertEqual((r["ticker"],r["drug"],r["indication"]),
     (expected["ticker"],expected["drug"],expected["indication"]))
   self.assertEqual(roster[nct]["ticker"],expected["ticker"])
   pack=json.loads((PACKETS/(nct+".json")).read_text())
   self.assertEqual(pack["nctId"],nct)
   self.assertEqual(pack["ticker"],r["ticker"])
   self.assertIn(r["drug"].lower(),[s["name"].lower() for s in pack["registry"]["interventions"]])
   self.assertIn(r["indication"].lower(),[s.lower() for s in pack["registry"]["indications"]])
   self.assertEqual(set(r["facts"]),set(expected["facts"]))
   self.assertEqual(r["advantages"],[])
   for key,fact in r["facts"].items():
    self.assertEqual(fact["sourceUrl"],expected["source"])
    self.assertEqual(fact["sourceDate"],expected["date"])
    self.assertEqual(fact["status"],"VERIFIED")
    self.assertEqual(fact["confidence"],"MODERATE")
    self.assertLessEqual(len(fact["value"]),500)
    self.assertTrue(all(x in fact["value"] for x in expected["phrases"] if key!="headToHead"
                       or x in ("16.5","9.2","0.50","0.39","0.65")))
    self.assertIn("issuer",fact["method"].lower() if nct=="NCT05208047" else
                  fact["method"].lower().replace("company", "issuer"))
    self.assertIn(nct,fact["method"])
 def test_no_unreviewed_rating_escalation(self):
  by={r["nctId"]:r for r in json.loads(FEED.read_text())["records"]}
  for nct in REQUIRED:
   facts=by[nct]["facts"]
   for disallowed in ("survivalBenefit","safetyAdvantage","seriousAes",
                      "exclusivity","payerAccess","valuationImpact",
                      "shareholderRisk","peakAnnualSales"):
    self.assertNotIn(disallowed,facts)
   self.assertFalse(any("approvalProbability" in f for f in facts.values()))

if __name__=="__main__":
 unittest.main()
