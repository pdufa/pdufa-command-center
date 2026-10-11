"""Regression: SEC blocks and unreviewed text never clear Step 4 / Step 7."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import recheck_events as mod


class SecRecheckFailClosed(unittest.TestCase):
    def test_keyword_closing_text_is_not_verified_closure(self):
        source = {"financing_evidence_url": "https://www.sec.gov/Archives/edgar/data/123/ex99.htm"}
        html = "On October 1, 2026 the Company completed the financing transaction."
        with patch.object(mod, "get", return_value=html):
            result = mod.financing_check(source, [])
        self.assertEqual(result["status"], "CLOSURE_CLAUSE_FOR_REVIEW")
        self.assertFalse(result.get("closed"))
        self.assertIn("SEC", result.get("source", "").upper())

    def test_all_financing_filing_requests_failed(self):
        source = {"financing_evidence_url":"https://www.sec.gov/Archives/edgar/data/123/a.htm"}
        with patch.object(mod, "get", side_effect=PermissionError("HTTP 403")):
            result = mod.financing_check(source, [])
        self.assertEqual(result["status"], "SOURCE_BLOCKED_RETAINED")
        self.assertFalse(result.get("closed"))

    def test_partial_financing_filing_requests_failed(self):
        source = {"financing_evidence_url":"https://www.sec.gov/Archives/edgar/data/123/a.htm"}
        filings = [{"form":"8-K","url":"https://www.sec.gov/Archives/edgar/data/123/b.htm"}]
        with patch.object(mod, "get", side_effect=["Nothing about financing close", PermissionError("HTTP 403")]):
            result = mod.financing_check(source, filings)
        self.assertEqual(result["status"], "PARTIAL_SOURCE_REVIEW")
        self.assertFalse(result.get("closed"))

    def test_blocked_sec_counts_as_unsuccessful_run_and_cannot_change_closure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            candidate = root / "candidates.csv"
            status = root / "status.csv"
            original = {
                "event_key": "ABC|DRUG_20270101", "ticker": "ABC",
                "company": "Test Therapeutics", "drug": "Drug", "pdufa_date": "2027-01-01",
                "financing_status": "ANNOUNCED", "financing_evidence_url": "",
            }
            with candidate.open("w", newline="", encoding="utf-8") as stream:
                w = csv.DictWriter(stream, fieldnames=list(original))
                w.writeheader(); w.writerow(original)
            with patch.object(mod, "CAND", candidate), patch.object(mod, "STATUS", status), \
                 patch.object(mod, "cik_map", return_value={"ABC": "0000000001"}), \
                 patch.object(mod, "sec_filings", side_effect=PermissionError("SEC HTTP 403")), \
                 patch.object(sys, "argv", ["recheck_events.py", "--all", "--categories", "financing", "--no-sleep"]):
                mod.main()
            with candidate.open(newline="", encoding="utf-8") as stream:
                row = next(csv.DictReader(stream))
            with status.open(newline="", encoding="utf-8") as stream:
                check = next(csv.DictReader(stream))
            self.assertEqual(row["financing_status"], "ANNOUNCED")
            self.assertEqual(check["financing_status"], "SOURCE_BLOCKED_RETAINED")
            self.assertEqual(check["run_status"], "COMPLETED_WITH_ERRORS")
            self.assertFalse(check["last_successful_recheck_utc"])


if __name__ == "__main__":
    unittest.main()
