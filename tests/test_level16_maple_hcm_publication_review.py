"""MAPLE-HCM source-role, continuous endpoint and guarded review regression tests."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/medical/level16_maple_hcm_publication_review.py"
spec = importlib.util.spec_from_file_location("level16_maple_hcm_publication_review", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MapleHcmPublicationTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(module.INPUT.read_text(encoding="utf-8"))

    def test_exact_nct_and_nejm_source_validated(self):
        item = module.assess(self.doc)
        self.assertEqual(item["nct"], "NCT05767346")
        self.assertEqual(item["sourceUrl"],
                         "https://www.nejm.org/doi/10.1056/NEJMoa2504654")
        self.assertEqual(item["publishedDate"], "2025-08-30")
        self.assertEqual(item["endpointDataType"],
                         "CONTINUOUS_EXERCISE_CAPACITY_NOT_BINARY_ABSTINENCE")
        self.assertTrue(item["outcomeExposedNotBlind"])
        self.assertEqual(item["independentScientificReviews"], 0)
        self.assertFalse(item["sourceIndependentlyAuthenticated"])
        self.assertFalse(item["scientificallyAdjudicated"])
        self.assertIsNone(item["approvalProbability"])
        self.assertIsNone(item["scientificScores"])
        self.assertIsNone(item["fdaOutcomeJudgment"])

    def test_active_comparator_and_175_randomized(self):
        item = module.assess(self.doc)
        d = item["studyDesign"]
        self.assertEqual(d["randomized"], 175)
        self.assertEqual([(x["id"], x["randomized"]) for x in d["doseArms"]],
                         [("AFICAMTEN", 88), ("METOPROLOL", 87)])
        self.assertEqual(d["treatmentWeeks"], 24)
        self.assertTrue(d["comparatorIsActiveDrug"])
        self.assertFalse(d["placeboOnlyControl"])

    def test_primary_pvo2_continuous_change_with_source_reported_ci(self):
        primary = module.assess(self.doc)["primaryEndpointReported"]
        self.assertEqual(primary["classification"], "PRIMARY")
        self.assertEqual(primary["type"], "CONTINUOUS_CHANGE")
        self.assertEqual(primary["unit"], "mL/kg/min")
        self.assertEqual(primary["aficamtenMeanChange"], 1.1)
        self.assertEqual(primary["metoprololMeanChange"], -1.2)
        self.assertEqual(primary["adjustedBetweenGroupMeanDifference"], 2.3)
        self.assertEqual(primary["adjustedBetweenGroup95CI"], [1.5, 3.1])
        self.assertEqual(primary["sourceReportedPValue"], "<0.001")

    def test_secondary_outcomes_preserve_direction_units_and_non_significance(self):
        result = module.assess(self.doc)
        secondary = result["secondaryEndpointsFromACC"]
        self.assertEqual(len(secondary), 6)
        by_id = {x["id"]:x for x in secondary}
        self.assertEqual(by_id["VALSALVA_LVOT_GRADIENT_W24"]["effect"], -34.9)
        self.assertEqual(by_id["NT_PROBNP_PROPORTIONAL_CHANGE_W24"]["type"], "RATIO")
        self.assertEqual(by_id["LEFT_VENTRICULAR_MASS_INDEX_W24"]["ci95"],
                         [-11.7, 2.0])
        self.assertEqual(by_id["LEFT_VENTRICULAR_MASS_INDEX_W24"]["pValue"], "0.16")
        self.assertTrue(all(x["reportedBy"] ==
                            "INDEPENDENT_SOCIETY_SUMMARY_NOT_ORIGINAL_STUDY_REPORT"
                            for x in secondary))

    def test_serious_adverse_events_and_lvef_risks_remain(self):
        safety = module.assess(self.doc)["publishedSafetyObservationFromACC"]
        self.assertEqual(safety["seriousAdverseEvents"],
                         {"aficamten":7,"metoprolol":6,
                          "aficamtenDenom":88,"metoprololDenom":87})
        self.assertEqual(safety["lvefBetweenGroupDifferencePercentagePoints"], -4.2)
        self.assertEqual(safety["lvefDifference95CI"], [-5.3,-3.1])
        self.assertTrue(safety["oneDeathReportedInAficamtenArm"])
        self.assertIn("attribution", safety["note"])

    def test_forged_authentication_review_and_fda_predictions_refused(self):
        for key,val in (
            ("sourceIndependentlyAuthenticated",True),
            ("originalClinicalTablesAuthenticated",True),
            ("qualifiedClinicalReviewCompleted",True),
            ("independentStatisticalReviewCompleted",True),
            ("finalAdjudicationCompleted",True),
            ("verifiedFdaApplicationCycle",True),
            ("blindHistoricalPredictionPermitted",True),
            ("clinicalScore",95),
            ("approvalProbability",0.98),
            ("fdaOutcomeJudgment","APPROVED"),
            ("nct","NCT04576949"),
            ("evidenceCutoffDate","2025-01-01"),
            ("reviewerId","fake-admin"),
        ):
            doc=copy.deepcopy(self.doc)
            doc[key]=val
            with self.subTest(key=key),self.assertRaises(ValueError):
                module.assess(doc)

    def test_source_attribution_never_promotes_acc_synopsis_to_original_article(self):
        for mutation in (
            lambda d:d["sources"][1].update(role="ORIGINAL_PEER_REVIEWED_ABSTRACT"),
            lambda d:d["sources"][1].update(originalSourceIndependentlyAuthenticated=True),
            lambda d:d["sources"][1].update(url="https://example.com/fake.pdf"),
            lambda d:d["sources"].pop(),
            lambda d:d["primaryEndpoint"].update(sourceRole=
                "INDEPENDENT_SOCIETY_SUMMARY_NOT_ORIGINAL_STUDY_REPORT"),
        ):
            row=copy.deepcopy(self.doc)
            mutation(row)
            with self.assertRaises(ValueError):
                module.assess(row)

    def test_primary_endpoint_metric_unit_and_ci_cannot_be_corrupted(self):
        for key,value in (
            ("type","BINARY_ODDS_RATIO"),
            ("unit","%"),
            ("aficamtenMeanChange",-1.2),
            ("metoprololMeanChange",1.1),
            ("adjustedBetweenGroupMeanDifference",0.0),
            ("adjustedBetweenGroup95CI",[0.0,3.1]),
            ("sourceReportedPValue","<1"),
        ):
            doc=copy.deepcopy(self.doc)
            doc["primaryEndpoint"][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                module.assess(doc)

    def test_missing_or_corrupted_secondary_effects_and_safety_rejected(self):
        for change in (
            lambda d:d["secondaryEndpoints"].pop(),
            lambda d:d["secondaryEndpoints"][0].update(unit="mm Hg"),
            lambda d:d["secondaryEndpoints"][0].update(effect=100),
            lambda d:d["secondaryEndpoints"][5].update(pValue="<.001"),
            lambda d:d["safety"]["seriousAdverseEvents"].update(aficamten=0),
            lambda d:d["safety"].update(oneDeathReportedInAficamtenArm=False),
            lambda d:d["safety"].update(lvefBetweenGroupDifferencePercentagePoints=0.0),
        ):
            d=copy.deepcopy(self.doc)
            change(d)
            with self.assertRaises(ValueError):
                module.assess(d)

    def test_scope_and_documented_limitations_remain_unreviewed(self):
        d=copy.deepcopy(self.doc)
        d["evidenceLimitationsUnreviewed"]=[]
        with self.assertRaises(ValueError):
            module.assess(d)
        d=copy.deepcopy(self.doc)
        d["reviewQuestions"]=[]
        with self.assertRaises(ValueError):
            module.assess(d)
        result=module.assess(self.doc)
        joined=" ".join(result["documentedLimitationsUnreviewed"]).lower()
        self.assertIn("ejection fraction",joined)
        self.assertIn("mortality",joined)
        self.assertIn("generalizability",joined)


if __name__=="__main__":
    unittest.main()
