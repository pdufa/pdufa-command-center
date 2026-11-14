"""Check published ORCA-2 results are cited without fabricated statistical review."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/medical/level16_orca2_publication_review.py"
spec = importlib.util.spec_from_file_location("level16_orca2_publication_review", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Orca2PublicationReviewTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(module.INPUT.read_text(encoding="utf-8"))

    def test_cites_all_four_2023_publication_comparisons_without_fda_predictions(self):
        report = module.assess(self.doc)
        self.assertEqual(report["nct"], "NCT04576949")
        self.assertEqual(report["sourceUrl"],
                         "https://pmc.ncbi.nlm.nih.gov/articles/PMC10336611/")
        self.assertTrue(report["outcomeExposedNotBlind"])
        self.assertEqual(len(report["publishedEfficacyComparisons"]), 4)
        self.assertEqual([r["classification"] for r in report["publishedEfficacyComparisons"]],
                         ["PRIMARY", "PRIMARY", "SECONDARY", "SECONDARY"])
        self.assertEqual(report["publishedEfficacyComparisons"][0]["activePct"], 25.3)
        self.assertEqual(report["publishedEfficacyComparisons"][0]["placeboPct"], 4.4)
        self.assertEqual(report["publishedEfficacyComparisons"][1]["activePct"], 32.6)
        self.assertEqual(report["publishedEfficacyComparisons"][1]["placeboPct"], 7.0)
        self.assertEqual(report["actualOriginalSourceAuthenticationCount"], 0)
        self.assertEqual(report["independentScientificReviews"], 0)
        self.assertIsNone(report["scientificScores"])
        self.assertIsNone(report["fdaOutcomeJudgment"])
        self.assertIsNone(report["approvalProbability"])

    def test_safety_has_distinct_denominator_and_concerning_imbalances(self):
        report = module.assess(self.doc)
        self.assertEqual(report["studyDesign"]["randomized"], 810)
        self.assertEqual(report["studyDesign"]["followupWeek24Completed"], 618)
        self.assertEqual(report["publishedSafetyObservation"]["cytisiniclineExposed"], 539)
        self.assertEqual(report["publishedSafetyObservation"]["placeboExposed"], 270)
        self.assertEqual(report["publishedSafetyObservation"]["seriousAdverseEvents"]["cytisinicline"], 18)
        self.assertEqual(report["publishedSafetyObservation"]["seriousAdverseEvents"]["placebo"], 3)
        self.assertEqual(report["publishedSafetyObservation"][
            "treatmentRelatedSeriousAdverseEventsJudgedByInvestigators"]["cytisinicline"], 0)
        self.assertTrue(report["publishedSafetyObservation"]["oneDeathReportedInCyt6"])
        self.assertFalse("risk" in report["status"].lower())

    def test_rejects_invented_reviews_predictions_and_scores(self):
        for field, value in (
            ("sourceIndependentlyAuthenticated", True),
            ("sourceReviewerApproved", True),
            ("independentlyAdjudicatedLevels", 1),
            ("predictionAllowed", True),
            ("approvalProbability", 0.99),
            ("fdaOutcomeJudgment", "APPROVED"),
            ("reviewerId", "injected"),
            ("scientificScore", 100),
            ("evidenceCutoffDate", "2022-01-01"),
            ("nct", "NCT05507203"),
        ):
            changed = copy.deepcopy(self.doc)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                module.assess(changed)

    def test_rejects_primary_secondary_switch_and_placebo_denominator_change(self):
        for field, value in (
            ("classification", "SECONDARY"),
            ("activeRandomized", 270),
            ("placeboRandomized", 269),
            ("activePct", 99.9),
            ("oddsRatioReported", 50.0),
            ("pValueReported", "<0.000001"),
            ("ci95Reported", [0.5, 99.9]),
        ):
            changed = copy.deepcopy(self.doc)
            changed["efficacy"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                module.assess(changed)

    def test_rejects_cross_trial_or_duplicate_endpoint_sources(self):
        changed = copy.deepcopy(self.doc)
        changed["source"]["url"] = "https://pmc.ncbi.nlm.nih.gov/articles/another-trial/"
        with self.assertRaises(ValueError):
            module.assess(changed)
        changed = copy.deepcopy(self.doc)
        changed["efficacy"][1] = copy.deepcopy(changed["efficacy"][0])
        with self.assertRaises(ValueError):
            module.assess(changed)

    def test_rejects_erased_safety_events_and_treatment_related_inference(self):
        changed = copy.deepcopy(self.doc)
        changed["safety"]["seriousAdverseEvents"]["cytisinicline"] = 0
        with self.assertRaises(ValueError):
            module.assess(changed)
        changed = copy.deepcopy(self.doc)
        changed["safety"]["treatmentRelatedSeriousAdverseEventsJudgedByInvestigators"]["cytisinicline"] = 18
        with self.assertRaises(ValueError):
            module.assess(changed)
        changed = copy.deepcopy(self.doc)
        changed["safety"]["oneDeathReportedInCyt6"] = False
        with self.assertRaises(ValueError):
            module.assess(changed)

    def test_unapproved_source_must_not_hide_limitations_or_missing_followup(self):
        changed = copy.deepcopy(self.doc)
        changed["trial"]["followupWeek24Completed"] = 810
        with self.assertRaises(ValueError):
            module.assess(changed)
        changed = copy.deepcopy(self.doc)
        changed["limitationsUnreviewed"] = []
        with self.assertRaises(ValueError):
            module.assess(changed)
        changed = copy.deepcopy(self.doc)
        changed["unresolvedQuestions"] = ["Nothing remains"]
        with self.assertRaises(ValueError):
            module.assess(changed)

    def test_cannot_claim_long_term_clinical_outcomes(self):
        result = module.assess(self.doc)
        joined = " ".join(result["documentedLimitationsUnreviewed"]).lower()
        self.assertIn("mortality", joined)
        self.assertIn("rare", joined)
        self.assertIn("generalizability", joined)


if __name__ == "__main__":
    unittest.main()
