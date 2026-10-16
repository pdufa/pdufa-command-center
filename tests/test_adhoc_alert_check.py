"""Regression tests for ad hoc error checks (offline, no Gmail/network)."""
import sys
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from adhoc_alert_check import current_issue, filter_headers, completed_scan_context, audit_gmail
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

    def test_gmail_audit_checks_all_messages_in_batches_of_100(self):
        """A >150 message mailbox must not silently truncate; labels dedupe."""
        since = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
        calls = []

        class FakeIMAP:
            def __init__(self, host, timeout):
                self.folder = None
                self.readonly = []
            def login(self, username, password):
                return "OK", [b"logged in"]
            def select(self, folder, readonly=False):
                self.folder = folder
                self.readonly.append(readonly)
                return "OK", [b"250"]
            def uid(self, command, *args):
                if command == "SEARCH":
                    ids = range(1, 6) if self.folder == "INBOX" else (
                        range(1, 251) if self.folder == '"PDUFA"' else [])
                    return "OK", [b" ".join(str(x).encode() for x in ids)]
                self_assert = command == "FETCH"
                if not self_assert:
                    raise AssertionError("Expected only FETCH")
                batch = args[0].split(b",")
                calls.append((self.folder, len(batch), args[1]))
                if not 1 <= len(batch) <= 100:
                    raise AssertionError("Not bounded to batches of 100")
                rows = []
                for uid in batch:
                    n = int(uid)
                    header = (
                        f"Subject: [PDUFA] START {n}\\r\\n"
                        f"Date: Fri, 16 Oct 2026 13:00:00 +0000\\r\\n"
                        f"Message-ID: <pdufa-{n}@gmail.com>\\r\\n\\r\\n"
                    ).encode()
                    rows.append((b"1 (UID " + uid + b" X-GM-MSGID " +
                                 str(9000 + n).encode() + b")", header))
                return "OK", rows
            def logout(self):
                return "BYE", [b""]
        with patch("adhoc_alert_check.imaplib.IMAP4_SSL", FakeIMAP):
            report = audit_gmail("sender@gmail.com", "app-password", since)
        self.assertEqual(report["status"], "CHECKED")
        self.assertEqual(report["relevant_messages"], 250)
        self.assertEqual(report["scan_start_subjects"], 250)
        self.assertEqual([count for folder, count, _ in calls if folder == '"PDUFA"'],
                         [100, 100, 50])
        self.assertTrue(all("BODY.PEEK" in fmt for _, _, fmt in calls))

    def test_missing_header_in_batch_remains_partial(self):
        """Never report CHECKED when a requested Gmail header is missing."""
        since = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
        class FakeIMAP:
            def __init__(self, host, timeout):
                self.folder = ""
            def login(self, *args):
                return "OK", [b""]
            def select(self, folder, readonly=False):
                self.folder = folder
                return "OK", [b""]
            def uid(self, command, *args):
                if command == "SEARCH":
                    return "OK", [b"1 2"] if self.folder == '"PDUFA"' else [b""]
                data = []
                for uid in args[0].split(b","):
                    if uid == b"2":
                        continue
                    header = (
                        b"Subject: [PDUFA] END test\\r\\n"
                        b"Date: Fri, 16 Oct 2026 13:00:00 +0000\\r\\n"
                        b"Message-ID: <missing-one@gmail.com>\\r\\n\\r\\n"
                    )
                    data.append((b"1 (UID " + uid + b" X-GM-MSGID 7001)", header))
                return "OK", data
            def logout(self):
                pass
        with patch("adhoc_alert_check.imaplib.IMAP4_SSL", FakeIMAP):
            report = audit_gmail("sender@gmail.com", "app-password", since)
        self.assertEqual(report["status"], "PARTIAL")
        self.assertIn("incomplete header batch", report["reason"])
        self.assertEqual(report["relevant_messages"], 1)

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

    def test_awaited_parent_context_keeps_running_parent_distinct_from_finished_sources(self):
        from scripts.nightly_sequence import SOURCE_JOBS, SOURCE_TAILS, RUN_TITLE, WORKFLOW_PATH
        parent = {"id": 42, "name": RUN_TITLE, "display_title": RUN_TITLE, "path": WORKFLOW_PATH,
                  "head_repository": {"full_name": "pdufa/pdufa-command-center"},
                  "head_branch": "main", "status": "in_progress"}
        jobs = [{"name": "sources / " + name, "status": "completed", "conclusion": "success"}
                for name in SOURCE_JOBS + SOURCE_TAILS]
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "42", "PDUFA_SERIAL_STAGE_CONCLUSION": "success"}):
            with patch("adhoc_alert_check.github_json", side_effect=[parent, {"jobs": jobs}]):
                result = completed_scan_context("synthetic-token", "42")
        self.assertEqual(result["parent_status"], "in_progress")
        self.assertEqual(result["stage"], "sources")


if __name__ == "__main__":
    unittest.main()
