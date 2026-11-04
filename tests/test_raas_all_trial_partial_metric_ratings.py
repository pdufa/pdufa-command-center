"""Regression tests for all-trial RAAS partial research scores, never full FDA odds."""
import csv
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import raas_all_trial_partial_metric_ratings as mod


def trial(nct="NCT00000001", ticker="ABC"):
    return {
        "nctId": nct, "ticker": ticker,
        "sourceUrl": "https://clinicaltrials.gov/study/" + nct,
        "postedResults": True, "registryStatus": "COMPLETED",
        "primaryResults": [],
        "primaryDefinitions": [],
        "seriousEventDetails": [],
        "evidenceState": "POSTED_RESULTS_UNGRADED",
    }


def index(trials):
    return {
        "schemaVersion": 1, "scope": "RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX",
        "sourceAsOf": "2026-11-04T22:55:00+00:00",
        "summary": {"researchNcts": len(trials)},
        "records": trials,
    }


def review(nct="NCT00000001", metric="post-1-1", finding="ABOVE_BENCHMARK",
           independentReview="AI_SOURCE_CROSSCHECKED"):
    return {
        "nctId": nct, "ticker": "ABC",
        "stage": "post", "metricId": metric,
        "drug": "Drug X", "indication": "Condition A",
        "finding": finding, "independentReview": independentReview,
        "assessedAt": "2026-11-04", "sourceDate": "2026-11-01",
        "sourceUrl": "https://clinicaltrials.gov/study/" + nct,
        "benchmarkSourceUrl": "https://www.fda.gov/regulatory-information",
        "observedResult": "Observed comparator-reviewed effect with reported numerical confidence interval.",
        "uncertaintyReview": "Independent treatment benefit and missingness remain to be established.",
        "criticalRiskReview": "No approval success or superiority inferred.",
    }


def feed(items):
    return {
        "schemaVersion": 1,
        "scope": "RAAS_EXPLICIT_METRIC_REVIEWS_RESEARCH_ONLY",
        "sourceAsOf": "2026-11-04", "records": items,
    }


class PartialMetricRatingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = mod.CATALOG.read_text(encoding="utf8")

    def test_catalog_matches_six_groups_each_stage_and_no_overweighting(self):
        result = mod.metric_weights(self.spec)
        self.assertEqual(set(result), {"pre", "post"})
        for stage in ("pre", "post"):
            self.assertEqual(len(result[stage]), 30)
            self.assertAlmostEqual(sum(result[stage].values()), 100)
            self.assertEqual(result[stage][f"{stage}-1-1"], 5)
            self.assertEqual(result[stage][f"{stage}-6-5"], 1)

    def test_unknown_metrics_unscored_no_fake_predictions_or_overall(self):
        rows, status = mod.build(index([trial()]), feed([]), self.spec)
        self.assertEqual(len(rows), 2)
        self.assertEqual(status["researchTrials"], 1)
        self.assertEqual(status["reviewedMetricRecords"], 0)
        self.assertEqual(status["fullValidatedRaasScores"], 0)
        self.assertEqual(status["calibratedFdaPredictions"], 0)
        for row in rows:
            self.assertEqual(row["metricReviewsOf30"], 0)
            self.assertEqual(row["weightedMetricCoveragePct"], 0)
            self.assertEqual(row["observedMeanOnlyOnReviewedMetrics"], "")
            self.assertEqual(row["unscoredMetricCountOf30"], 30)
            self.assertEqual(row["full30MetricRaasScore"], "")
            self.assertEqual(row["fdaPassCrlExtensionProbability"], "")
            self.assertEqual(row["eligibleActive300mTo10bPipeline"], "NOT_VERIFIED")

    def test_observed_mean_denominator_is_only_reviewed_weights(self):
        records = [review(metric="post-1-1"),
                   review(metric="post-1-2", finding="MIXED_EVIDENCE")]
        rows, status = mod.build(index([trial()]), feed(records), self.spec)
        post = next(row for row in rows if row["stage"] == "POST_RESEARCH_ONLY")
        self.assertEqual(post["metricReviewsOf30"], 2)
        self.assertEqual(post["aiCrosscheckedMetricsOf30"], 2)
        self.assertEqual(post["weightedMetricCoveragePct"], 10)
        self.assertEqual(post["reviewedMetricContributionOf100"], 6.25)
        self.assertEqual(post["observedMeanOnlyOnReviewedMetrics"], 62.5)
        self.assertEqual(post["unscoredMetricCountOf30"], 28)
        self.assertEqual(post["gradedMetricIdAndScorePairs"], "post-1-1:75;post-1-2:50")
        self.assertEqual(post["full30MetricRaasScore"], "")
        self.assertEqual(status["trialStageRowsWithActualProvisionalMetricScores"], 1)
        self.assertEqual(status["uniqueNctsWithActualProvisionalMetricScores"], 1)

    def test_extra_metric_does_not_become_overall_score(self):
        records = [review(metric=f"post-{cat}-{item}")
                   for cat in range(1, 7) for item in range(1, 6)]
        rows, status = mod.build(index([trial()]), feed(records), self.spec)
        post = next(row for row in rows if row["stage"] == "POST_RESEARCH_ONLY")
        self.assertEqual(post["metricReviewsOf30"], 30)
        self.assertEqual(post["weightedMetricCoveragePct"], 100)
        self.assertEqual(post["observedMeanOnlyOnReviewedMetrics"], 75)
        # Registry alone cannot verify historical time point or external model validation.
        self.assertEqual(post["full30MetricRaasScore"], "")
        self.assertEqual(status["fullValidatedRaasScores"], 0)

    def test_mismatched_ticker_and_source_rejected(self):
        row = trial()
        with self.assertRaisesRegex(ValueError, "REVIEW_CROSS_TRIAL"):
            mod.build(index([row]), feed([{**review(), "ticker": "FAKE"}]), self.spec)
        with self.assertRaisesRegex(ValueError, "REVIEW_EVIDENCE"):
            mod.build(index([row]), feed([{**review(), "sourceUrl": "not-a-url"}]), self.spec)

    def test_ambiguous_program_does_not_inherit_other_drug_grades(self):
        a = review(metric="post-1-1")
        b = {**review(metric="post-1-2"), "drug": "Drug Y"}
        with self.assertRaisesRegex(ValueError, "REVIEW_OR_COHORT_PARITY"):
            mod.build(index([trial()]), feed([a, b]), self.spec)

    def test_duplicate_exact_trial_source_rejected(self):
        a = trial()
        with self.assertRaisesRegex(ValueError, "TRIAL_IDENTITY"):
            mod.build(index([a, a]), feed([]), self.spec)

    def test_spreadsheet_safe_and_actual_live_762_research_population(self):
        if not mod.INDEX.exists() or not mod.REVIEWS.exists():
            self.skipTest("Live review source not present")
        idx = json.loads(mod.INDEX.read_text(encoding="utf8"))
        reviewed = json.loads(mod.REVIEWS.read_text(encoding="utf8"))
        text, status_text = mod.generate(idx, reviewed, self.spec)
        rows = list(csv.DictReader(io.StringIO(text)))
        status = json.loads(status_text)
        self.assertEqual(len(rows), 2 * idx["summary"]["researchNcts"])
        self.assertEqual(status["reviewedMetricRecords"], len(reviewed["records"]))
        unique_ncts = {r["nctId"] for r in reviewed["records"]}
        unique_stage_rows = {(r["nctId"], r["stage"]) for r in reviewed["records"]}
        self.assertEqual(status["uniqueNctsWithActualProvisionalMetricScores"], len(unique_ncts))
        self.assertEqual(status["trialStageRowsWithActualProvisionalMetricScores"], len(unique_stage_rows))
        self.assertEqual(status["reviewedMetricRecords"], len(reviewed["records"]))
        self.assertGreaterEqual(status["reviewedMetricRecords"], 36)
        self.assertEqual(status["totalIndependentMetricReviews"], 0)
        self.assertEqual(status["fullValidatedRaasScores"], 0)
        self.assertTrue(all(x["full30MetricRaasScore"] == "" for x in rows))
        self.assertTrue(all(x["fdaPassCrlExtensionProbability"] == "" for x in rows))
        self.assertEqual(mod._excel_safe("=2+2"), "'=2+2")


if __name__ == "__main__":
    unittest.main()
