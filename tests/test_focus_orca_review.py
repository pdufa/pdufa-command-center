"""Cross-validate manually reviewed ORCA-2/ORCA-3 exact Phase 3 findings.

Two distinct NCTs must remain separate. Week 3-6 primary abstinence odds ratios
and 95% confidence intervals must match saved exact ClinicalTrials.gov analyses.
"""
import json
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect_focus_survey_evidence as collector
FEED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
STATS=ROOT/"reports/focus-survey/statistical-evidence.json"
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"

class TestORCAReview(unittest.TestCase):
 def test_achv_both_trial_results_match_original_statistics(self):
  feed=json.loads(FEED.read_text(encoding="utf-8"))
  records={r["nctId"]:r for r in feed["records"]}
  stats=json.loads(STATS.read_text(encoding="utf-8"))["observations"]
  roster={r["nct"]:r for r in json.loads(ROSTER.read_text(encoding="utf-8"))["records"]}
  cases={
   "NCT04576949":("8.00","3.94","16.25"),
   "NCT05206370":("2.85","1.475","5.617"),
  }
  for nct,(val,lower,upper) in cases.items():
   with self.subTest(nct=nct):
    rec=records[nct]
    self.assertEqual(rec["ticker"],"ACHV")
    self.assertEqual(rec["drug"],"Cytisinicline")
    self.assertEqual(rec["indication"],"Smoking Cessation")
    self.assertEqual(set(rec["facts"]),{"clinicalBenefit","magnitude","responseRemission"})
    packet=json.loads((PACKETS/(nct+".json")).read_text(encoding="utf-8"))
    matched=[x for x in stats if x["nctId"]==nct and
       x["kind"]=="POSTED_STATISTICAL_ANALYSIS" and
       x["outcomeType"]=="PRIMARY" and
       x["endpoint"]=="Percentage of Participants With Smoking Abstinence From Weeks 3 to Week 6"
       and x["parameters"].get("paramType")=="Odds Ratio (OR)" and
       x["parameters"].get("paramValue")==val and
       x["parameters"].get("ciLowerLimit")==lower and
       x["parameters"].get("ciUpperLimit")==upper]
    self.assertEqual(len(matched),1)
    witness=rec["facts"]["magnitude"]["sourceWitness"]
    self.assertEqual(witness["registrySourceHash"],packet["registrySourceHash"])
    self.assertEqual(witness["groupIds"],matched[0]["parameters"]["groupIds"])
    self.assertEqual(witness["observedValue"],val)
    self.assertEqual(witness["confidenceLower"],lower)
    self.assertEqual(witness["confidenceUpper"],upper)
    self.assertIn("pubmed.ncbi.nlm.nih.gov" if nct=="NCT04576949"
                  else "pmc.ncbi.nlm.nih.gov",witness["crossReference"])
    for field in rec["facts"]:
     self.assertIsNotNone(collector.reviewed_fact([rec],roster[nct],packet,field))
    self.assertIsNone(collector.reviewed_fact([rec],roster[nct],
       {**packet,"registrySourceHash":"0"*64},"magnitude"))
    self.assertIsNone(collector.reviewed_fact([{**rec,"indication":"Wrong disease"}],
       roster[nct],packet,"magnitude"))
    self.assertIsNone(collector.reviewed_fact([rec,rec],roster[nct],packet,"magnitude"))

if __name__=="__main__":
 unittest.main()
