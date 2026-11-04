"""Test all-NCT TOP/BOTTOM source-review queue without inventing a RAAS score."""
import csv
import importlib.util
import io
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "scripts/raas_review_worklist.py"
SPEC = importlib.util.spec_from_file_location("raas_review_worklist", PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def trial(nct, ticker, posted=False, detailed=False):
    return {
        "nctId": nct, "ticker": ticker,
        "sourceUrl": "https://clinicaltrials.gov/study/" + nct,
        "evidenceState": "POSTED_RESULTS_UNGRADED" if posted else "PROTOCOL_ONLY",
        "postedResults": posted,
        "primaryDefinitions": [{"measure": "Prespecified endpoint"}],
        "primaryResults": [{
            "measurements": [{"groupId": "OG1", "value": "2.4"}],
            "comparisons": [{"groupIds": ["OG1", "OG2"],
                             "ciLowerLimit": "-2", "ciUpperLimit": "-1"}]
        }] if detailed else [],
        "seriousEventDetails": [{
            "groups": [{"numAffected": 1, "numAtRisk": 12}]
        }] if detailed else [],
    }


def index(records):
    return {
        "schemaVersion": 1, "scope": "RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX",
        "sourceAsOf": "2026-11-04T19:35:21Z",
        "summary": {"researchNcts": len(records)},
        "records": records,
    }


def reviews(records=None):
    return {
        "schemaVersion": 1, "scope": "RAAS_EXPLICIT_METRIC_REVIEWS_RESEARCH_ONLY",
        "records": [] if records is None else records,
    }


class ReviewWorklistTests(unittest.TestCase):
    def test_all_trials_get_both_stage_queues_even_without_verified_readout(self):
        roster = [trial("NCT00000001", "AAA", True, True),
                  trial("NCT00000002", "BBB", False, False)]
        rows, status = mod.build_worklist(index(roster), reviews())
        self.assertEqual(len(rows), 4)
        self.assertEqual(status["researchTrials"], 2)
        self.assertEqual(status["trialStageReviewRows"], 4)
        self.assertEqual(status["submittedMetricReviewRecords"], 0)
        self.assertEqual(status["aiSourceCrosscheckedGradeRecords"], 0)
        self.assertEqual(status["independentMetricReviewRecords"], 0)
        self.assertTrue(all(r["submittedMetricReviews"] == 0 and
                            r["missingMetricReviewCount"] == 30 and
                            r["stageIndependentlyVerified"] == "NOT_ASSESSED_IN_REGISTRY"
                            for r in rows))
        self.assertEqual(sum(r["sourceReviewPriority"].startswith("1_")
                             for r in rows), 1)
        detailed = next(r for r in rows if r["nctId"] == "NCT00000001"
                        and r["researchStage"] == "BOTTOM_RESEARCH_ONLY")
        self.assertTrue(detailed["hasPrimaryMeasurements"])
        self.assertTrue(detailed["hasGroupComparisons"])
        self.assertTrue(detailed["hasSafetyDenominators"])
        self.assertTrue(detailed["hasConfidenceIntervals"])
        self.assertEqual(detailed["missingMetricIds"].count(";"), 29)

    def test_submitted_review_is_never_mislabeled_validated_score(self):
        row = {"nctId": "NCT00000001", "ticker": "AAA", "stage": "post",
               "metricId": "post-1-1", "independentReview": "AI_SOURCE_CROSSCHECKED", "drug": "Example intervention",
               "indication": "Example indication"}
        csv_text, receipt = mod.generate(index([trial("NCT00000001", "AAA", True)]),
                                         reviews([row]))
        parsed = list(csv.DictReader(io.StringIO(csv_text)))
        bottom = next(r for r in parsed if r["researchStage"] == "BOTTOM_RESEARCH_ONLY")
        top = next(r for r in parsed if r["researchStage"] == "TOP_RESEARCH_ONLY")
        self.assertEqual(bottom["submittedMetricReviews"], "1")
        self.assertEqual(bottom["aiSourceCrosscheckedGrades"], "1")
        self.assertEqual(bottom["independentMetricReviews"], "0")
        self.assertEqual(bottom["missingMetricReviewCount"], "29")
        self.assertEqual(top["submittedMetricReviews"], "0")
        self.assertNotIn("fullResearchScore", receipt)
        self.assertNotIn("approvedOverallScore", receipt)

    def test_duplicate_or_cross_trial_reviews_rejected(self):
        row = {"nctId": "NCT00000001", "ticker": "BAD", "stage": "pre",
               "metricId": "pre-1-1", "independentReview": "PASSED", "drug": "Test", "indication": "Test"}
        with self.assertRaisesRegex(ValueError, "CROSS_TRIAL"):
            mod.build_worklist(index([trial("NCT00000001", "AAA")]), reviews([row]))
        row["ticker"] = "AAA"
        with self.assertRaisesRegex(ValueError, "DUPLICATE_REVIEW"):
            mod.build_worklist(index([trial("NCT00000001", "AAA")]), reviews([row, row]))

    def test_same_nct_different_drug_is_not_automatically_combined(self):
        a = {"nctId": "NCT00000001", "ticker": "AAA", "stage": "post",
             "metricId": "post-1-1", "independentReview": "PASSED", "drug": "Drug A", "indication": "Condition"}
        b = {**a, "drug": "Drug B", "metricId": "post-1-2"}
        rows, _ = mod.build_worklist(index([trial("NCT00000001", "AAA", True)]),
                                      reviews([a, b]))
        bottom = next(r for r in rows if r["researchStage"] == "BOTTOM_RESEARCH_ONLY")
        self.assertEqual(bottom["reviewIdentityState"], "AMBIGUOUS_PROGRAM")
        self.assertEqual(bottom["submittedMetricReviews"], 0)
        self.assertEqual(bottom["missingMetricReviewCount"], 30)

    def test_wrong_scope_and_duplicate_nct_fail_closed(self):
        i = index([trial("NCT00000001", "AAA")])
        i["scope"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "INDEX_SCOPE"):
            mod.build_worklist(i, reviews())
        i = index([trial("NCT00000001", "AAA"), trial("NCT00000001", "AAA")])
        with self.assertRaisesRegex(ValueError, "TRIAL_IDENTITY"):
            mod.build_worklist(i, reviews())


if __name__ == "__main__":
    unittest.main()
