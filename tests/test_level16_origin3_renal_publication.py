"""Exact-NCT ORIGIN 3 renal evidence and non-leaking clinical review gates."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/medical/level16_origin3_renal_publication.py"
spec = importlib.util.spec_from_file_location("level16_origin3_renal_publication", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Origin3RenalPublicationTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(mod.INPUT.read_text(encoding="utf-8"))

    def test_same_nct_has_two_original_publication_dates_not_two_trials(self):
        p = mod.assess(self.data)
        self.assertEqual(p["nct"], "NCT04716231")
        self.assertTrue(p["outcomeExposedNotBlind"])
        self.assertEqual(p["interimPublicationDate"], "2025-11-06")
        self.assertEqual(p["finalPublicationDate"], "2026-10-22")
        self.assertIn("NEJMoa2510198", p["interimSource"])
        self.assertIn("NEJMoa2610103", p["finalSource"])
        self.assertTrue(p["interimAndFinalCohortsNotInterchangeable"])
        self.assertFalse(p["historicalBlindBacktestPermitted"])
        self.assertFalse(p["fdaPredictionPermitted"])
        self.assertEqual(p["independentlyAdjudicatedLevels"], 0)
        self.assertIsNone(p["score"])
        self.assertIsNone(p["approvalProbability"])
        self.assertIsNone(p["fdaOutcomeJudgment"])

    def test_phase3_interim_primary_is_proteinuria_not_final_egfr(self):
        p = mod.assess(self.data)
        self.assertEqual(p["studyContext"]["registryPhaseUnreviewed"], ["PHASE3"])
        a = p["interimAnalysis"]
        self.assertEqual(a["denominator"]["prespecifiedInterimAnalysisTotal"], 203)
        self.assertEqual(a["denominator"]["atacicept"], 106)
        self.assertEqual(a["denominator"]["placebo"], 97)
        self.assertEqual(a["primary"]["classification"], "PRIMARY_INTERIM")
        self.assertEqual(a["primary"]["metric"], "GEOMETRIC_MEAN_PERCENT_REDUCTION")
        self.assertEqual(a["primary"]["ataciceptPercentReduction"], 45.7)
        self.assertEqual(a["primary"]["placeboPercentReduction"], 6.8)
        self.assertEqual(a["primary"]["publishedBetweenGroupDifferencePercentagePoints"], 41.8)
        self.assertEqual(a["primary"]["difference95CI"], [28.9, 52.3])
        self.assertTrue(p["primaryUPCRIsNotEGFR"])

    def test_final_secondary_renal_function_and_progression_preserved(self):
        p = mod.assess(self.data)
        f = p["finalAnalysis"]
        self.assertEqual(f["denominator"]["randomized"], 431)
        self.assertEqual(f["denominator"]["treatedTotal"], 428)
        self.assertEqual(f["denominator"]["ataciceptTreated"], 214)
        self.assertEqual(f["denominator"]["placeboTreated"], 214)
        self.assertTrue(p["finalEGFREndpointsAreSecondary"])
        self.assertEqual([v["classification"] for v in f["secondaryEfficacy"]],
                         ["PRESPECIFIED_SECONDARY", "PRESPECIFIED_SECONDARY"])
        self.assertEqual(f["secondaryEfficacy"][0]["reportedBetweenGroupDifference"], 5.58)
        self.assertEqual(f["secondaryEfficacy"][0]["unit"], "mL/min/1.73m²")
        self.assertEqual(f["secondaryEfficacy"][1]["reportedBetweenGroupDifference"], 5.00)
        self.assertEqual(f["secondaryEfficacy"][1]["unit"], "mL/min/1.73m²/year")
        self.assertEqual(f["progression"]["atacicept"], 11)
        self.assertEqual(f["progression"]["placebo"], 38)
        self.assertEqual(f["progression"]["hazardRatio"], 0.24)
        self.assertEqual(f["progression"]["label"], "PUBLISHED_COMPOSITE_NOT_MORTALITY_ENDPOINT")

    def test_safety_interim_and_final_samples_are_not_pooled(self):
        p = mod.assess(self.data)
        self.assertEqual(p["interimAnalysis"]["safety"]["ataciceptPercent"], 59.3)
        self.assertEqual(p["interimAnalysis"]["safety"]["placeboPercent"], 50.0)
        f = p["finalAnalysis"]
        self.assertEqual(f["safety"]["anyAdverseEvents"]["atacicept"], 160)
        self.assertEqual(f["safety"]["anyAdverseEvents"]["placebo"], 167)
        self.assertEqual(f["safety"]["seriousAdverseEventsPercent"]["atacicept"], 7.0)
        self.assertEqual(f["safety"]["seriousAdverseEventsPercent"]["placebo"], 15.4)
        self.assertEqual(f["safety"]["deathsReported"]["atacicept"], 0)
        self.assertEqual(f["safety"]["deathsReported"]["placebo"], 1)

    def test_fake_source_review_and_fda_forecast_are_rejected(self):
        for key, val in (
            ("originalClinicalSourceAuthenticated", True),
            ("genuineStatisticalReviewCompleted", True),
            ("genuineDiseaseSpecialistReviewCompleted", True),
            ("independentChallengeCompleted", True),
            ("scientificAdjudicationCompleted", True),
            ("fdaApplicationCycleVerified", True),
            ("blindHistoricalPredictionPermitted", True),
            ("scientificScore", 98),
            ("approvalProbability", .99),
            ("fdaOutcomeJudgment", "APPROVED"),
            ("nct", "NCT05507203"),
            ("reviewerId", "fake-person"),
        ):
            item = copy.deepcopy(self.data)
            item[key] = val
            with self.subTest(key=key), self.assertRaises(ValueError):
                mod.assess(item)

    def test_interim_efficacy_and_denom_corruption_blocked(self):
        changes = (
            lambda d: d["reports"][0]["primary"].update(
                publishedBetweenGroupDifferencePercentagePoints=38.9),
            lambda d: d["reports"][0]["primary"].update(metric="RAW_UNADJUSTED_DIFFERENCE"),
            lambda d: d["reports"][0]["primary"].update(timeWeek=52),
            lambda d: d["reports"][0]["primary"].update(
                classification="SECONDARY"),
            lambda d: d["reports"][0]["denominator"].update(
                prespecifiedInterimAnalysisTotal=431),
            lambda d: d["reports"][0]["denominator"].update(atacicept=214),
        )
        for fn in changes:
            d = copy.deepcopy(self.data)
            fn(d)
            with self.assertRaises(ValueError):
                mod.assess(d)

    def test_final_kidney_slope_and_progression_misclassification_blocked(self):
        changes = (
            lambda d: d["reports"][1]["secondaryEfficacy"][0].update(
                classification="PRIMARY"),
            lambda d: d["reports"][1]["secondaryEfficacy"][1].update(
                unit="mL/min/1.73m²"),
            lambda d: d["reports"][1]["secondaryEfficacy"][0].update(
                reportedBetweenGroupDifference=0.0),
            lambda d: d["reports"][1]["secondaryEfficacy"].pop(),
            lambda d: d["reports"][1]["progression"].update(hazardRatio=1.0),
            lambda d: d["reports"][1]["progression"].update(
                label="MORTALITY_ENDPOINT"),
            lambda d: d["reports"][1]["denominator"].update(treatedTotal=431),
            lambda d: d["reports"][1]["safety"]["seriousAdverseEventsPercent"].update(
                atacicept=0.0),
        )
        for fn in changes:
            d = copy.deepcopy(self.data)
            fn(d)
            with self.assertRaises(ValueError):
                mod.assess(d)

    def test_postpublished_2026_outcome_cannot_be_reclassified_as_predecision(self):
        for fn in (
            lambda d: d.update(evidenceCutoffDate="2025-11-07"),
            lambda d: d["reports"][1]["source"].update(publishedOnline="2025-11-06"),
            lambda d: d["reports"].reverse(),
            lambda d: d["reports"][1]["source"].update(doi="10.1056/NEJMoa2510198"),
            lambda d: d["reports"][1]["source"].update(independentlyAuthenticated=True),
            lambda d: d["reports"][0]["source"].update(pmid="42911181"),
        ):
            d = copy.deepcopy(self.data)
            fn(d)
            with self.assertRaises(ValueError):
                mod.assess(d)

    def test_review_questions_include_population_and_biological_endpoints(self):
        result = mod.assess(self.data)
        q = " ".join(result["independentReviewQuestions"]).lower()
        for term in ("phase 2b", "proteinuria", "egfr", "multiplicity",
                     "clinical", "cutoff", "source"):
            self.assertIn(term, q)
        self.assertFalse(result["sourceIndependentlyAuthenticated"])
        self.assertFalse(result["scientificallyAdjudicated"])


if __name__ == "__main__":
    unittest.main()
