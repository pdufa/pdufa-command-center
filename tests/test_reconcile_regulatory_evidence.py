"""Regression tests for provenance-aware regulatory evidence reconciliation."""
import unittest
from scripts.reconcile_regulatory_evidence import reconcile_evidence


class RegulatoryEvidenceTests(unittest.TestCase):
    def test_bijuva_discrepancy_and_post_decision_leakage(self):
        result = reconcile_evidence([
            {"source": "clinicaltrials.gov", "source_url": "https://clinicaltrials.gov/study/NCT01942668",
             "metric": "endometrial_hyperplasia_rate_pct", "population": "1mg/100mg",
             "value": 0, "available_date": "2018-01-01"},
            {"source": "FDA adjudication", "source_url": "https://www.accessdata.fda.gov/",
             "metric": "endometrial_hyperplasia_rate_pct", "population": "1mg/100mg",
             "value": 0.36, "available_date": "2018-11-01"},
        ], decision_date="2018-10-28")
        self.assertTrue(result["has_discrepancy"])
        self.assertEqual(len(result["discrepancies"]), 1)
        self.assertEqual(len(result["pre_decision_records"]), 1)
        self.assertEqual(result["pre_decision_records"][0]["value"], 0)
        self.assertFalse(result["trading_ready"])

    def test_missing_date_fails_closed(self):
        result = reconcile_evidence([
            {"source": "trial", "metric": "efficacy", "population": "dose A", "value": 1}
        ], decision_date="2020-01-01")
        self.assertEqual(result["pre_decision_records"], [])
        self.assertEqual(result["records"][0]["exclusion_reason"], "missing_provenance_or_not_pre_decision")

    def test_distinct_populations_not_false_discrepancy(self):
        result = reconcile_evidence([
            {"source": "trial", "metric": "rate", "population": "ITT", "value": 0, "available_date": "2017-01-01"},
            {"source": "FDA", "metric": "rate", "population": "safety", "value": 1, "available_date": "2017-01-01"},
        ])
        self.assertFalse(result["has_discrepancy"])


if __name__ == "__main__":
    unittest.main()
