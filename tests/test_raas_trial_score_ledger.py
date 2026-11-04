"""Regression tests for all-trial RAAS source-based diagnostic ledger.

Never interpret a study design score as a validated RAAS clinical/FDA score.
"""
import csv
import importlib.util
import io
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "raas_trial_score_ledger", ROOT / "scripts/raas_trial_score_ledger.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def trial(nct, ticker, *, posted=False, design=None, primary=True):
    return {
        "nctId": nct, "ticker": ticker,
        "sourceUrl": "https://clinicaltrials.gov/study/" + nct,
        "registryStatus": "COMPLETED" if posted else "RECRUITING",
        "evidenceState": "POSTED_RESULTS_UNGRADED" if posted else "PROTOCOL_ONLY",
        "postedResults": posted,
        "registeredDesign": design or {},
        "registeredInterventions": ["Drug A", "Placebo"] if posted else ["Drug A"],
        "primaryDefinitions": [{"measure": "Primary symptom endpoint", "timeFrame": "Week 12"}]
                              if primary else [],
        "primaryResults": [{"analysisCount": 1, "measurements": [{"value": "1"}]}]
                          if posted else [],
        "postedPrimaryOutcomeCount": 1 if posted else 0,
        "seriousAdverseEventTermCount": 1 if posted else 0,
    }


def index(records):
    return {
        "schemaVersion": 1, "scope": "RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX",
        "sourceAsOf": "2026-11-04T21:26:09+00:00",
        "summary": {"researchNcts": len(records)},
        "records": records
    }


def reviews(records=None):
    return {"schemaVersion": 1, "scope": "RAAS_EXPLICIT_METRIC_REVIEWS_RESEARCH_ONLY",
            "records": records or []}


class LedgerTests(unittest.TestCase):
    def test_numeric_design_parity_four_registered_facets(self):
        r = trial("NCT00000001", "AAA", posted=True, design={
            "allocation": "RANDOMIZED", "masking": "DOUBLE",
            "interventionModel": "PARALLEL"
        })
        self.assertEqual(mod.source_design_diagnostic(r),
                         {"score": 100, "known": 4, "unknown": 0,
                          "lowerBound": 100, "upperBound": 100})

    def test_unknown_design_is_not_numeric_zero(self):
        r = trial("NCT00000001", "AAA", primary=False)
        x = mod.source_design_diagnostic(r)
        self.assertIsNone(x["score"])
        self.assertEqual(x["known"], 0)
        self.assertEqual(x["lowerBound"], 0)
        self.assertEqual(x["upperBound"], 100)

    def test_known_limitations_score_as_observed_without_inventing_other_facets(self):
        r = trial("NCT00000001", "AAA", design={
            "allocation": "NON_RANDOMIZED", "masking": "NONE",
            "interventionModel": "SINGLE_GROUP"
        })
        x = mod.source_design_diagnostic(r)
        self.assertEqual(x["known"], 4)
        self.assertEqual(x["score"], 25)
        self.assertEqual(x["lowerBound"], 25)
        self.assertEqual(x["upperBound"], 25)

    def test_all_trials_have_a_row_and_missing_composite_stays_blank(self):
        a = trial("NCT00000001", "AAA", posted=True, design={
            "allocation": "RANDOMIZED", "masking": "QUADRUPLE",
            "interventionModel": "PARALLEL"
        })
        b = trial("NCT00000002", "BBB", primary=False)
        text, status = mod.generate(index([a, b]), reviews())
        rows = list(csv.DictReader(io.StringIO(text)))
        import json
        summary = json.loads(status)
        self.assertEqual(len(rows), 2)
        self.assertEqual(summary["researchTrials"], 2)
        self.assertEqual(summary["trialStageReviewRows"], 4)
        self.assertEqual(summary["trialsWithNumericSourceDesignDiagnostic"], 1)
        self.assertEqual(rows[0]["designDiagnosticScore"], "100")
        self.assertEqual(rows[1]["designDiagnosticScore"], "")
        self.assertTrue(all(row["fullValidatedRaasScore"] == "" for row in rows))
        self.assertEqual(summary["fullyValidatedRaasScoresInLedger"], 0)
        self.assertEqual(rows[0]["topRegistryLeadWeightPct"], "5")
        self.assertEqual(rows[0]["bottomRegistryLeadWeightPct"], "15")

    def test_ai_review_is_not_silently_independent(self):
        r = trial("NCT00000001", "AAA", posted=True)
        candidate = {
            "nctId": r["nctId"], "ticker": r["ticker"],
            "stage": "post", "metricId": "post-1-1",
            "drug": "Drug A", "indication": "Trial condition",
            "independentReview": "AI_SOURCE_CROSSCHECKED"
        }
        rows, summary = mod.build_ledger(index([r]), reviews([candidate]))
        self.assertEqual(rows[0]["bottomAiSourceCrosschecks"], 1)
        self.assertEqual(rows[0]["bottomIndependentMetricReviewsOf30"], 0)
        self.assertEqual(summary["aiSourceCrosscheckedMetricReviews"], 1)
        self.assertEqual(summary["independentMetricReviews"], 0)
        self.assertEqual(rows[0]["fullValidatedRaasScore"], "")

    def test_duplicate_nct_rejected(self):
        a = trial("NCT00000001", "AAA")
        with self.assertRaises(ValueError):
            mod.build_ledger(index([a, a]), reviews())

    def test_live_source_all_762_ncts_are_in_one_output_when_present(self):
        import json
        if not mod.INDEX.exists():
            self.skipTest("Source snapshot not checked out")
        source = json.loads(mod.INDEX.read_text(encoding="utf-8"))
        saved = json.loads(mod.REVIEWS.read_text(encoding="utf-8"))
        rows, summary = mod.build_ledger(source, saved)
        self.assertEqual(len(rows), summary["researchTrials"])
        self.assertEqual(len({row["nctId"] for row in rows}), len(rows))
        self.assertEqual(summary["trialStageReviewRows"], 2 * len(rows))
        self.assertTrue(all(row["fullValidatedRaasScore"] == "" for row in rows))
        self.assertTrue(any(isinstance(row["designDiagnosticScore"], int)
                            for row in rows))


if __name__ == "__main__":
    unittest.main()
