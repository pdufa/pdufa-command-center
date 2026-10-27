"""Read-only census audit regression tests (standard library only)."""
import csv
import tempfile
import unittest
from pathlib import Path
from scripts.trial_census_identity_audit import audit_csv


class CensusIdentityAuditTests(unittest.TestCase):
    def audit(self, rows, header="nct_id"):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trials.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([header, "status"])
                writer.writerows((value, "UNKNOWN") for value in rows)
            return audit_csv(str(path))

    def test_valid_unique_trial_ids(self):
        result = self.audit(["NCT05535946", "NCT05507216"])
        self.assertEqual(result["counts"]["rows"], 2)
        self.assertEqual(result["counts"]["unique_valid_nct"], 2)
        self.assertEqual(result["counts"].get("duplicate_nct", 0), 0)

    def test_missing_invalid_and_duplicate(self):
        result = self.audit(["NCT05535946", "NCT05535946", "", "NCT123", "NCT05507216"])
        self.assertEqual(result["counts"]["rows"], 5)
        self.assertEqual(result["counts"]["duplicate_nct"], 1)
        self.assertEqual(result["counts"]["missing_nct"], 1)
        self.assertEqual(result["counts"]["invalid_nct"], 1)
        self.assertEqual(result["counts"]["unique_valid_nct"], 2)

    def test_alternate_header(self):
        self.assertEqual(self.audit(["NCT05535946"], "trial_id")["counts"]["unique_valid_nct"], 1)

    def test_missing_column_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "No supported NCT"):
            self.audit(["NCT05535946"], "unrelated_column")


if __name__ == "__main__":
    unittest.main()
