"""GEM Phase 3 intake must never publish incomplete or cross-issuer data."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.phase3_results_intake import FIELDS, scan


def registry(path):
    (path / "company_registry.csv").write_text(
        "ticker,company\nAAA,Example Biotechnology\n", encoding="utf-8"
    )


def study(nct="NCT01234567"):
    return {"protocolSection": {
        "statusModule": {"resultsFirstPostDateStruct": {"date": "2026-09-01"}},
        "identificationModule": {"nctId": nct},
        "sponsorCollaboratorsModule": {"leadSponsor": {
            "name": "Example Biotechnology"
        }},
        "designModule": {"phases": ["PHASE3"]},
        "armsInterventionsModule": {"interventions": [
            {"type": "DRUG", "name": "Test Drug"}]},
        "conditionsModule": {"conditions": ["Test Indication"]},
    }}


def ledger(path):
    with (path / "phase3_announcements.csv").open(
            newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class Phase3SafePublicationTests(unittest.TestCase):
    def test_complete_page_publishes_review_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);registry(p)
            with patch("scripts.phase3_results_intake.fetch",return_value={
                "studies":[study()]}):
                scan("daily", 2, p)
            saved=ledger(p)
            self.assertEqual(len(saved),1)
            self.assertEqual(saved[0]["source_type"],"CLINICALTRIALS_RESULTS")
            self.assertEqual(saved[0]["verification_status"],
                             "REGISTERED_RESULTS_POSTED")
            self.assertNotEqual(saved[0]["phase3_status"],"VERIFIED_SUCCESS")

    def test_page_budget_preserves_previous_good_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);registry(p)
            with patch("scripts.phase3_results_intake.fetch",return_value={
                "studies":[study()]}):
                scan("daily", 2, p)
            prior=(p/"phase3_announcements.csv").read_bytes()
            with patch("scripts.phase3_results_intake.fetch",return_value={
                "studies":[study("NCT99999999")],"nextPageToken":"MORE"}):
                with self.assertRaisesRegex(RuntimeError,"incomplete"):
                    scan("backfill", 1, p)
            self.assertEqual((p/"phase3_announcements.csv").read_bytes(),prior)
            status=json.loads((p/"phase3_intake_status.json").read_text())
            self.assertFalse(status["complete"])
            self.assertIn("Page budget exhausted",status["errors"][0])

    def test_duplicate_token_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);registry(p)
            with patch("scripts.phase3_results_intake.fetch",return_value={
                "studies":[study()],"nextPageToken":"SAME"}):
                with self.assertRaises(RuntimeError):
                    scan("daily",3,p)
            self.assertFalse((p/"phase3_announcements.csv").exists())

    def test_missing_registry_does_not_count_as_complete(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"registry"):
                scan("daily",1,Path(d))


if __name__ == "__main__":
    unittest.main()
