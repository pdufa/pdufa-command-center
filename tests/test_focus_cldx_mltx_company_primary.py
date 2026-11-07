"""Cross-check company Phase 3 facts for exact CLDX and MoonLake NCTs.

Source verification is not a trial efficacy grade, FDA outcome, commercial
model, or RAAS probability. VELA-2's nonsignificant *primary* must be kept.
"""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
CASES={
 "NCT06445023":("CLDX","barzolvolimab","Chronic Spontaneous Urticaria",
    {"magnitude":["-20.2","-20.5","-10.7","0.00001"],
     "responseRemission":["42.4%","42.1%","9.3%","49.0%"]}),
 "NCT06455202":("CLDX","barzolvolimab","Chronic Spontaneous Urticaria",
    {"magnitude":["-20.2","-19.7","-11.4","0.00001"],
     "responseRemission":["45.7%","44.0%","12.6%","54.0%"]}),
 "NCT06411899":("MLTX","Sonelokimab","Hidradenitis Suppurativa",
    {"responseRemission":["VELA-1","17.5%","34.8%","0.001"]}),
 "NCT06411379":("MLTX","Sonelokimab","Hidradenitis Suppurativa",
    {"responseRemission":["VELA-2","25.6%","35.9%","0.053","0.033","DID NOT"]})
}
URL={
 "CLDX":"https://ir.celldex.com/news-releases/news-release-details/celldex-announces-positive-results-phase-3-embarq-csu1-and",
 "MLTX":"https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-immunotherapeutics-reports-week-16-results-vela-phase-3"
}
DATE={"CLDX":"2026-09-22","MLTX":"2025-09-28"}

class CompanyPrimarySources(unittest.TestCase):
 def test_cldx_moonlake_are_exact_trials_and_values_not_raas(self):
  data=json.loads(FEED.read_text(encoding="utf-8"))
  by={x["nctId"]:x for x in data["records"]}
  for nct,(ticker,drug,indication,facts) in CASES.items():
   with self.subTest(nct=nct):
    self.assertIn(nct,by)
    record=by[nct]
    self.assertEqual(record["ticker"],ticker)
    self.assertEqual(record["drug"],drug)
    self.assertEqual(record["indication"],indication)
    self.assertEqual(set(record["facts"]),set(facts))
    self.assertFalse(record["advantages"])
    packet=json.loads((PACKETS/(nct+".json")).read_text(encoding="utf-8"))
    self.assertEqual(packet["ticker"],ticker)
    self.assertEqual(packet["nctId"],nct)
    self.assertIn(drug.lower(),[i["name"].lower() for i in packet["registry"]["interventions"]])
    self.assertIn(indication.lower(),[i.lower() for i in packet["registry"]["indications"]])
    for ingredient,expected in facts.items():
     evidence=record["facts"][ingredient]
     self.assertEqual(evidence["status"],"VERIFIED")
     self.assertEqual(evidence["sourceUrl"],URL[ticker])
     self.assertEqual(evidence["sourceDate"],DATE[ticker])
     self.assertEqual(evidence["confidence"],"MODERATE")
     self.assertLessEqual(len(evidence["value"]),500)
     for numeric in expected:
      self.assertIn(numeric,evidence["value"])
    for key in ("raasScore","fdaProbability","approvalOdds","clinicalGrade"):
     self.assertNotIn(key,record)
 def test_vela2_primary_failure_visible_and_not_cherry_picked(self):
  rows=json.loads(FEED.read_text(encoding="utf-8"))["records"]
  data=next(x["facts"]["responseRemission"]["value"] for x in rows
            if x["nctId"]=="NCT06411379")
  self.assertIn("composite-strategy PRIMARY endpoint DID NOT reach significance",data)
  self.assertIn("p=0.053",data)
  self.assertIn("treatment-policy alternative",data.lower())
 def test_ringside_new_response_is_cited_separately(self):
  rows=json.loads(FEED.read_text(encoding="utf-8"))["records"]
  r=next(x for x in rows if x["nctId"]=="NCT04871282")
  self.assertEqual(r["drug"],"AL102")
  f=r["facts"]["responseRemission"]
  self.assertEqual(f["status"],"VERIFIED")
  self.assertEqual(f["sourceDate"],"2026-10-26")
  self.assertIn("56%",f["value"])
  self.assertIn("9%",f["value"])
  self.assertTrue(f["sourceUrl"].startswith("https://investors.immunome.com/"))
  self.assertIn("NCT04871282",f["method"])

if __name__=="__main__":
 unittest.main()
