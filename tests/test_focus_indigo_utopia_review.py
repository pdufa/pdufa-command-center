"""Maintain exact Phase 3 NCT / issuer / trial-type evidence protections."""
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
CASES={
 "NCT05662241":("ZBIO","Obexelimab","IgG4 Related Disease",{
  "clinicalBenefit":["0.44","0.277","0.711","73.2%","45.4%","0.0005"],
  "magnitude":["0.44","0.277","0.711","56%","0.0005"],
  "responseRemission":["37.1%","19.6%","17.5","0.0049"]},
  "https://investors.zenasbio.com/news-releases/news-release-details/zenas-biopharma-announces-data-registrational-phase-3-indigo","2026-06-02"),
 "NCT06331299":("URGN","UGN-103","Bladder Cancer",{
  "responseRemission":["77/99","77.8%","68.3","85.5","single-arm"],
  "durability":["94.5%","86.1","97.9","among patients"]},
  "https://www.sec.gov/Archives/edgar/data/1668243/000143774926034780/urgn20260930_10q.htm","2026-11-04")
}
class IndigoUtopiaReview(unittest.TestCase):
 def test_issuer_or_filing_source_values_are_program_specific(self):
  feed=json.loads(FEED.read_text(encoding="utf-8"))
  unique={r["nctId"]:r for r in feed["records"]}
  self.assertEqual(len(unique),len(feed["records"]))
  for nct,(ticker,drug,indication,expected,url,date) in CASES.items():
   with self.subTest(nct=nct):
    record=unique[nct]
    self.assertEqual((record["ticker"],record["drug"],record["indication"]),(ticker,drug,indication))
    self.assertEqual(set(record["facts"]),set(expected))
    self.assertEqual(record["advantages"],[])
    packet=json.loads((PACKETS/(nct+".json")).read_text(encoding="utf-8"))
    self.assertEqual(packet["nctId"],nct)
    self.assertEqual(packet["ticker"],ticker)
    self.assertIn(drug.lower(),[x["name"].lower() for x in packet["registry"]["interventions"]])
    self.assertIn(indication.lower(),[x.lower() for x in packet["registry"]["indications"]])
    for key,values in expected.items():
     fact=record["facts"][key]
     self.assertEqual(fact["status"],"VERIFIED")
     self.assertEqual(fact["sourceUrl"],url)
     self.assertEqual(fact["sourceDate"],date)
     self.assertTrue(len(fact["method"])>80)
     for marker in values:self.assertIn(marker,fact["value"],(nct,key,marker))
    self.assertNotIn("fdaProbability",record)
    self.assertNotIn("raasScore",record)
 def test_single_arm_urogen_no_false_comparator(self):
  rows=json.loads(FEED.read_text(encoding="utf-8"))["records"]
  r=next(x for x in rows if x["nctId"]=="NCT06331299")
  self.assertIn("single-arm",r["facts"]["responseRemission"]["value"])
  self.assertIn("No randomized concurrent comparator",r["facts"]["responseRemission"]["value"])
  self.assertIn("among patients achieving",r["facts"]["durability"]["value"])
  for key in ("headToHead","survivalBenefit","safetyAdvantage","valuationImpact"):
   self.assertNotIn(key,r["facts"])
 def test_indigo_flare_is_not_mortality(self):
  rows=json.loads(FEED.read_text(encoding="utf-8"))["records"]
  r=next(x for x in rows if x["nctId"]=="NCT05662241")
  self.assertIn("flare",r["facts"]["clinicalBenefit"]["value"])
  self.assertNotIn("survivalBenefit",r["facts"])
  self.assertNotIn("safetyAdvantage",r["facts"])

if __name__=="__main__":
 unittest.main()
