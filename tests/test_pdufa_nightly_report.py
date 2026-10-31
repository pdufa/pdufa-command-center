"""Offline contracts for published clinical scan reports (no external network)."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import pdufa_scan_audit as audit


def sample_zip(scan="2", *, errors=None, report_status="PARTIAL"):
    errors = errors if errors is not None else []
    report = {
        "scan": scan, "scan_kind": "CLINICAL_SOURCE_COLLECTION_ONLY",
        "full_coverage_verified": False, "collector_status": "COMPLETE",
        "collector_exit_code": 0, "status": report_status,
        "errors_count": len(errors),
        "created_at_utc": "2026-10-12T09:00:00+00:00",
        "studies_checked": 10,
    }
    state = {"status": "COMPLETE", "errors": errors}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("reports/nightly-clinical-" + scan + ".json", json.dumps(report))
        archive.writestr("data/" + audit.SCANS[scan][1], json.dumps(state))
    return buf.getvalue()


def extract_test_archive(path, scan="2", errors=None):
    with zipfile.ZipFile(io.BytesIO(sample_zip(scan, errors=errors))) as archive:
        archive.extractall(path)


class NightlyScanAuditTests(unittest.TestCase):
    def test_valid_clinical_report_remains_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            extract_test_archive(folder)
            row = audit.inspect_artifact("2", {}, "fake", extracted_dir=folder)
        self.assertEqual(row["status"], "PARTIAL")
        self.assertEqual(row["artifact_integrity"], "PASS")
        self.assertEqual(row["metrics"]["studies_checked"], 10)
        self.assertIsNone(row["new_records"])

    def test_absent_archive_is_never_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            row = audit.inspect_artifact("4", {}, "fake", extracted_dir=folder)
        self.assertEqual(row["status"], "UNVERIFIED")
        self.assertEqual(row["artifact_integrity"], "FAILED")

    def test_reported_errors_are_checked_against_source(self):
        with tempfile.TemporaryDirectory() as folder:
            extract_test_archive(folder, errors=["source down"])
            row = audit.inspect_artifact("2", {}, "fake", extracted_dir=folder)
        self.assertEqual(row["errors_count"], 1)
        self.assertEqual(row["artifact_integrity"], "PASS")

    def test_archive_zip_is_valid_and_readable(self):
        blob = sample_zip()
        self.assertEqual(audit.archive_json(blob, "nightly-clinical-2.json")["scan"], "2")
        self.assertEqual(audit.archive_json(blob, audit.SCANS["2"][1])["status"], "COMPLETE")

    def test_large_pipeline_state_within_eight_megabytes_is_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            extract_test_archive(folder)
            source = Path(folder) / "data" / audit.SCANS["2"][1]
            state = json.loads(source.read_text(encoding="utf-8"))
            state["large_source_audit"] = "x" * (2 * 1024 * 1024)
            source.write_text(json.dumps(state), encoding="utf-8")
            self.assertGreater(source.stat().st_size, 1024 * 1024)
            self.assertLess(source.stat().st_size, audit.MAX_JSON)
            row = audit.inspect_artifact("2", {}, "fake", extracted_dir=folder)
        self.assertEqual(row["status"], "PARTIAL")
        self.assertEqual(row["artifact_integrity"], "PASS")

    def test_unknown_totals_do_not_turn_into_zero(self):
        self.assertIsNone(audit.verified_total(
            [{"new_records": None}, {"new_records": 0}], "new_records"))
        self.assertEqual(audit.verified_total(
            [{"new_records": 0}, {"new_records": 5}], "new_records"), 5)

    def test_successful_collector_does_not_certify_full_sources(self):
        run = {"conclusion": "success", "html_url": "https://github.com/example/actions/runs/8"}
        def mocked_api(path, token):
            if path.endswith("/artifacts?per_page=100"):
                return {"artifacts": [
                    {"name": "nightly-clinical-2-8", "archive_download_url": "https://example.test"}
                ]}
            return run
        with tempfile.TemporaryDirectory() as folder:
            location = Path(folder) / "nightly-clinical-2-8"
            location.mkdir()
            extract_test_archive(location)
            with patch.object(audit, "api", side_effect=mocked_api):
                result = audit.gather(8, "fake", artifacts_dir=folder)
        self.assertEqual(result["scope"], "CLINICAL_POOL_PIPELINE_AND_PHASE3_RESULTS_COLLECTORS_ONLY")
        self.assertEqual(result["verification"]["all_source_coverage"], "NOT_VERIFIED")
        self.assertNotEqual(result["status"], "COMPLETE")
        self.assertEqual(len(result["scans"]), 3)
        self.assertIsNone(result["metrics"]["new_records"])


if __name__ == "__main__":
    unittest.main()
