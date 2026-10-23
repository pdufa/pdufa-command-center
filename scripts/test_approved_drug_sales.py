"""Regression tests for the curated financial sales ledger validator."""
import csv
import tempfile
import unittest
from pathlib import Path

from validate_approved_drug_sales import COLUMNS, PATH, validate


class FinancialLedgerTests(unittest.TestCase):
    def setUp(self):
        with PATH.open(newline="", encoding="utf-8-sig") as f:
            self.records = list(csv.DictReader(f))
        self.assertGreater(len(self.records), 0)

    def check_records(self, records):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sales.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(records)
            return validate(path)

    def test_current_ledger(self):
        self.assertEqual(self.check_records(self.records), len(self.records))

    def test_duplicate_record_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.check_records(self.records + [dict(self.records[0])])

    def test_inconsistent_ticker_company_rejected(self):
        changed = dict(self.records[0])
        changed["period"] = "Q1 2026"
        changed["company"] = "Incorrect Company"
        with self.assertRaisesRegex(ValueError, "multiple company names"):
            self.check_records(self.records + [changed])

    def test_invalid_reporting_period_rejected(self):
        changed = dict(self.records[0])
        changed["period"] = "2026"
        with self.assertRaisesRegex(ValueError, "unsupported reporting period"):
            self.check_records([changed])

    def test_nonfinite_sales_rejected(self):
        changed = dict(self.records[0])
        changed["individual_sales"] = "NaN"
        with self.assertRaisesRegex(ValueError, "invalid individual_sales"):
            self.check_records([changed])


if __name__ == "__main__":
    unittest.main()
