import csv
import tempfile
import unittest
from pathlib import Path
from research.fda_existing_history_audit import audit_legacy_history


class LegacyHistoryAuditTests(unittest.TestCase):
    def test_retrospective_legacy_predictions_are_not_verified_labels(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "history.csv"
            with p.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["ticker", "pdufa_date", "actual_outcome", "validation_period", "independence_status"])
                writer.writeheader()
                writer.writerow({"ticker": "TEST", "pdufa_date": "2025-01-01", "actual_outcome": "APPROVED", "validation_period": "RETROSPECTIVE", "independence_status": "NOT_BLIND"})
            result = audit_legacy_history(p)
            self.assertEqual(result["total_candidates"], 1)
            self.assertEqual(result["eligible_for_further_review"], 0)
            self.assertFalse(result["legacy_predictions_validated_by_this_audit"])
            self.assertIsNone(result["approval_rate"])


if __name__ == "__main__":
    unittest.main()
