"""Verify exact-match intervention and optional indication search never implies approval."""
import unittest
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect_focus_additional_indications as ind
import sync_focus_additional_indications_to_sheets as sheet

def study(nct,drug,conditions):
 return {"protocolSection":{
   "identificationModule":{"nctId":nct},
   "armsInterventionsModule":{"interventions":[{"name":drug,"type":"DRUG"}]},
   "conditionsModule":{"conditions":conditions},
   "sponsorCollaboratorsModule":{"leadSponsor":{"name":"Sponsor"}},
   "statusModule":{"overallStatus":"RECRUITING"},
   "designModule":{"phases":["PHASE2"]}}}

class TestAdditionalIndications(unittest.TestCase):
 def test_active_drug_not_placebo_or_brand_substring(self):
  self.assertEqual(ind.primary_drug({"interventions":[
   {"name":"Placebo","type":"DRUG"},
   {"name":"Aficamten (CK-3773274) (5 mg, 10 mg, 15 mg and 20 mg)","type":"DRUG"}]}),
   "Aficamten")
  self.assertEqual(ind.primary_drug({"interventions":[
   {"name":"Placebo","type":"DRUG"},
   {"name":"Behavioral support","type":"BEHAVIORAL"}]}),None)
  self.assertFalse(ind.intervention_matches("AD109","AD1099"))
  self.assertTrue(ind.intervention_matches("AD109","AD109 2.5mg capsule"))
  self.assertFalse(ind.intervention_matches("Metoprolol","Placebo to match Metoprolol"))
 def test_exact_source_study_match(self):
  valid=study("NCT12345678","Aficamten",["Condition B"])
  result=ind.study_match("Aficamten",valid)
  self.assertEqual(result["nctId"],"NCT12345678")
  self.assertEqual(result["conditions"],["Condition B"])
  self.assertEqual(result["phase"],"PHASE2")
  self.assertEqual(result["overallStatus"],"RECRUITING")
  self.assertIsNone(ind.study_match("Aficamten",
    study("NCT12345678","Placebo",["Condition B"])))
  self.assertIsNone(ind.study_match("Aficamten",
    study("INVALID","Aficamten",["Condition B"])))
 def test_diff_conditions_are_candidates_only(self):
  roster=[{"nct":"NCT12345678","ticker":"TEST","company":"Company A"},
          {"nct":"NCT12345679","ticker":"TEST","company":"Company A"}]
  packets={
   "NCT12345678":{"registry":{"indications":["Condition A"],
             "interventions":[{"name":"Drug ABC","type":"DRUG"}]}},
   "NCT12345679":{"registry":{"indications":["Condition B"],
             "interventions":[{"name":"Drug ABC","type":"DRUG"}]}},
  }
  leads=[
   study("NCT12345678","Drug ABC",["Condition A"]),
   study("NCT12345679","Drug ABC",["Condition B"]),
   study("NCT12345680","Drug ABC",["Condition C"]),
   study("NCT12345681","Placebo",["Condition D"]),
  ]
  searches={"drug abc":{"studies":leads,"queryCount":len(leads),"scanTruncated":False}}
  results,coverage=ind.build_index(roster,packets,searches)
  self.assertEqual(len(coverage),2)
  self.assertEqual(len(results),4)
  self.assertTrue(all(x["evidenceStatus"]==ind.STATUS for x in results))
  self.assertTrue(all(not x["sourceFocusNct"]==x["otherNct"] for x in results))
  self.assertEqual({x["otherNct"] for x in results},{"NCT12345678","NCT12345679","NCT12345680"})
  summary={"schemaVersion":1,"focusTrials":2,"candidateOtherIndicationLinks":4}
  # Production requires >=20 distinct trials; pilot must be blocked from Sheets.
  with self.assertRaisesRegex(ValueError,"INVALID_ADDITIONAL_INDICATION_RESEARCH_UNIVERSE"):
   sheet.tables({"schemaVersion":1,"candidates":results,"byTrial":coverage},summary)
 def test_population_only_trials_are_not_new_therapeutic_indications(self):
  for phrase in ("Healthy Volunteers","Healthy Adults","Healthy Subjects",
                 "Health Volunteers","Healthy Male Volunteers","Normal Healthy Volunteers"):
   self.assertTrue(ind.population_only_condition(phrase),phrase)
  self.assertFalse(ind.population_only_condition("Rheumatoid Arthritis"))
  self.assertFalse(ind.population_only_condition("Obstructive Sleep Apnea"))
  self.assertEqual(ind.canonical_condition("OSA"),"obstructive sleep apnea")
  self.assertEqual(ind.canonical_condition("Hereditary Angioedema Type II"),
                   "hereditary angioedema type ii")
  roster=[{"nct":"NCT12345678","ticker":"TEST","company":"Company A"}]
  packets={"NCT12345678":{"registry":{"indications":["OSA"],
             "interventions":[{"name":"AD109","type":"DRUG"}]}}}
  sample=[
    study("NCT12345679","AD109",["Healthy Volunteers"]),
    study("NCT12345680","AD109",["Obstructive Sleep Apnea"]),
    study("NCT12345681","AD109",["Rheumatoid Arthritis"]),
  ]
  found,coverage=ind.build_index(roster,packets,{
   "ad109":{"studies":sample,"queryCount":len(sample),"scanTruncated":False}})
  self.assertEqual(len(found),1)
  self.assertEqual(found[0]["otherNct"],"NCT12345681")
  self.assertEqual(coverage[0]["candidateOtherIndicationTrials"],1)
 def test_source_unavailable_not_conflated_with_no_trials(self):
  roster=[{"nct":"NCT12345678","ticker":"TEST","company":"Company A"}]
  packets={"NCT12345678":{"registry":{"indications":["Condition A"],
             "interventions":[{"name":"Drug ABC","type":"DRUG"}]}}}
  leads,coverage=ind.build_index(roster,packets,{"drug abc":{"error":"HTTP 503"}})
  self.assertEqual(len(leads),0)
  self.assertEqual(coverage[0]["searchStatus"],"SEARCH_UNAVAILABLE")

if __name__=="__main__":
 unittest.main()
