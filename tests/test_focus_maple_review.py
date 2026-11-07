"""Manual source-reviewed NCT05767346 Phase 3 comparison provenance.

This test validates exact identity, registry snapshot, endpoint analysis, and
published DOI cross-reference without creating new clinical claims or RAAS scores.
"""
import json
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect_focus_survey_evidence as survey

FEED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
STATS=ROOT/"reports/focus-survey/statistical-evidence.json"
PACKET=ROOT/"reports/focus-survey/source-packets/NCT05767346.json"
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"

class TestMAPLEReview(unittest.TestCase):
 def test_whole_feed_contains_no_scores_or_unknown_ingredients(self):
  feed=json.loads(FEED.read_text(encoding="utf-8"))
  catalog=json.loads(survey.CATALOG.read_text(encoding="utf-8"))
  valid={f["id"] for g in catalog["assessments"] for f in g["ingredients"]}
  self.assertEqual(feed["schemaVersion"],1)
  for r in feed["records"]:
   self.assertTrue(set(r["facts"])<=valid)
   self.assertEqual(r["advantages"],[])
   self.assertFalse(r.get("overallAdvantages"))
   for fact in r["facts"].values():
    self.assertEqual(fact["status"],"VERIFIED")
    self.assertIn(fact["confidence"],("HIGH","MODERATE","LOW"))
    self.assertTrue(fact["sourceUrl"].startswith("https://"))
    self.assertTrue(fact["sourceDate"] <= "2026-11-07")

 def test_maple_review_exact_match_from_both_sources(self):
  feed=json.loads(FEED.read_text(encoding="utf-8"))
  reviewed=[r for r in feed["records"] if r["nctId"]=="NCT05767346"]
  self.assertEqual(len(reviewed),1)
  record=reviewed[0]
  self.assertEqual(record["ticker"],"CYTK")
  self.assertEqual(record["drug"],"Aficamten")
  self.assertEqual(record["indication"],"Obstructive Hypertrophic Cardiomyopathy (oHCM)")
  self.assertEqual(set(record["facts"]),{"magnitude","clinicalBenefit","headToHead"})
  packet=json.loads(PACKET.read_text(encoding="utf-8"))
  stats=json.loads(STATS.read_text(encoding="utf-8"))
  roster=json.loads(ROSTER.read_text(encoding="utf-8"))
  row=next(r for r in roster["records"] if r["nct"]=="NCT05767346")
  self.assertIn("Aficamten",packet["registry"]["interventions"][0]["name"])
  primary=[x for x in stats["observations"]
    if x["nctId"]==row["nct"] and x["kind"]=="POSTED_STATISTICAL_ANALYSIS"
       and x["outcomeType"]=="PRIMARY"]
  self.assertEqual(len(primary),1)
  p=primary[0]["parameters"]
  self.assertEqual(p["paramValue"],"2.30")
  self.assertEqual(p["ciLowerLimit"],"1.52")
  self.assertEqual(p["ciUpperLimit"],"3.07")
  self.assertEqual(p["pValue"],"<0.0001")
  self.assertEqual(primary[0]["group"],"Aficamten versus Metoprolol")
  self.assertEqual(primary[0]["timeFrame"],"Baseline to Week 24")
  for ingredient,fact in record["facts"].items():
   witness=fact["sourceWitness"]
   self.assertEqual(witness["registrySourceHash"],packet["registrySourceHash"])
   self.assertEqual(witness["endpointTitle"],primary[0]["endpoint"])
   self.assertEqual(witness["observedValue"],p["paramValue"])
   self.assertEqual(witness["confidenceLower"],p["ciLowerLimit"])
   self.assertEqual(witness["confidenceUpper"],p["ciUpperLimit"])
   self.assertEqual(witness["groupIds"],p["groupIds"])
   self.assertEqual(witness["crossReference"],"https://pubmed.ncbi.nlm.nih.gov/40888697/")
   self.assertIsNotNone(survey.reviewed_fact([record],row,packet,ingredient))
  altered={**packet,"registrySourceHash":"0"*64}
  self.assertIsNone(survey.reviewed_fact([record],row,altered,"magnitude"))
  wrong_ind={**record,"indication":"Unrelated Cancer"}
  self.assertIsNone(survey.reviewed_fact([wrong_ind],row,packet,"magnitude"))
  wrong_drug={**record,"drug":"aficam"}
  self.assertIsNone(survey.reviewed_fact([wrong_drug],row,packet,"magnitude"))
  wrong_ticker={**record,"ticker":"OTHER"}
  self.assertIsNone(survey.reviewed_fact([wrong_ticker],row,packet,"magnitude"))

if __name__=="__main__":
 unittest.main()
