"""Baseline-first #2/#3/#4 inventory must never be mistaken for live scanning."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.scan_234_preflight import build_report, file_audit


class BaselineFirstPreflightTests(unittest.TestCase):
    def make_setup(self, root):
        (root / "config").mkdir(parents=True)
        (root / "data").mkdir(parents=True)
        plan = {
            "tabs": [
                {"id": 2, "name": "PIPELINE",
                 "source_files": ["company_registry.csv", "all_phase_trials.csv"]},
                {"id": 3, "name": "PRE3",
                 "source_files": ["all_phase_trials.csv", "phase2_primary_pvalues.csv"]},
                {"id": 4, "name": "POST3",
                 "source_files": ["pdufa_candidates.csv", "phase3_primary_pvalues.csv"]},
            ],
            "universe_sources": ["data/company_registry.csv", "data/all_phase_trials.csv"],
            "shared_source_families": [
                {"name": "clinicaltrials", "required": True},
                {"name": "sec", "required": True},
            ],
        }
        (root / "config" / "scan_234.json").write_text(json.dumps(plan))
        return plan

    @staticmethod
    def write_csv(path, records):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["ticker", "nct_id"])
            writer.writeheader()
            writer.writerows(records)

    def test_preflight_is_never_complete_even_when_every_csv_exists(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan = self.make_setup(root)
            for filename in {
                name for tab in plan["tabs"] for name in tab["source_files"]
            }:
                self.write_csv(root / "data" / filename,
                               [{"ticker": "ABC", "nct_id": "NCT12345678"}])
            report = build_report(root)
            self.assertEqual(report["status"], "INPUTS_PRESENT_SOURCE_SCAN_PENDING")
            self.assertFalse(report["baseline_verified"])
            self.assertFalse(report["nightly_automation_enabled"])
            self.assertEqual(report["external_network_requests_made"], 0)
            self.assertEqual(report["registry_rows_saved_not_reverified"], 1)
            self.assertEqual(len(report["tabs"]), 3)
            self.assertTrue(all(not item["baseline_verified"] for item in report["tabs"]))
            self.assertIn("sec", report["missing_required_source_families"])

    def test_missing_required_csv_blocks_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.make_setup(root)
            self.write_csv(root / "data" / "company_registry.csv",
                           [{"ticker": "ABC", "nct_id": ""}])
            report = build_report(root)
            self.assertEqual(report["status"], "MISSING_INPUT_FILES")
            self.assertIn("all_phase_trials.csv", report["universe_files_missing"])
            self.assertTrue(report["tabs"][2]["missing_or_invalid_files"])
            self.assertFalse(report["baseline_verified"])

    def test_source_checksum_changes_when_rows_change(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "snapshot.csv"
            self.write_csv(path, [{"ticker": "ABC", "nct_id": "NCT12345678"}])
            first = file_audit(path)
            self.write_csv(path, [{"ticker": "DEF", "nct_id": "NCT87654321"}])
            second = file_audit(path)
            self.assertNotEqual(first["sha256"], second["sha256"])
            self.assertEqual(first["records"], second["records"])
            self.assertEqual(first["state"], "PRESENT_UNVERIFIED")

    def test_invalid_tab_order_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            config = self.make_setup(root)
            config["tabs"].reverse()
            (root / "config" / "scan_234.json").write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                build_report(root)


if __name__ == "__main__":
    unittest.main()
