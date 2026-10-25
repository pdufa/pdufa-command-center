"""Avoid false FDA source conflicts during independent PDUFA claim rechecks."""
import unittest
import csv
import json
import tempfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from scripts.targeted_verification_repair import fresh_result, run


class FakeVerifier:
    def __init__(self, expected="2026-11-01", status="VERIFIED"):
        self.expected = expected
        self.status = status

    def regulatory(self, event):
        return [{
            "event_key": event["event_key"],
            "ticker": event["ticker"],
            "category": "FDA",
            "claim": "PDUFA_TARGET",
            "verification_status": self.status,
            "expected": self.expected,
            "observed": self.expected,
            "reason": "Exact source verified",
            "source_url": "https://example.org/issuer-release",
            "source_sha256": "f" * 64,
            "checked_at": "2026-10-15T02:20:00+00:00",
            "evidence": "Verified program and matching date",
        }]


class TargetedFdaRecheckTests(unittest.TestCase):
    EVENT = {"event_key": "AGIO|MITAPIVAT_SCD_20261101", "ticker": "AGIO"}

    def row(self, expected, status="REVIEW_REQUIRED"):
        return {
            "event_key": self.EVENT["event_key"],
            "ticker": "AGIO",
            "category": "FDA",
            "claim": "PDUFA_TARGET",
            "expected": expected,
            "verification_status": status,
        }

    def test_disease_name_in_saved_expected_is_not_a_calendar_date_conflict(self):
        for previous in ("sickle cell disease", "Duchenne muscular dystrophy (DMD)",
                         "recurrent respiratory papillomatosis (RRP)", "UNVERIFIED", ""):
            with self.subTest(previous=previous):
                found = fresh_result(FakeVerifier(), self.EVENT, self.row(previous))
                self.assertEqual(found["verification_status"], "VERIFIED")

    def test_comparable_saved_date_mismatch_still_causes_conflict(self):
        different = fresh_result(FakeVerifier(), self.EVENT, self.row("2026-11-08"))
        self.assertEqual(different["verification_status"], "CONFLICT")
        same = fresh_result(FakeVerifier(), self.EVENT, self.row("2026-11-01"))
        self.assertEqual(same["verification_status"], "VERIFIED")

    def test_previous_primary_date_conflict_is_not_silently_removed(self):
        found = fresh_result(FakeVerifier(), self.EVENT,
                             self.row("sickle cell disease", status="CONFLICT"))
        self.assertEqual(found["verification_status"], "CONFLICT")
        self.assertIn("separate reconciliation", found["reason"])

    def test_fresh_verifier_conflict_is_not_suppressed(self):
        found = fresh_result(FakeVerifier(status="CONFLICT"), self.EVENT,
                             self.row("sickle cell disease"))
        self.assertEqual(found["verification_status"], "CONFLICT")


class TargetedSecRegistryRecheckTests(unittest.TestCase):
    def test_exact_registry_inventory_is_rechecked_without_a_program_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            data.mkdir()
            def csvfile(name, entries):
                with (data / name).open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.DictWriter(stream, fieldnames=entries[0].keys())
                    writer.writeheader()
                    writer.writerows(entries)
            csvfile("pdufa_candidates.csv", [
                {"event_key": "ABC|DRUG", "ticker": "ABC", "drug": "TestDrug"},
            ])
            csvfile("company_registry.csv", [
                {"ticker": "QNCX", "company": "Quince Therapeutics",
                 "cik10": "0001662774"},
            ])
            original = {"event_key": "REGISTRY:QNCX", "ticker": "QNCX",
                        "category": "SEC", "claim": "FILINGS_INVENTORY",
                        "verification_required": "YES", "verification_status": "CONFLICT"}
            csvfile("pdufa_source_review_queue.csv", [original])
            (data / "pdufa_source_report.json").write_text(json.dumps({
                "latest_run_id": "12345", "full_coverage_verified": False,
                "required_findings_unresolved": 1,
            }))
            args = Namespace(root=root, data_dir=data, source_run_id="12345",
                             output=root / "result.json", csv_output=root / "result.csv",
                             scan_report=None)

            def unresolved(self, company):
                return {
                    "event_key": company["event_key"],
                    "ticker": company["ticker"], "category": "SEC",
                    "claim": "FILINGS_INVENTORY", "verification_status": "CONFLICT",
                    "reason": "SEC response ticker differs from current registry",
                    "source_url": "https://data.sec.gov/submissions/CIK0001662774.json",
                    "source_sha256": "a" * 64,
                    "checked_at": "2026-10-25T16:00:00Z",
                    "evidence": "Conflicted issuer identity",
                    "expected": "", "observed": "",
                }
            with patch("scripts.targeted_verification_repair.Verifier.registry", unresolved):
                report = run(args)
            self.assertEqual(report["findings_due"], 1)
            self.assertEqual(report["required_findings_unresolved"], 1)
            self.assertEqual(report["findings_verified"], 0)
            item = list(csv.DictReader(args.csv_output.open()))[0]
            self.assertEqual(item["event_key"], "REGISTRY:QNCX")
            self.assertEqual(item["fresh_status"], "CONFLICT")
            self.assertEqual(item["resolution"], "HOLD_UNRESOLVED")
            original["ticker"] = "TBPH"  # Identity conflict must fail closed.
            csvfile("pdufa_source_review_queue.csv", [original])
            with self.assertRaisesRegex(ValueError, "SEC registry identity"):
                run(args)


if __name__ == "__main__":
    unittest.main()
