"""Only exact primary-statistic source-reviewed magnitude facts may be promoted."""
import json
import re
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
STATS=ROOT/"reports/focus-survey/statistical-evidence.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"
ALLOWED={"NCT05811247","NCT05813275","NCT04544293"}

class PrimaryFacts(unittest.TestCase):
 def test_three_independent_source_reviewed_magnitudes_only(self):
  source=json.loads(FEED.read_text())
  stats=json.loads(STATS.read_text())["observations"]
  roster={x["nct"]:x for x in json.loads(ROSTER.read_text())["records"]}
  records=source["records"]
  self.assertTrue(ALLOWED.issubset({r["nctId"] for r in records}))
  self.assertEqual(source["schemaVersion"],1)
  for record in records:
   if record["nctId"] not in ALLOWED:continue
   nct=record["nctId"]
   self.assertEqual(record["ticker"],roster[nct]["ticker"])
   self.assertEqual(list(record["facts"]),["magnitude"])
   self.assertEqual(record["advantages"],[])
   fact=record["facts"]["magnitude"]
   self.assertEqual(fact["status"],"VERIFIED")
   self.assertEqual(fact["sourceUrl"],"https://clinicaltrials.gov/study/"+nct)
   self.assertEqual(fact["confidence"],"MODERATE")
   self.assertIn("not",fact["method"].lower())
   packet=json.loads((PACKETS/(nct+".json")).read_text())
   self.assertEqual(packet["nctId"],nct)
   self.assertIn(record["drug"].lower(),
    [x["name"].lower() for x in packet["registry"]["interventions"]])
   self.assertIn(record["indication"].lower(),
    [x.lower() for x in packet["registry"]["indications"]])
   self.assertEqual(fact["sourceDate"],
     packet["registry"]["milestones"]["resultsFirstPostDateStruct"]["date"])
   primary=[x for x in stats if x["nctId"]==nct and
            x["kind"]=="POSTED_STATISTICAL_ANALYSIS" and
            x["outcomeType"]=="PRIMARY" and
            x["parameters"].get("paramValue") and
            x["parameters"].get("ciLowerLimit") and
            x["parameters"].get("ciUpperLimit") and
            x["parameters"].get("pValue")]
   self.assertTrue(primary,nct)
   evidence=next((x for x in primary if
     x["parameters"]["paramValue"] in fact["value"] and
     x["parameters"]["ciLowerLimit"] in fact["value"] and
     x["parameters"]["ciUpperLimit"] in fact["value"] and
     re.sub(r"\s+","",x["parameters"]["pValue"]).replace("<","<") in
       re.sub(r"\s+","",fact["value"])),None)
   self.assertIsNotNone(evidence,"Unmatched primary endpoint estimate for "+nct)
   self.assertEqual(evidence["sourceUrl"],fact["sourceUrl"])
 def test_no_survey_score_or_fda_probability_inserted(self):
  source=json.loads(FEED.read_text())
  for record in source["records"]:
   self.assertTrue(set(record["facts"]))
   self.assertFalse(record.get("overallAdvantages"))
   self.assertTrue(all(x not in record for x in
     ("raasScore","fdaProbability","numericalScore","approvalOdds")))

if __name__=="__main__":
 unittest.main()
