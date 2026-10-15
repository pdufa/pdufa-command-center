"""Offline tests for independent PDUFA workflow-run END notifications."""
import io
import json
import unittest
import zipfile
from datetime import datetime, timezone

from scripts.notify_completed_clinical_run import (
    _completion, _fetch_run, _job_for_scan, _report_from_artifact,
)


def artifact(report):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("scan_execution_report.json", json.dumps(report))
    return out.getvalue()


class ClinicalEndEmailTests(unittest.TestCase):
    RUN = {
        "name": "PDUFA One-Time Clinical Scan", "id": 38195214610,
        "status": "completed", "html_url":
            "https://github.com/pdufa/pdufa-command-center/actions/runs/38195214610",
        "run_started_at": "2026-10-12T02:17:44Z",
        "updated_at": "2026-10-12T02:22:51Z",
    }

    def test_collectors_not_claimed_all_source_complete(self):
        job = {"conclusion": "success", "started_at": "2026-10-12T02:17:45Z",
               "completed_at": "2026-10-12T02:22:50Z"}
        report = {
            "scan": "2", "status": "PARTIAL",
            "scan_kind": "CLINICAL_SOURCE_COLLECTION_ONLY",
            "collector_status": "COMPLETE",
            "companies_checked": 717, "companies_due": 717,
            "studies_checked": 15342,
            "new_records": 12, "errors": [],
        }
        status, subject, body = _completion("2", self.RUN, job, report)
        self.assertEqual(status, "PARTIAL")
        self.assertIn("END", subject)
        self.assertIn("PIPELINE — inventory", subject)
        self.assertIn("Companies checked: 717/717", body)
        self.assertIn("Registry studies checked: 15342", body)
        self.assertIn("FDA regulatory decisions", body)
        self.assertIn("NOT VERIFIED", body)
        self.assertIn("Run ID: 38195214610", body)

    def test_failed_collector_sends_failed_and_no_guessed_metrics(self):
        job = {"conclusion": "failure"}
        status, subject, body = _completion("3", self.RUN, job, None)
        self.assertEqual(status, "FAILED")
        self.assertIn("Fresh collector report unavailable", body)
        self.assertIn("PIPELINE — clinical enrichment", subject)

    def test_successful_run_missing_report_is_unverified(self):
        status, subject, body = _completion("4", self.RUN,
                                           {"conclusion": "success"}, None)
        self.assertEqual(status, "UNVERIFIED")
        self.assertIn("UNVERIFIED", subject)

    def test_zip_archive_only_uses_verified_manifest(self):
        report = {"scan": "4", "status": "PARTIAL"}
        self.assertEqual(_report_from_artifact(artifact(report)), report)
        with self.assertRaises((zipfile.BadZipFile, ValueError)):
            _report_from_artifact(b"not a zip")

    def test_duplicate_or_missing_jobs_are_not_misreported(self):
        self.assertIsNone(_job_for_scan([], "2"))
        jobs = [{"name": "PDUFA #2 PIPELINE", "conclusion": "success"}]
        self.assertEqual(_job_for_scan(jobs, "2")["conclusion"], "success")
        self.assertIsNone(_job_for_scan(jobs + jobs, "2"))

    def test_collector_completion_sends_exactly_three_summaries(self):
        token = "mock-token"
        repo = "pdufa/pdufa-command-center"
        run_id = "38195214610"
        base = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
        jobs = [{"name": "PDUFA #2 PIPELINE", "conclusion": "success"},
                {"name": "PDUFA #3 PRE3", "conclusion": "failure"},
                {"name": "PDUFA #4 POST3", "conclusion": "success"}]
        artifacts = [{"name": f"clinical-scan-{k}-{run_id}",
                      "archive_download_url": f"https://example.com/{k}.zip",
                      "expired": False} for k in ("2", "3", "4")]
        def fetch(url, supplied_token):
            self.assertEqual(supplied_token, token)
            if url == base:
                return self.RUN
            if url.endswith("/jobs?per_page=100"):
                return {"jobs": jobs}
            if url.endswith("/artifacts?per_page=100"):
                return {"artifacts": artifacts}
            raise AssertionError(url)
        def download(url, supplied_token):
            self.assertEqual(supplied_token, token)
            scan = url.rsplit("/", 1)[-1].split(".", 1)[0]
            return artifact({"scan": scan,
                             "scan_kind": "CLINICAL_SOURCE_COLLECTION_ONLY",
                             "status": "PARTIAL", "companies_checked": 10,
                             "companies_due": 717})
        emails = _fetch_run(repo, run_id, token, getter=fetch, downloader=download)
        self.assertEqual(len(emails), 3)
        self.assertEqual([x[0] for x in emails], ["2", "3", "4"])
        self.assertEqual([x[1] for x in emails], ["PARTIAL", "FAILED", "PARTIAL"])
        self.assertTrue(all("GitHub job outcome:" in x[3] for x in emails))

    def test_wrong_workflow_does_not_email(self):
        def fetch(url, token):
            return {**self.RUN, "name": "Unrelated CI"}
        with self.assertRaises(ValueError):
            _fetch_run("pdufa/pdufa-command-center", "38195214610", "x",
                       getter=fetch, downloader=lambda *_: b"")


if __name__ == "__main__":
    unittest.main()
