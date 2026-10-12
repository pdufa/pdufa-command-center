"""Source-safe nightly score audit: status, provenance and fail-closed inputs."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.nightly_scoring_audit import build_report

GOOD = "PDUFA Nightly Scan Report Publisher"
EXTENDED = "PDUFA Nightly FDA SEC Financial Market Issuer Sources"


class NightlyScoringAuditTests(unittest.TestCase):
    def test_saved_input_gaps_are_review_not_fabricated_scores(self):
        report = build_report(".", source_run_id="123", source_workflow=GOOD,
                              source_conclusion="success")
        self.assertEqual(report["source_scan"]["run_id"], 123)
        self.assertEqual(report["source_scan"]["workflow"], GOOD)
        self.assertEqual(report["counts"]["models_mapped"], 9)
        self.assertEqual(report["counts"]["input_tests"], 6)
        self.assertIn(report["status"], ("REVIEW_REQUIRED", "NO_INPUT_GAPS_FOUND"))
        self.assertIn("not necessarily the fresh artifacts", report["provenance_note"].lower())

    def test_unavailable_source_data_never_passes(self):
        with TemporaryDirectory() as root:
            result = build_report(root, source_run_id="5", source_workflow=EXTENDED,
                                  source_conclusion="success")
            self.assertEqual(result["status"], "INPUTS_UNAVAILABLE")
            self.assertFalse(any(entry["file_present"] for entry in result["sources"]))

    def test_failed_scan_is_exposed_even_with_available_input_snapshots(self):
        report = build_report(".", source_run_id="127", source_workflow=EXTENDED,
                              source_conclusion="failure")
        self.assertEqual(report["status"], "SCAN_FAILURE")
        self.assertEqual(report["source_scan"]["conclusion"], "failure")

    def test_invalid_source_identity_and_result_rejected(self):
        for run_id in ("", "-1", "abc", "0"):
            with self.subTest(id=run_id), self.assertRaises(ValueError):
                build_report(".", source_run_id=run_id,
                             source_workflow=GOOD, source_conclusion="success")
        for source_name in ("PDUFA Command Center CI", "PDUFA Nightly Clinical Scans"):
            with self.subTest(source=source_name), self.assertRaises(ValueError):
                build_report(".", source_run_id="123",
                             source_workflow=source_name, source_conclusion="success")
        with self.assertRaises(ValueError):
            build_report(".", source_run_id="123", source_workflow=GOOD, source_conclusion="pending")


if __name__ == "__main__":
    unittest.main()
