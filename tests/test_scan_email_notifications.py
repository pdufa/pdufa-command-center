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
    file_pdufa_notification,
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
        for key, label in [("2", "PIPELINE — inventory"), ("3", "PIPELINE — clinical enrichment"), ("4", "GEM JR — Phase 3 readout")]:
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

    def test_clinical_end_distinguishes_collection_from_overall_partial(self):
        at = datetime(2026, 10, 13, 3, 50, tzinfo=timezone.utc)
        for scan, collector in (("2", "COMPLETE"), ("3", "COMPLETE WITH WARNINGS"),
                                ("4", "COMPLETE")):
            subject, body = compose_end(
                scan, "DELTA", "run-123", at, "PARTIAL", "Errors: 0", 120,
                collector_status=collector)
            self.assertIn(f"CLINICAL {collector}", subject)
            self.assertIn("OVERALL PARTIAL", subject)
            self.assertIn("Clinical collection: " + collector, body)
            self.assertIn("Overall PDUFA source verification: PARTIAL", body)
            self.assertIn("Errors: 0", body)

    def test_incomplete_clinical_collector_never_labeled_complete(self):
        at = datetime(2026, 10, 13, 3, 50, tzinfo=timezone.utc)
        subject, _ = compose_end(
            "2", "DELTA", "run-123", at, "FAILED", "Collector failed", 12,
            collector_status="FAILED")
        self.assertIn("FAILED", subject)
        self.assertNotIn("CLINICAL COMPLETE", subject)

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

    def test_pdufa_notification_is_labeled_and_archived_without_resend(self):
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
        result = file_pdufa_notification(
            settings, "<example@localhost>", imap_factory=FakeImap)
        self.assertEqual(result, "PDUFA_LABEL_AND_ARCHIVE_ACCEPTED")
        stores = [c for c in calls if c[0] == "STORE"]
        self.assertEqual(stores, [
            ("STORE", b"101", "+X-GM-LABELS", "(PDUFA)"),
            ("STORE", b"101", "-X-GM-LABELS", r"(\Inbox)"),
        ])
        self.assertNotIn(settings.app_password, str(calls))

    def test_pdufa_label_is_added_to_script_sent_copy_with_external_recipient(self):
        # The sender's PDUFA folder also retains notifications to other recipients.
        settings = self.settings()
        class FakeImap:
            def __init__(self, *args, **kwargs):
                self.commands = []
            def login(self, *args):
                pass
            def select(self, *args):
                return "OK", [b"1"]
            def uid(self, command, *args):
                self.commands.append((command, *args))
                return ("OK", [b"12"] if command == "SEARCH" else [b""])
            def logout(self):
                pass
        imap = FakeImap()
        result = file_pdufa_notification(
            settings, "<outbound@sample>", imap_factory=lambda *a, **kw: imap)
        self.assertEqual(result, "PDUFA_LABEL_AND_ARCHIVE_ACCEPTED")
        self.assertIn(("STORE", b"12", "+X-GM-LABELS", "(PDUFA)"), imap.commands)

    def test_imap_filing_failure_does_not_resend_or_claim_archived(self):
        settings = self.settings()
        class FailedImap:
            def __init__(self, *args, **kwargs):
                self.store_calls = []
            def login(self, *args):
                pass
            def select(self, *args):
                return "OK", [b"1"]
            def uid(self, command, *args):
                if command == "SEARCH":
                    return "OK", [b"88"]
                self.store_calls.append((command, *args))
                if len(self.store_calls) == 2:
                    return "NO", [b"archive denied"]
                return "OK", [b""]
            def logout(self):
                pass
        imap = FailedImap()
        status = file_pdufa_notification(
            settings, "<justsent@sample>", imap_factory=lambda *a, **kw: imap)
        self.assertEqual(status, "LABEL_APPLIED_ARCHIVE_NOT_CONFIRMED")

    def test_actual_smtp_success_invokes_immediate_filing_once(self):
        settings = EmailSettings("sample@gmail.com", "secret", "sample@gmail.com")
        outgoing = []
        class FakeSMTP:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def login(self, *args):
                pass
            def send_message(self, message):
                outgoing.append(message["Message-ID"])
                return {}
        with patch("scripts.scan_email.smtplib.SMTP_SSL", FakeSMTP), \
                patch("scripts.scan_email.file_pdufa_notification",
                      return_value="PDUFA_LABEL_AND_ARCHIVE_ACCEPTED") as filed:
            response = send_email(settings, "[PDUFA] END - SEC", "done")
        self.assertEqual(len(outgoing), 1)
        filed.assert_called_once_with(settings, outgoing[0])
        self.assertEqual(response["filing_status"], "PDUFA_LABEL_AND_ARCHIVE_ACCEPTED")
        self.assertEqual(response["status"], "submitted_not_delivered")

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

    def test_verification_error_details_do_not_create_duplicate_error_count(self):
        status, summary = report_summary({
            "status": "PARTIAL",
            "execution_status": "COMPLETE_WITH_VERIFICATION_ERRORS",
            "errors_count": 4,
            "verification_technical_failure_count": 4,
            "errors": [
                "4 technical source verification failure(s); inspect the primary evidence review queue"
            ],
        }, 0, True)
        self.assertEqual(status, "PARTIAL")
        self.assertEqual(summary.count("Errors: 4"), 1)
        self.assertNotIn("Errors: 1", summary)
        self.assertIn("Error details: 4 technical source verification failure", summary)
        self.assertIn("Scan execution: COMPLETE_WITH_VERIFICATION_ERRORS", summary)

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

    def test_opt_in_dual_channel_sends_one_start_and_end_per_provider(self):
        from scripts.scan_sms import SMSSettings
        sms = SMSSettings("AC" + "a" * 32, "private-sms-token",
                          "+15035550101", "+15035550202")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            status = root / "status.json"
            events = []

            def email_sender(settings, subject, body):
                events.append(("email", "START" if "START" in subject else "END", body))
                return {"status": "submitted_not_delivered"}

            def sms_sender(settings, message):
                events.append(("sms", "START" if "START" in message else "END", message))
                return {"status": "submitted_not_delivered", "provider_message_id": "SMtest"}

            def collector(*_, **__):
                events.append(("scan", "", ""))
                status.write_text(json.dumps({
                    "status": "COMPLETE", "full_coverage_verified": True,
                    "companies_checked": 10, "companies_due": 10
                }))
                return SimpleNamespace(returncode=0)

            code, audit = run_scan(
                scan="2", mode="DELTA", command=["mock"],
                status_file=status, audit_dir=root / "audits",
                settings=self.settings(), sender=email_sender, executor=collector,
                require_sms=True, sms_settings=sms, sms_sender=sms_sender)
            self.assertEqual(code, 0)
            self.assertEqual([(kind, event) for kind, event, _ in events],
                             [("email", "START"), ("sms", "START"), ("scan", ""),
                              ("email", "END"), ("sms", "END")])
            self.assertEqual(audit["channel"], "EMAIL_AND_SMS")
            self.assertEqual(audit["start_sms"], "submitted_not_delivered")
            self.assertEqual(audit["end_sms"], "submitted_not_delivered")
            saved = (root / "audits" / (audit["run_id"] + ".json")).read_text()
            self.assertNotIn(sms.auth_token, saved)
            self.assertNotIn(self.settings().app_password, saved)

    def test_email_start_failure_does_not_attempt_sms_or_run_scanner(self):
        from scripts.scan_sms import SMSSettings
        sms = SMSSettings("AC" + "a" * 32, "private-token",
                          "+15035550101", "+15035550202")
        with tempfile.TemporaryDirectory() as folder:
            sms_sender, collector = Mock(), Mock()
            code, audit = run_scan(
                scan="2", mode="DELTA", command=["mock"],
                status_file=Path(folder) / "status.json",
                audit_dir=Path(folder) / "audit",
                settings=self.settings(), sender=Mock(side_effect=EmailSendError("SMTP unavailable")),
                executor=collector, require_sms=True,
                sms_settings=sms, sms_sender=sms_sender)
            self.assertEqual(code, 4)
            collector.assert_not_called()
            sms_sender.assert_not_called()
            self.assertEqual(audit["start_sms"], "NOT_SENT_SCAN_NOT_STARTED")
            self.assertEqual(audit["end_sms"], "NOT_SENT_SCAN_NOT_STARTED")


    def test_unconfigured_dual_channel_blocks_before_email_or_scan(self):
        with tempfile.TemporaryDirectory() as folder:
            sender, executor = Mock(), Mock()
            with patch.dict(os.environ, {}, clear=True):
                from scripts.scan_sms import SMSSetupError
                with self.assertRaises(SMSSetupError):
                    run_scan(
                        scan="2", mode="DELTA", command=["mock"],
                        status_file=Path(folder) / "status.json",
                        audit_dir=Path(folder) / "audit",
                        settings=self.settings(), sender=sender, executor=executor,
                        require_sms=True)
            sender.assert_not_called()
            executor.assert_not_called()

    def test_sms_start_failure_aborts_scan_and_emails_end_aborted(self):
        from scripts.scan_sms import SMSSettings, SMSSendError
        sms = SMSSettings("AC" + "a" * 32, "private-token",
                          "+15035550101", "+15035550202")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            messages, sms_attempts = [], []
            executor = Mock()
            def sms_fail(_settings, message):
                sms_attempts.append(message)
                raise SMSSendError("ambiguous provider acknowledgement")
            code, audit = run_scan(
                scan="3", mode="DELTA", command=["mock"],
                status_file=root / "status.json", audit_dir=root / "audit",
                settings=self.settings(),
                sender=lambda _, subject, body: (messages.append((subject, body)) or {
                    "status": "submitted_not_delivered"}),
                executor=executor, require_sms=True, sms_settings=sms, sms_sender=sms_fail)
            self.assertEqual(code, 4)
            executor.assert_not_called()
            self.assertEqual(len(sms_attempts), 1)
            self.assertEqual(len(messages), 2)
            self.assertIn("START", messages[0][0])
            self.assertIn("END", messages[1][0])
            self.assertEqual(audit["start_email"], "submitted_not_delivered")
            self.assertEqual(audit["end_sms"], "NOT_SENT_SCAN_NOT_STARTED")
            self.assertEqual(audit["coverage_status"], "FAILED")
            self.assertFalse(audit["scan_executed"])

    def test_sms_end_failure_does_not_resend_email_or_repeat_scan(self):
        from scripts.scan_sms import SMSSettings, SMSSendError
        sms = SMSSettings("AC" + "a" * 32, "private-token",
                          "+15035550101", "+15035550202")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            status = root / "status.json"
            messages, sms_attempts = [], []
            def collect_once(*_, **__):
                status.write_text('{"status":"PARTIAL"}')
                return SimpleNamespace(returncode=1)
            collector = Mock(side_effect=collect_once)
            def sms_sender(_settings, message):
                sms_attempts.append(message)
                if len(sms_attempts) == 2:
                    raise SMSSendError("unknown END receipt")
                return {"status": "submitted_not_delivered"}
            code, audit = run_scan(
                scan="4", mode="DELTA", command=["mock"],
                status_file=status, audit_dir=root / "audit",
                settings=self.settings(),
                sender=lambda _, subject, body: (messages.append((subject, body)) or {
                    "status": "submitted_not_delivered"}),
                executor=collector, require_sms=True, sms_settings=sms,
                sms_sender=sms_sender)
            self.assertEqual(code, 4)
            self.assertEqual(collector.call_count, 1)
            self.assertEqual(len(messages), 2)
            self.assertEqual(len(sms_attempts), 2)
            self.assertEqual(audit["end_sms"], "FAILED_OR_UNKNOWN")


    def test_nightly_sms_requires_explicit_verified_delivery_opt_in(self):
        root = Path(__file__).resolve().parents[1]
        clinical = (root / ".github/workflows/pdufa-nightly-clinical.yml").read_text()
        self.assertEqual(clinical.count('scripts/run_scan_with_email.py "${sms_opt[@]}"'), 3)
        self.assertEqual(clinical.count('sms_opt+=(--require-sms)'), 3)
        self.assertEqual(clinical.count('if [[ "${PDUFA_SMS_VERIFIED:-}" == "true" ]]'), 3)
        for secret in ("PDUFA_SMS_VERIFIED", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
                       "TWILIO_FROM_NUMBER", "PDUFA_SMS_TO_NUMBER"):
            self.assertEqual(clinical.count("secrets." + secret), 2)
        self.assertNotIn("scripts/run_scan_with_sms.py", clinical)

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
