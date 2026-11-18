"""Regression checks for the unrestricted Level 1 audit."""
import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path
from scripts.audit_2026_unrestricted_level1 import audit, REQUIRED

def row(**changes):
    base = dict.fromkeys(REQUIRED, "")
    base.update(application_id="NDA123456", review_cycle="1", indication="Example indication",
                pdufa_date="2026-06-01", prediction="APPROVAL",
                prediction_frozen_at="2026-05-01T00:00:00Z",
                evidence_cutoff_at="2026-04-30T00:00:00Z",
                actual_outcome="APPROVAL",
                outcome_published_at="2026-06-01T00:00:00Z",
                source_url="https://www.fda.gov/example")
    base.update(changes)
    return base

def run(rows, expected=None):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "cohort.csv"
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=REQUIRED)
            writer.writeheader()
            writer.writerows(rows)
        return audit(path, date(2026, 11, 18), len(rows) if expected is None else expected)

class Level1AuditTests(unittest.TestCase):
    def test_correct_historical(self):
        result = run([row()])
        self.assertEqual(result["accuracy_pct"], 100.0)
        self.assertEqual(result["verified_comparisons"], 1)

    def test_incorrect_historical(self):
        result = run([row(actual_outcome="CRL")])
        self.assertEqual(result["accuracy_pct"], 0.0)

    def test_future_not_in_accuracy(self):
        result = run([row(pdufa_date="2026-12-15", actual_outcome="", outcome_published_at="")])
        self.assertEqual(result["future"], 1)
        self.assertIsNone(result["accuracy_pct"])

    def test_post_outcome_prediction_excluded(self):
        result = run([row(prediction_frozen_at="2026-06-02T00:00:00Z")])
        self.assertEqual(result["verified_comparisons"], 0)
        self.assertTrue(result["issues"])

    def test_duplicate_identity_flagged(self):
        result = run([row(), row()])
        self.assertFalse(result["complete"])
        self.assertTrue(any("duplicate" in issue["issue"] for issue in result["issues"]))

    def test_missing_source_flagged(self):
        result = run([row(source_url="")])
        self.assertFalse(result["complete"])

    def test_cohort_size_mismatch(self):
        result = run([row()], expected=196)
        self.assertFalse(result["complete"])

if __name__ == "__main__":
    unittest.main()
