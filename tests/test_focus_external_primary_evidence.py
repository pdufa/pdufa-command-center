"""Source-review constraints for RINGSIDE and ACACIA-HCM program-only facts.

This test verifies the saved facts against source-reviewed primary-publication
and issuer-report numbers; it does not replace independent clinical interpretation.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
TARGETS={
 "NCT04871282":{
  "ticker":"IMNM","drug":"AL102","indication":"Desmoid Tumor",
  "url":"https://investors.immunome.com/immunome-announces-detailed-phase-3-ringside-data-for-varegacestat-in-adults-with-progressing-desmoid-tumors-at-the-2026-asco-annual-meeting/",
  "date":"2026-05-30",
  "expected":{"clinicalBenefit":["0.16","0.071","0.375","56%","9%","−2.42"],
              "magnitude":["0.16","0.071","0.375","56%","9%"]},
 },
 "NCT06081894":{
  "ticker":"CYTK","drug":"Aficamten",
  "indication":"Symptomatic Non-Obstructive Hypertrophic Cardiomyopathy",
  "url":"https://pubmed.ncbi.nlm.nih.gov/42663312/",
  "date":"2026-08-28",
  "expected":{"clinicalBenefit":["0.67","0.22","1.11","3.0","0.5","5.5","10.5%","0.8%","20.2%","14.7%"],
              "magnitude":["0.67","0.22","1.11","3.0","0.5","5.5"]},
 }
}
class TestExternalPrimaryFacts(unittest.TestCase):
 def test_exact_nct_drug_indication_source_and_approved_values(self):
  feed=json.loads(FEED.read_text(encoding="utf-8"))
  roster={r["nct"]:r for r in json.loads(ROSTER.read_text(encoding="utf-8"))["records"]}
  by_nct={r["nctId"]:r for r in feed["records"]}
  self.assertEqual(feed["schemaVersion"],1)
  self.assertEqual(len(set(by_nct)),len(feed["records"]))
  for nct,expect in TARGETS.items():
   self.assertIn(nct,roster)
   self.assertIn(nct,by_nct)
   r=by_nct[nct]
   self.assertEqual(r["ticker"],expect["ticker"])
   self.assertEqual(r["ticker"],roster[nct]["ticker"])
   self.assertEqual(r["drug"],expect["drug"])
   self.assertEqual(r["indication"],expect["indication"])
   self.assertTrue(set(expect["expected"]).issubset(set(r["facts"])))
   self.assertEqual(set(r["facts"])-set(expect["expected"]),
                    {"responseRemission"} if nct=="NCT04871282" else set())
   self.assertEqual(r.get("advantages"),[])
   if nct=="NCT04871282":
    response=r["facts"]["responseRemission"]
    self.assertEqual(response["status"],"VERIFIED")
    self.assertEqual(response["sourceDate"],"2026-10-26")
    self.assertEqual(response["sourceUrl"],"https://investors.immunome.com/immunome-presents-additional-clinical-data-for-varegacestat-in-desmoid-tumors-at-esmo-2026/")
    self.assertIn("56%",response["value"])
    self.assertIn("9%",response["value"])
    self.assertIn("NCT04871282",response["method"])

   packet=json.loads((PACKETS/(nct+".json")).read_text(encoding="utf-8"))
   reg=packet["registry"]
   self.assertEqual(packet["nctId"],nct)
   self.assertEqual(packet["ticker"],expect["ticker"])
   self.assertIn(expect["drug"].lower(),[x["name"].lower() for x in reg["interventions"]])
   self.assertIn(expect["indication"].lower(),[x.lower() for x in reg["indications"]])
   for ingredient,values in expect["expected"].items():
    f=r["facts"][ingredient]
    self.assertEqual(f["sourceUrl"],expect["url"])
    self.assertEqual(f["sourceDate"],expect["date"])
    self.assertEqual(f["status"],"VERIFIED")
    self.assertLessEqual(len(f["value"]),500)
    self.assertTrue(any(token in f["method"].lower() for token in
                        ("approval","regulator")))
    for val in values:
     self.assertIn(val,f["value"],nct+"/"+ingredient+" missing "+val)
    self.assertTrue("NCT" in f["method"] or "RINGSIDE" in f["method"])
    self.assertNotIn("Approval Probability",f["value"])
    self.assertNotIn("RAAS score",f["value"])
 def test_no_fabricated_survival_or_safety_advantage_rating(self):
  by_nct={r["nctId"]:r for r in json.loads(FEED.read_text())["records"]}
  for nct in TARGETS:
   facts=by_nct[nct]["facts"]
   self.assertNotIn("survivalBenefit",facts)
   self.assertNotIn("seriousAes",facts)
   self.assertNotIn("qualityOfLife",facts)
   self.assertNotIn("shareholderRisk",facts)
   self.assertNotIn("valuationImpact",facts)
   self.assertNotIn("peakAnnualSales",facts)

if __name__=="__main__":
 unittest.main()
