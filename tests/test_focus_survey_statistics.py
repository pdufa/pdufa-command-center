"""Source-only statistical extraction from full exact-NCT ClinicalTrials.gov records."""
import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect_focus_survey_statistics as stats

class TestStatistics(unittest.TestCase):
 def trial(self,nct="NCT12345678"):
  return {"protocolSection":{"identificationModule":{"nctId":nct}},
    "resultsSection":{"outcomeMeasuresModule":{"outcomeMeasures":[
      {"type":"PRIMARY","title":"Clinical remission","timeFrame":"8 weeks",
       "unitOfMeasure":"Participants","groups":[
         {"id":"OG000","title":"Study drug"},{"id":"OG001","title":"Placebo"}],
       "classes":[{"categories":[{"measurements":[
        {"groupId":"OG000","value":"69"},
        {"groupId":"OG001","value":"4"}]}]}],
       "denoms":[{"units":"Participants","counts":[
         {"groupId":"OG000","value":"300"},{"groupId":"OG001","value":"150"}]}],
       "analyses":[{"groupIds":["OG000","OG001"],"pValue":"0.001",
        "paramType":"Risk Difference","paramValue":"0.203","ciPctValue":"95",
        "ciLowerLimit":"0.16","ciUpperLimit":"0.25",
        "method":"Wald test"}]}]}}}
 def test_outcome_groups_statistical_analysis_and_denominators(self):
  rows=stats.extract("NCT12345678","EX",self.trial(),"2026-11-07T20:00:00Z")
  kinds={x["kind"] for x in rows}
  self.assertTrue({"REPORTED_GROUP_OUTCOME","ANALYSIS_DENOMINATOR",
                   "POSTED_STATISTICAL_ANALYSIS",
                   "ARITHMETIC_GROUP_DIFFERENCE_UNREVIEWED"}<=kinds)
  diff=next(x for x in rows if x["kind"]=="ARITHMETIC_GROUP_DIFFERENCE_UNREVIEWED")
  self.assertEqual(diff["value"],"65")
  self.assertTrue(diff["parameters"]["directionNotInterpreted"])
  analysis=next(x for x in rows if x["kind"]=="POSTED_STATISTICAL_ANALYSIS")
  self.assertEqual(analysis["parameters"]["pValue"],"0.001")
  self.assertEqual(analysis["parameters"]["ciLowerLimit"],"0.16")
  denoms=[x for x in rows if x["kind"]=="ANALYSIS_DENOMINATOR"]
  self.assertEqual(len(denoms),2)
  self.assertTrue(all(x["status"]=="REGISTRY_SOURCE_RETRIEVED_REVIEW_REQUIRED" for x in rows))
  self.assertTrue(all("not an independently reviewed" in x["disclaimer"].lower() for x in rows))
 def test_no_posted_results_returns_empty(self):
  self.assertEqual(stats.extract("NCT12345678","EX",{
     "protocolSection":{"identificationModule":{"nctId":"NCT12345678"}}},
     "2026-11-07T20:00:00Z"),[])
 def test_reject_other_trial(self):
  with self.assertRaisesRegex(ValueError,"FOCUS_REGISTRY_NCT_MISMATCH"):
   stats.extract("NCT87654321","EX",self.trial(),"2026-11-07T20:00:00Z")
 def test_no_subtraction_when_multiple_measurements_per_group(self):
  raw=self.trial()
  ms=raw["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]["classes"][0]["categories"][0]["measurements"]
  ms.append({"groupId":"OG000","value":"80"})
  rows=stats.extract("NCT12345678","EX",raw,"2026-11-07T20:00:00Z")
  self.assertFalse(any(x["kind"]=="ARITHMETIC_GROUP_DIFFERENCE_UNREVIEWED" for x in rows))

if __name__=="__main__":
 unittest.main()
