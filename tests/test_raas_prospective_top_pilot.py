"""Regression tests: prospective TOP NCTs are not FDA PDUFA predictions."""
import copy
import csv
import io
import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import raas_prospective_top_pilot as mod


def sources():
    return (
        json.loads(mod.BASELINES.read_text(encoding="utf8")),
        json.loads(mod.REGISTRY.read_text(encoding="utf8")),
        json.loads(mod.REVIEWS.read_text(encoding="utf8")),
        mod.CATALOG.read_text(encoding="utf8"),
    )


class ProspectiveSourceOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baselines, cls.registry, cls.reviews, cls.catalog = sources()

    def test_two_trials_sixty_metrics_and_six_real_documented_top_reviews(self):
        csv_data, status_data = mod.generate(
            self.baselines, self.registry, self.reviews, self.catalog)
        data = list(csv.DictReader(io.StringIO(csv_data)))
        status = json.loads(status_data)
        self.assertEqual(status["prospectiveTrials"], 2)
        self.assertEqual(status["researchTrialUniverse"], 762)
        self.assertEqual(status["metricSlots"], 60)
        self.assertEqual(status["provisionalScoredMetricSlots"], 6)
        self.assertEqual(status["unscoredMetricSlots"], 54)
        self.assertEqual(status["fullValidatedRaasScores"], 0)
        self.assertEqual(status["calibratedFdaPredictions"], 0)
        self.assertEqual(status["trialNctsWithProvisionalScores"], 2)
        self.assertEqual(len(data), 60)
        for nct in ("NCT07363577", "NCT07671911"):
            rows = [r for r in data if r["nctId"] == nct]
            scored = [r for r in rows if r["provisionalMetricScore"]]
            self.assertEqual(len(rows), 30)
            self.assertEqual(len(scored), 3)
            self.assertEqual(
                {r["metricId"] for r in scored}, {"pre-1-1", "pre-1-2", "pre-4-1"})
            self.assertTrue(all(r["provisionalMetricScore"] == "50" for r in scored))
            self.assertTrue(all(r["reviewClass"] == "AI_SOURCE_CROSSCHECKED"
                                for r in scored))
            self.assertTrue(all(r["reviewClass"] == "N_A_MISSING_REVIEW"
                                for r in rows if not r["provisionalMetricScore"]))
            self.assertTrue(all(r["weightedCoverageAcross30Pct"] == "13.0"
                                for r in rows))
            self.assertTrue(all(r["observedMeanOnReviewedMetricsOnly"] == "50.0"
                                for r in rows))
            self.assertTrue(all(r["full30MetricRaasScore"] == "" and
                                r["fdaPassCrlExtensionProbability"] == "" and
                                r["marketCapCurrentValidation"] ==
                                    "VENDOR_ONLY_NOT_INDEPENDENTLY_VERIFIED" and
                                r["stageAndPdufaIndependentlyVerified"] == "False"
                                for r in rows))
            self.assertTrue(all(r["metricEvidenceSourceUrl"].startswith("https://")
                                and r["benchmarkSourceUrl"].startswith("https://")
                                and r["observedEvidence"] and r["criticalRisks"]
                                for r in scored))
        trvi = next(r for r in data if r["nctId"] == "NCT07671911")
        self.assertIn("2028", trvi["readoutWindowAsReported"])
        self.assertNotIn("H1 2027", trvi["readoutWindowAsReported"])

    def test_bad_drug_ticker_or_future_information_fails_closed(self):
        x = copy.deepcopy(self.baselines)
        x["records"][0]["ticker"] = "TRVI"
        with self.assertRaisesRegex(ValueError, "CROSS_NCT"):
            mod.generate(x, self.registry, self.reviews, self.catalog)
        x = copy.deepcopy(self.baselines)
        x["records"][0]["drug"] = "Different medication"
        with self.assertRaisesRegex(ValueError, "REVIEW_IDENTITY"):
            mod.generate(x, self.registry, self.reviews, self.catalog)
        x = copy.deepcopy(self.baselines)
        x["records"][0]["observations"][0]["sourcePublishedAt"] = "2026-11-05"
        with self.assertRaisesRegex(ValueError, "FUTURE_SOURCE"):
            mod.generate(x, self.registry, self.reviews, self.catalog)
        x = copy.deepcopy(self.baselines)
        x["records"][0]["archivedRaasPrediction"] = True
        with self.assertRaisesRegex(ValueError, "INVALID_CAPTURE"):
            mod.generate(x, self.registry, self.reviews, self.catalog)

    def test_never_leaks_another_trial_or_uses_the_wrong_readout(self):
        x = copy.deepcopy(self.reviews)
        for r in x["records"]:
            if r["nctId"] == "NCT07671911" and r["metricId"] == "pre-4-1":
                r["sourceDate"] = "2026-11-05"
        with self.assertRaisesRegex(ValueError, "RAAS_PARTIAL_REVIEW_EVIDENCE_INVALID"):
            mod.generate(self.baselines, self.registry, x, self.catalog)
        x = copy.deepcopy(self.baselines)
        x["records"][1]["observations"] = [
            o for o in x["records"][1]["observations"]
            if "pre-4-1" not in o.get("metricIds", [])
        ]
        with self.assertRaisesRegex(ValueError, "MISSING_READOUT_GUIDANCE"):
            mod.generate(x, self.registry, self.reviews, self.catalog)

    def test_duplicate_prospective_program_and_source_drift_rejected(self):
        x = copy.deepcopy(self.baselines)
        x["records"].append(copy.deepcopy(x["records"][0]))
        with self.assertRaisesRegex(ValueError, "INVALID_CAPTURE"):
            mod.generate(x, self.registry, self.reviews, self.catalog)
        x = copy.deepcopy(self.baselines)
        x["records"][0]["marketCap"]["observedAsOf"] = "2026-11-05"
        with self.assertRaisesRegex(ValueError, "INVALID_VENDOR_CAP"):
            mod.generate(x, self.registry, self.reviews, self.catalog)

    def test_csv_formula_injection_protected(self):
        self.assertEqual(mod._safe("=2+2"), "'=2+2")
        self.assertEqual(mod._safe("@SUM(A1)"), "'@SUM(A1)")
        self.assertEqual(mod._safe("ordinary"), "ordinary")


if __name__ == "__main__":
    unittest.main()
