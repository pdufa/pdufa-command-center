"""No guesswork regression tests for 10-NCT 300-metric retrospective RAAS audit."""
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("raas_ten_trial_clinical_pilot",
                                             ROOT / "scripts/raas_ten_trial_clinical_pilot.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def source():
    return (json.loads(mod.INDEX.read_text(encoding="utf8")),
            json.loads(mod.REVIEWS.read_text(encoding="utf8")))


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if mod.INDEX.exists() and mod.REVIEWS.exists():
            cls.idx, cls.reviews = source()
        else:
            cls.idx = cls.reviews = None

    def require_sources(self):
        if self.idx is None:
            self.skipTest("No exact NCT registry index in this checkout")

    def test_all_300_explicit_slots_ten_exact_trials_and_real_review_counts(self):
        self.require_sources()
        rows, summary = mod.build(self.idx, self.reviews)
        self.assertEqual(len(rows), 300)
        self.assertEqual(summary["pilotNctCount"], 10)
        self.assertEqual(summary["metricSlots"], 300)
        self.assertEqual(summary["aiSourceReviewedMetricSlots"], 26)
        self.assertEqual(summary["unscoredMetricSlots"], 274)
        self.assertEqual(summary["humanIndependentReviewedMetricSlots"], 0)
        self.assertEqual(summary["complete30MetricTrials"], 0)
        self.assertEqual(summary["calibratedFdaPredictions"], 0)
        self.assertEqual({r["nctId"] for r in rows}, set(mod.TRIALS))
        for nct in mod.TRIALS:
            group = [r for r in rows if r["nctId"] == nct]
            self.assertEqual(len(group), 30)
            self.assertEqual({r["metricId"] for r in group}, set(mod.METRICS))
            self.assertTrue(all(r["full30of30Score"] == "" for r in group))
            self.assertTrue(all(r["fdaPassCrlExtensionProbability"] == "" for r in group))
            self.assertTrue(all(r["currentPipelineAndPdufaEligibility"] ==
                                "NOT_INDEPENDENTLY_VERIFIED" for r in group))
            self.assertTrue(all(r["purpose"] ==
                                "RETROSPECTIVE_PILOT_NOT_PREDICTIVE_VALIDATION"
                                for r in group))

    def test_provisional_scores_include_primary_source_and_benchmark_not_zeros_for_missing(self):
        self.require_sources()
        rows, _ = mod.build(self.idx, self.reviews)
        scored = [r for r in rows if r["provisionalMetricScore"] != ""]
        missing = [r for r in rows if r["provisionalMetricScore"] == ""]
        self.assertEqual(len(scored), 26)
        self.assertEqual(len(missing), 274)
        self.assertTrue(all(r["provisionalMetricScore"] in (0, 25, 50, 75, 100)
                            for r in scored))
        self.assertTrue(all(r["sourceUrl"].startswith("https://") and
                            r["benchmarkSourceUrl"].startswith("https://") and
                            r["observedResult"] and r["uncertaintyReview"] and
                            r["criticalRiskReview"] for r in scored))
        self.assertTrue(all(r["observedResult"] == "" and
                            r["sourceUrl"] == "" for r in missing))
        self.assertTrue(all(r["humanIndependentReview"] is False for r in rows))

    def test_wrong_trial_ticker_cannot_inherit_historical_metric_reviews(self):
        self.require_sources()
        altered = copy.deepcopy(self.idx)
        for e in altered["records"]:
            if e["nctId"] == mod.TRIALS[0]:
                e["ticker"] = "WRONG"
        with self.assertRaisesRegex(ValueError, "INVALID_REVIEW"):
            mod.build(altered, self.reviews)

    def test_duplicate_or_forged_metric_review_rejected(self):
        self.require_sources()
        duplicated = copy.deepcopy(self.reviews)
        duplicated["records"].append(duplicated["records"][0])
        with self.assertRaisesRegex(ValueError, "DUPLICATE_METRIC"):
            mod.build(self.idx, duplicated)
        modified = copy.deepcopy(self.reviews)
        modified["records"][0]["sourceUrl"] = "https://clinicaltrials.gov/study/BAD"
        modified["records"][0]["benchmarkSourceUrl"] = "https://clinicaltrials.gov/study/BAD"
        with self.assertRaisesRegex(ValueError, "INVALID_REVIEW"):
            mod.build(self.idx, modified)

    def test_extra_out_of_pilot_trials_not_silently_scored(self):
        self.require_sources()
        altered = copy.deepcopy(self.reviews)
        altered["records"].append({**altered["records"][0],
                                    "nctId": "NCT99999999"})
        rows, result = mod.build(self.idx, altered)
        self.assertEqual(len(rows), 300)
        self.assertEqual(result["aiSourceReviewedMetricSlots"], 26)

    def test_pilot_csv_is_excel_safe_and_contains_300_rows(self):
        self.require_sources()
        output, summary = mod.generate(self.idx, self.reviews)
        rows = list(csv.DictReader(io.StringIO(output)))
        self.assertEqual(len(rows), 300)
        self.assertEqual(json.loads(summary)["complete30MetricTrials"], 0)
        self.assertEqual(mod.safe("=SUM(1,1)"), "'=SUM(1,1)")
        self.assertEqual(mod.safe("-1"), "'-1")
        self.assertEqual(mod.safe("safe"), "safe")


if __name__ == "__main__":
    unittest.main()
