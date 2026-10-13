"""PDUFA scan Gmail notification contract; entirely offline tests."""
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts.scan_email import (
    EmailSettings, EmailSetupError, EmailSendError,
    compose_start, compose_end, report_summary, send_email,
    place_self_sent_message_in_inbox,
)
from scripts.run_scan_with_email import run_scan


class ScanEmailTests(unittest.TestCase):
    TEST_ENV = {
        "PDUFA_GMAIL_USER": "testsender@gmail.com",
        "PDUFA_GMAIL_APP_PASSWORD": "testapppassword",
        "PDUFA_ALERT_EMAIL": "receiver@example.net",
    }

    def settings(self):
        return EmailSettings.from_env(self.TEST_ENV)

    def test_email_is_the_critical_channel_and_no_scanners_auto_start(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / "config/scan_234.json").read_text(encoding="utf-8"))
        policy = config["notification_policy"]
        self.assertEqual(policy["delivery_mode"], "EMAIL_TWO_PER_SCAN")
        self.assertEqual(policy["messages_per_scan"], 2)
        self.assertEqual(policy["priority"], "CRITICAL_REQUIRED_BEFORE_PRODUCTION")
        self.assertTrue(policy["start_email_required"])
        self.assertTrue(policy["end_email_attempted_on_success_and_failure"])
        self.assertFalse(policy["notifications_active"])
        self.assertFalse(config["automation_enabled"])
        self.assertFalse(policy["nightly_schedules_restored"])
        for name in ("overnight-pdufa.yml", "phase-pipeline.yml", "surveillance.yml"):
            self.assertFalse((root / ".github/workflows" / name).exists())
        manual_test = (root / ".github/workflows/email-delivery-test.yml").read_text()
        self.assertIn("workflow_dispatch:", manual_test)
        self.assertNotIn("schedule:", manual_test)

    def test_sender_and_recipient_are_required(self):
        with self.assertRaises(EmailSetupError):
            EmailSettings.from_env({})
        self.assertEqual(self.settings().recipient, "receiver@example.net")
        with self.assertRaises(EmailSetupError):
            EmailSettings.from_env({**self.TEST_ENV, "PDUFA_ALERT_EMAIL": "not-an-email"})

    def test_start_and_end_content(self):
        at = datetime(2026, 10, 12, 1, 0, tzinfo=timezone.utc)
        for key, label in [("2", "#2 PIPELINE"), ("3", "#3 PRE3"), ("4", "#4 POST3")]:
            subj, body = compose_start(key, "BASELINE", "abc123", at)
            self.assertIn("START", subj)
            self.assertIn(label, subj)
            self.assertIn("Run ID: abc123", body)
            subj, body = compose_end(
                key, "BASELINE", "abc123", at, "PARTIAL",
                "Companies checked: 690/717\nNew records: 4", 3600)
            self.assertIn("END", subj)
            self.assertIn("PARTIAL", subj)
            self.assertIn("Companies checked: 690/717", body)
            self.assertIn("New records: 4", body)
            self.assertIn("60.0 minutes", body)

    def test_smtp_send_once_and_no_credentials_leak(self):
        settings = self.settings()
        sent = []
        class FakeSMTP:
            def __init__(self, host, port, timeout, context):
                self.host = host
                self.port = port

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def login(self, username, password):
                self.username = username
                self.password = password

            def send_message(self, email):
                sent.append(email)
                return {}
        result = send_email(settings, "[PDUFA] TEST", "body", smtp_factory=FakeSMTP)
        self.assertEqual(result["status"], "submitted_not_delivered")
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["To"], settings.recipient)
        self.assertNotIn(settings.app_password, str(result))

    def test_self_sent_notification_is_labeled_inbox_when_gmail_accepts(self):
        settings = EmailSettings("sample@gmail.com", "private-value", "sample@gmail.com")
        calls = []
        class FakeImap:
            def __init__(self, host, port, timeout):
                calls.append(("server", host, port))
            def login(self, sender, password):
                calls.append(("login", sender))
            def select(self, mailbox):
                calls.append(("select", mailbox))
                return "OK", [b"10"]
            def uid(self, command, *args):
                calls.append((command, *args))
                if command == "SEARCH":
                    return "OK", [b"101"]
                return "OK", [b""]
            def logout(self):
                calls.append(("logout",))
        status = place_self_sent_message_in_inbox(
            settings, "<example@localhost>", imap_factory=FakeImap)
        self.assertEqual(status, "INBOX_LABEL_ACCEPTED")
        self.assertTrue(any(row[0] == "STORE" and row[-1] == r"(\\Inbox)"
                            for row in calls))
        self.assertNotIn(settings.app_password, str(calls))

    def test_non_self_addressed_mail_never_accesses_imap(self):
        self.assertEqual(
            place_self_sent_message_in_inbox(
                self.settings(), "<external@test>",
                imap_factory=lambda *a, **kw: self.fail("IMAP must not start")),
            "EXTERNAL_RECIPIENT_NOT_CHECKED")

    def test_two_emails_on_success_and_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            status = root / "status.json"
            messages = []
            def sender(settings, subject, body):
                messages.append((subject, body))
                return {"status": "submitted_not_delivered"}
            def execute(cmd, cwd, check):
                status.write_text(json.dumps({
                    "status": "COMPLETE", "full_coverage_verified": True,
                    "companies_checked": 717, "companies_due": 717,
                    "new_records": 8, "candidate_field_changes": 4
                }))
                return SimpleNamespace(returncode=0)
            code, audit = run_scan(
                scan="2", mode="BASELINE", command=["mock"],
                status_file=status, audit_dir=root / "audit",
                settings=self.settings(), sender=sender, executor=execute)
            self.assertEqual(code, 0)
            self.assertEqual(len(messages), 2)
            self.assertIn("START", messages[0][0])
            self.assertIn("END", messages[1][0])
            self.assertIn("COMPLETE", messages[1][0])
            self.assertIn("Companies checked: 717/717", messages[1][1])
            self.assertEqual(audit["end_email"], "submitted_not_delivered")
            saved = json.loads((root / "audit" / (audit["run_id"] + ".json")).read_text())
            self.assertNotIn(self.settings().app_password, json.dumps(saved))

    def test_failed_run_still_emails_actual_status(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            status = root / "status.json"
            messages = []
            def execute(*_, **__):
                status.write_text(json.dumps({
                    "status": "PARTIAL",
                    "tracked_trials_checked": 23, "tracked_trials_total": 99,
                    "errors": ["FDA unavailable"]
                }))
                return SimpleNamespace(returncode=1)
            code, audit = run_scan(
                scan="3", mode="DELTA", command=["mock"],
                status_file=status, audit_dir=root / "audit",
                settings=self.settings(),
                sender=lambda _, subj, body: (messages.append((subj, body)) or {
                    "status": "submitted_not_delivered"}),
                executor=execute)
            self.assertEqual(code, 1)
            self.assertEqual(len(messages), 2)
            self.assertIn("PARTIAL", messages[1][0])
            self.assertIn("Trials checked: 23/99", messages[1][1])
            self.assertIn("Errors: 1", messages[1][1])

    def test_stale_report_is_not_declared_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            status = root / "status.json"
            status.write_text('{"status":"COMPLETE","full_coverage_verified":true}')
            messages = []
            code, audit = run_scan(
                scan="4", mode="DELTA", command=["mock"],
                status_file=status, audit_dir=root / "audit",
                settings=self.settings(),
                sender=lambda _, subj, body: (messages.append((subj, body)) or {
                    "status": "submitted_not_delivered"}),
                executor=lambda *_, **__: SimpleNamespace(returncode=0))
            self.assertEqual(code, 3)
            self.assertEqual(len(messages), 2)
            self.assertIn("UNVERIFIED", messages[1][0])
            self.assertFalse(audit["fresh_status_report"])

    def test_clinical_source_only_does_not_report_all_source_complete(self):
        status, summary = report_summary(
            {"status": "COMPLETE", "companies_checked": 717, "companies_due": 717},
            0, True, full_scope=True)
        self.assertEqual(status, "UNVERIFIED")
        self.assertIn("Full-source coverage", summary)

    def test_start_failure_prevents_scan(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            execute = Mock()
            def fail(*args):
                raise EmailSendError("SMTP blocked")
            code, audit = run_scan(
                scan="2", mode="DELTA", command=["mock"],
                status_file=root / "status.json", audit_dir=root / "audit",
                settings=self.settings(), sender=fail, executor=execute)
            self.assertEqual(code, 4)
            execute.assert_not_called()
            self.assertEqual(audit["end_email"], "NOT_SENT_SCAN_NOT_STARTED")

    def test_timeout_sends_end_failure_email(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            messages = []
            def hang(*args, **kwargs):
                self.assertEqual(kwargs["timeout"], 15)
                raise subprocess.TimeoutExpired(["mock"], 15)
            code, audit = run_scan(
                scan="4", mode="MANUAL", command=["mock"],
                timeout_seconds=15, status_file=root / "status.json",
                audit_dir=root / "audit", settings=self.settings(),
                sender=lambda _, subj, body: (messages.append((subj, body)) or {
                    "status": "submitted_not_delivered"}), executor=hang)
            self.assertEqual(code, 1)
            self.assertEqual(len(messages), 2)
            self.assertIn("FAILED", messages[1][0])
            self.assertIn("TimeoutExpired", messages[1][1])

    def test_settings_fail_closed_without_real_smtp_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(EmailSetupError):
                    run_scan(
                        scan="2", mode="DELTA", command=["mock"],
                        status_file=Path(folder) / "status.json",
                        audit_dir=Path(folder) / "audit",
                        settings=None, executor=Mock())


if __name__ == "__main__":
    unittest.main()
