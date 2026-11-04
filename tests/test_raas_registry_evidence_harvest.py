"""Coverage and evidence-provenance tests for RAAS registry collection."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("harvest",ROOT/"scripts/raas_registry_evidence_harvest.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def study(nct="NCT06445023",posted=False):
    d={"protocolSection":{
        "identificationModule":{"nctId":nct,"briefTitle":"Phase 3 randomized trial"},
        "statusModule":{"overallStatus":"COMPLETED",
          "lastUpdatePostDateStruct":{"date":"2026-09-28"}},
        "sponsorCollaboratorsModule":{"leadSponsor":{"name":"Independent Sponsor"}},
        "designModule":{"phases":["PHASE3"],"studyType":"INTERVENTIONAL",
          "designInfo":{"allocation":"RANDOMIZED","interventionModel":"PARALLEL",
            "maskingInfo":{"masking":"QUADRUPLE"}},
          "enrollmentInfo":{"type":"ESTIMATED","count":420}},
        "conditionsModule":{"conditions":["Chronic Spontaneous Urticaria"]},
        "armsInterventionsModule":{"interventions":[{"type":"DRUG","name":"Barzolvolimab"},{"type":"OTHER","name":"Placebo"}]},
        "outcomesModule":{"primaryOutcomes":[{"measure":"Change in observed disease severity",
                "timeFrame":"Week 12"}],"secondaryOutcomes":[{"measure":"Quality of life"}]}}
      ,"hasResults":posted}
    if posted:
        d["resultsSection"]={
           "outcomeMeasuresModule":{"outcomeMeasures":[{"type":"PRIMARY",
             "title":"Change in disease severity","timeFrame":"Week 12",
             "unitOfMeasure":"points",
             "groups":[{"id":"OG000","title":"Treatment group"},{"id":"OG001","title":"Placebo group"}],
             "classes":[{"categories":[{"measurements":[
               {"groupId":"OG000","value":"-22.5"},{"groupId":"OG001","value":"-13.5"}]}]}],
             "analyses":[{"pValue":"0.0006","paramType":"MEAN_DIFFERENCE",
               "paramValue":"-9.0","ciPctValue":95,"ciLowerLimit":"-12.1",
               "ciUpperLimit":"-5.9","groupIds":["OG000","OG001"]}]}]},
           "adverseEventsModule":{"seriousEvents":[{"term":"Adverse event",
              "stats":[{"groupId":"EG000","numAffected":1,"numAtRisk":200}]}]}
        }
    return d

class RegistryEvidenceTest(unittest.TestCase):
    def test_cohort_is_nct_unique_and_exact(self):
        cohort=mod.cohort()
        self.assertEqual(len(cohort),762)
        self.assertEqual(len(set(cohort)),762)
        self.assertTrue(all(n.startswith("NCT") for n in cohort))

    def test_batch_rejects_cross_trial_duplicate_and_pagination(self):
        correct={"studies":[study()]}
        self.assertEqual(len(mod.verify_batch(correct,["NCT06445023"])),1)
        for wrong in [
            {"studies":[study("NCT12345678")]},
            {"studies":[study(),study()]},
            {"studies":[study()],"nextPageToken":"more"}]:
            with self.assertRaisesRegex(ValueError,"CROSS_TRIAL|PAGINATION"):
                mod.verify_batch(wrong,["NCT06445023"])

    def test_protocol_only_evidence_never_assigned_outcome_or_score(self):
        result=mod.extract("NCT06445023","CLDX",study(),"2026-11-04T15:00:00Z")
        self.assertEqual(result["registeredPrimaryOutcomes"][0]["timeFrame"],"Week 12")
        self.assertEqual(result["registeredConditions"],["Chronic Spontaneous Urticaria"])
        self.assertEqual(result["registeredInterventions"],["Barzolvolimab","Placebo"])
        self.assertEqual(result["registeredDesign"]["allocation"],"RANDOMIZED")
        self.assertEqual(result["registeredDesign"]["masking"],"QUADRUPLE")
        self.assertEqual(result["registeredDesign"]["enrollment"],420)
        self.assertFalse(result["hasPostedResults"])
        self.assertEqual(result["postedPrimaryOutcomeCount"],0)
        self.assertEqual(result["evidenceState"],"PROTOCOL_ONLY")
        self.assertIsNone(result["overallRaasScore"])
        self.assertTrue(result["sourceSha256"])
        self.assertEqual(result["sourceUrl"],"https://clinicaltrials.gov/study/NCT06445023")

    def test_source_condition_names_missing_and_malformed_are_not_invented(self):
        without = study()
        del without["protocolSection"]["conditionsModule"]
        result = mod.extract("NCT06445023","CLDX",without,"2026-11-04T15:00:00Z")
        self.assertEqual(result["registeredConditions"], [])
        bad = study()
        bad["protocolSection"]["conditionsModule"] = {"conditions": "not a list"}
        with self.assertRaisesRegex(ValueError,"CONDITIONS_INVALID"):
            mod.extract("NCT06445023","CLDX",bad,"2026-11-04T15:00:00Z")
        bad = study()
        bad["protocolSection"]["conditionsModule"] = ["Bad"]
        with self.assertRaisesRegex(ValueError,"CONDITIONS_MODULE_INVALID"):
            mod.extract("NCT06445023","CLDX",bad,"2026-11-04T15:00:00Z")

    def test_posted_primary_endpoint_analysis_and_serious_events_are_retained(self):
        result=mod.extract("NCT06445023","CLDX",study(posted=True),"2026-11-04T15:00:00Z")
        self.assertEqual(result["evidenceState"],"POSTED_RESULTS_UNGRADED")
        self.assertEqual(result["postedPrimaryOutcomeCount"],1)
        self.assertEqual(result["primaryPostedEvidence"][0]["groups"][0]["title"],"Treatment group")
        self.assertEqual(result["primaryPostedEvidence"][0]["analyses"][0]["groupIds"],["OG000","OG001"])
        self.assertEqual(result["primaryPostedEvidence"][0]["analyses"][0]["ciLowerLimit"],"-12.1")
        self.assertEqual(result["primaryPostedEvidence"][0]["analyses"][0]["pValue"],"0.0006")
        self.assertEqual(result["primaryPostedEvidence"][0]["measurements"][1]["value"],"-13.5")
        self.assertEqual(result["seriousAdverseEventTermCount"],1)
        self.assertIsNone(result["overallRaasScore"])

    def test_missing_registry_response_is_a_visible_error_not_a_negative_result(self):
        def fake(ids):
            return {"NCT06445023":study()} if "NCT06445023" in ids else {}
        got,errors=mod.harvest({"NCT06445023":"CLDX","NCT06455202":"CLDX"},
           ["NCT06445023","NCT06455202"],now="2026-11-04T15:00:00Z",fetch=fake)
        self.assertIn("NCT06445023",got)
        self.assertEqual(errors.get("NCT06455202"),"NOT_RETURNED_BY_REGISTRY_SEARCH")
        self.assertNotIn("NCT06455202",got)

    def test_registry_results_inconsistent_source_is_rejected(self):
        bad=study(posted=True)
        bad["hasResults"]=False
        with self.assertRaisesRegex(ValueError,"INCONSISTENT"):
            mod.extract("NCT06445023","CLDX",bad,"2026-11-04T15:00:00Z")

if __name__=="__main__":
    unittest.main()
