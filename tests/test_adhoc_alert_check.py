"""Regression tests for ad hoc error checks (offline, no Gmail/network)."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from adhoc_alert_check import current_issue, filter_headers, completed_scan_context
from unittest.mock import patch


class AdhocAlertTests(unittest.TestCase):
    def test_superseded_failure_does_not_raise_current_alert(self):
        old = {"id": 1, "created_at": "2026-10-12T12:00:00Z",
               "status": "completed", "conclusion": "failure"}
        fixed = {"id": 2, "created_at": "2026-10-12T13:00:00Z",
                 "status": "completed", "conclusion": "success"}
        self.assertIsNone(current_issue([old, fixed]))

    def test_current_failure_has_traceable_run(self):
        latest = {"id": 99, "created_at": "2026-10-12T13:00:00Z",
                  "status": "completed", "conclusion": "failure",
                  "html_url": "https://github.com/pdufa/pdufa-command-center/actions/runs/99"}
        found = current_issue([latest])
        self.assertEqual(found["id"], 99)
        self.assertIn("/runs/99", found["url"])

    def test_running_workflow_is_not_called_failure(self):
        run = {"id": 9, "created_at": "2026-10-12T13:00:00Z",
               "status": "in_progress", "conclusion": None}
        self.assertIsNone(current_issue([run]))

    def test_gmail_headers_only_in_time_window(self):
        recent = [{"Subject": "[PDUFA] END - PRE3", "Date": "Mon, 12 Oct 2026 14:00:00 +0000"},
                  {"Subject": "GitHub workflow failed", "Date": "Mon, 12 Oct 2026 14:15:00 +0000"},
                  {"Subject": "not relevant", "Date": "Mon, 12 Oct 2026 14:30:00 +0000"},
                  {"Subject": "[PDUFA] START - PRE3", "Date": "Sun, 11 Oct 2026 10:00:00 +0000"}]
        r = filter_headers(recent, datetime(2026, 10, 12, tzinfo=timezone.utc))
        self.assertEqual(r["relevant_messages"], 2)
        self.assertEqual(r["error_subjects"], 1)
        self.assertEqual(r["scan_end_subjects"], 1)
        self.assertEqual(r["scan_start_subjects"], 0)

    def test_completed_source_scan_is_linked_and_verified(self):
        source = {
            "id": 987, "name": "PDUFA Nightly Clinical Scans",
            "head_repository": {"full_name": "pdufa/pdufa-command-center"},
            "head_branch": "main", "status": "completed",
            "conclusion": "failure", "event": "schedule",
            "html_url": "https://github.com/pdufa/pdufa-command-center/actions/runs/987",
        }
        with patch("adhoc_alert_check.github_json", return_value=source) as request:
            result = completed_scan_context("synthetic-token", "987")
        self.assertTrue(result["needs_attention"])
        self.assertEqual(result["run_id"], 987)
        request.assert_called_once_with("/actions/runs/987", "synthetic-token")
        with patch("adhoc_alert_check.github_json",
                   return_value={**source, "conclusion": "success"}):
            self.assertFalse(completed_scan_context("synthetic-token", "987")["needs_attention"])

    def test_unapproved_scan_or_fork_rejected(self):
        good = {
            "id": 123, "name": "Step 7 PRE PHASE 3 Live Feed",
            "head_repository": {"full_name": "pdufa/pdufa-command-center"},
            "head_branch": "main", "status": "completed", "conclusion": "success",
        }
        for changes in ({"name": "Unknown workflow"},
                        {"head_repository": {"full_name": "other/fork"}},
                        {"head_branch": "not-main"},
                        {"status": "in_progress"}):
            with self.subTest(changes=changes):
                with patch("adhoc_alert_check.github_json", return_value={**good, **changes}):
                    with self.assertRaises(ValueError):
                        completed_scan_context("synthetic-token", "123")
        with self.assertRaises(ValueError):
            completed_scan_context("synthetic-token", "123/not-a-run")


if __name__ == "__main__":
    unittest.main()
