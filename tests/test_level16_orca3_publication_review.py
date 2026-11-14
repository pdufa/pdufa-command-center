"""ORCA-3 original JAMA source findings remain unreviewed and fixed to exact NCT."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "scripts/medical/level16_orca3_publication_review.py"
spec = importlib.util.spec_from_file_location("level16_orca3_publication_review", P)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Orca3PaperTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(module.INPUT.read_text(encoding="utf-8"))

    def test_pubmed_article_identity_and_four_original_comparisons(self):
        result = module.assess(self.doc)
        self.assertEqual(result["nct"], "NCT05206370")
        self.assertEqual(result["publishedDate"], "2025-04-21")
        self.assertEqual(result["sourceUrl"], "https://pmc.ncbi.nlm.nih.gov/articles/PMC12012700/")
        self.assertEqual(len(result["publishedEfficacyComparisons"]), 4)
        self.assertEqual([x["type"] for x in result["publishedEfficacyComparisons"]],
                         ["PRIMARY", "PRIMARY", "SECONDARY", "SECONDARY"])
        self.assertEqual(result["publishedEfficacyComparisons"][0]["activePercent"], 14.8)
        self.assertEqual(result["publishedEfficacyComparisons"][1]["activePercent"], 30.3)
        self.assertEqual(result["publishedEfficacyComparisons"][2]["activePercent"], 6.8)
        self.assertEqual(result["publishedEfficacyComparisons"][3]["activePercent"], 20.5)
        self.assertTrue(result["outcomeExposedNotBlind"])
        self.assertEqual(result["independentScientificReviews"], 0)
        self.assertIsNone(result["scientificScores"])
        self.assertIsNone(result["fdaOutcomeJudgment"])
        self.assertIsNone(result["approvalProbability"])

    def test_safety_and_followup_denominators_are_not_interchanged(self):
        result = module.assess(self.doc)
        self.assertEqual(result["studyDesign"]["randomized"], 792)
        self.assertEqual(result["studyDesign"]["week24Completed"], 628)
        self.assertEqual(result["studyDesign"]["safetyTreated"], 785)
        safety = result["publishedSafetyObservation"]
        self.assertEqual(safety["combinedCytisiniclineExposed"], 523)
        self.assertEqual(safety["placeboExposed"], 262)
        self.assertEqual(safety["seriousTreatmentEmergentAEs"]["cytisinicline"], 16)
        self.assertEqual(safety["seriousTreatmentEmergentAEs"]["placebo"], 8)
        self.assertEqual(safety["deathsInCytisiniclineArms"], 4)
        self.assertEqual(safety["seriousTreatmentRelatedAEsInvestigatorJudged"]["cytisinicline"], 0)

    def test_source_tables_and_narrative_ci_discrepancies_stay_visible(self):
        result = module.assess(self.doc)
        rows = result["publicationTextDiscrepanciesUnreviewed"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["table2"], "1.9")
        self.assertEqual(rows[0]["narrative"], "1.8")
        self.assertEqual(rows[1]["table2"], "12.5")
        self.assertEqual(rows[1]["narrative"], "12.4")
        self.assertTrue(all(x["status"].endswith("_REQUIRES_SOURCE_CHECK") for x in rows))

    def test_forged_signoff_fda_results_and_unblind_approval_rejected(self):
        for key, value in (
            ("sourceIndependentlyAuthenticated",True),
            ("independentMedicalReviewCompleted",True),
            ("statisticallyAdjudicated",True),
            ("independentChallengeCompleted",True),
            ("fdaApplicationLinkVerified",True),
            ("approvalProbability",0.93),
            ("approvalPrediction","FDA_APPROVED"),
            ("clinicalScore",98),
            ("reviewerId","fake-person"),
            ("nct","NCT04576949"),
            ("evidenceCutoffDate","2022-01-01"),
        ):
            row=copy.deepcopy(self.doc)
            row[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.assess(row)

    def test_misclassified_or_altered_primary_or_secondary_efficacy_rejected(self):
        for key,value in (
            ("type","SECONDARY"),("activeCount",999),("activeDenom",269),
            ("placeboCount",0),("placeboDenom",271),("activePercent",100.0),
            ("publishedOddsRatio",100),("table95ci",[0.0,100.0]),
            ("publishedPValue","=0"),("period","WEEKS_3_TO_24")
        ):
            row=copy.deepcopy(self.doc)
            row["endpoints"][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                module.assess(row)

    def test_duplicate_endpoint_and_cross_trial_source_rejected(self):
        row=copy.deepcopy(self.doc)
        row["endpoints"][1]=copy.deepcopy(row["endpoints"][0])
        with self.assertRaises(ValueError):
            module.assess(row)
        row=copy.deepcopy(self.doc)
        row["source"]["pmid"]="37432430"
        with self.assertRaises(ValueError):
            module.assess(row)

    def test_discrepancy_suppression_or_rewrite_fails_closed(self):
        for operation in (
            lambda x:x["sourceTextDiscrepanciesUnreviewed"].clear(),
            lambda x:x["sourceTextDiscrepanciesUnreviewed"][0].update(narrative="1.9"),
            lambda x:x["sourceTextDiscrepanciesUnreviewed"][0].update(status="RESOLVED"),
            lambda x:x["sourceTextDiscrepanciesUnreviewed"].append(
                copy.deepcopy(x["sourceTextDiscrepanciesUnreviewed"][0]))
        ):
            row=copy.deepcopy(self.doc)
            operation(row)
            with self.assertRaises(ValueError):
                module.assess(row)

    def test_serious_adverse_events_or_attribution_cannot_be_erased(self):
        for path,val in (
            (("seriousTreatmentEmergentAEs","cytisinicline"),0),
            (("seriousTreatmentEmergentAEs","placebo"),0),
            (("seriousTreatmentRelatedAEsInvestigatorJudged","cytisinicline"),16),
            (("studyDrugDiscontinuationsDueToAEs","cytisinicline"),0),
        ):
            row=copy.deepcopy(self.doc)
            row["safety"][path[0]][path[1]]=val
            with self.subTest(path=path),self.assertRaises(ValueError):
                module.assess(row)
        row=copy.deepcopy(self.doc)
        row["safety"]["deathsInCytisiniclineArms"]=0
        with self.assertRaises(ValueError):
            module.assess(row)

    def test_missing_source_limitations_or_wrong_safety_population_rejected(self):
        row=copy.deepcopy(self.doc)
        row["limitationsAndReviewNeeds"]=[]
        with self.assertRaises(ValueError):
            module.assess(row)
        row=copy.deepcopy(self.doc)
        row["trial"]["safetyArms"][1]["n"]=264
        with self.assertRaises(ValueError):
            module.assess(row)
        row=copy.deepcopy(self.doc)
        row["trial"]["week24Completed"]=792
        with self.assertRaises(ValueError):
            module.assess(row)


if __name__ == "__main__":
    unittest.main()
