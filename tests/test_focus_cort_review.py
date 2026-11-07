"""Check both CORT Phase 3 review conclusions, including null comparator outcome."""
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect_focus_survey_evidence as collector

FEED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
STATS=ROOT/"reports/focus-survey/statistical-evidence.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"

class TestRelacorilantReview(unittest.TestCase):
 def test_grace_responder_selection_and_gradient_null_primary(self):
  feed=json.loads(FEED.read_text(encoding="utf-8"))
  records={r["nctId"]:r for r in feed["records"]}
  stats=json.loads(STATS.read_text(encoding="utf-8"))["observations"]
  roster={r["nct"]:r for r in json.loads(ROSTER.read_text(encoding="utf-8"))["records"]}
  cases={
   "NCT03697109":{
      "fields":{"magnitude","clinicalBenefit","responseRemission"},
      "paramValue":"0.17","lower":"0.04","upper":"0.77","pValue":"0.0215",
      "word":"randomized-withdrawal",
      "title":"Number of Patients With Loss of Response With Respect to Hypertension During the RW Phase."},
   "NCT04308590":{
      "fields":{"magnitude"},"paramValue":"-2.67",
      "lower":"-9.096","upper":"3.766","pValue":"0.4160",
      "word":"NOT statistically significant","title":"Change in Average 24-hour SBP"},
  }
  for nct,expected in cases.items():
   with self.subTest(nct=nct):
    r=records[nct]
    self.assertEqual(r["ticker"],"CORT")
    self.assertEqual(r["drug"],"Relacorilant")
    self.assertEqual(set(r["facts"]),expected["fields"])
    packet=json.loads((PACKETS/(nct+".json")).read_text(encoding="utf-8"))
    found=[s for s in stats if s["nctId"]==nct and
           s["kind"]=="POSTED_STATISTICAL_ANALYSIS" and
           s["outcomeType"]=="PRIMARY" and
           s["endpoint"]==expected["title"] and
           s["parameters"].get("paramValue")==expected["paramValue"]]
    self.assertEqual(len(found),1)
    obs=found[0]
    self.assertEqual(obs["parameters"]["ciLowerLimit"],expected["lower"])
    self.assertEqual(obs["parameters"]["ciUpperLimit"],expected["upper"])
    self.assertEqual(obs["parameters"]["pValue"],expected["pValue"])
    for field,item in r["facts"].items():
     wit=item["sourceWitness"]
     self.assertEqual(wit["registrySourceHash"],packet["registrySourceHash"])
     self.assertEqual(wit["endpointTitle"],obs["endpoint"])
     self.assertEqual(wit["observedValue"],expected["paramValue"])
     self.assertEqual(wit["confidenceLower"],expected["lower"])
     self.assertEqual(wit["confidenceUpper"],expected["upper"])
     self.assertEqual(wit["groupIds"],obs["parameters"]["groupIds"])
     self.assertEqual(item["status"],"VERIFIED")
     self.assertIsNotNone(collector.reviewed_fact([r],roster[nct],packet,field))
    all_values=" ".join(item["value"] for item in r["facts"].values())
    self.assertIn(expected["word"],all_values)
    self.assertFalse(any(any(label in item for label in
                     ("raasScore","approvalOdds","numericalScore")) for item in r["facts"].values()))

if __name__=="__main__":
 unittest.main()
