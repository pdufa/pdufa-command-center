"""Two SMS notifications per scan, truthful summaries and safe failure modes."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs
from unittest.mock import Mock, patch
import os
import subprocess

from scripts.scan_sms import (
    SMSSettings, SMSSetupError, SMSSendError, begin_text, finish_text,
    single_sms, submit_sms, summarize_report,
)
from scripts.run_scan_with_sms import run_scan


class NotificationContractTests(unittest.TestCase):
    ENV = {
        "TWILIO_ACCOUNT_SID": "AC" + "1" * 32,
        "TWILIO_AUTH_TOKEN": "faketoken",
        "TWILIO_FROM_NUMBER": "+15035550100",
        "PDUFA_SMS_TO_NUMBER": "+15035550200",
    }

    def test_credentials_required_before_scanning(self):
        with self.assertRaises(SMSSetupError):
            SMSSettings.from_env({})
        s = SMSSettings.from_env(self.ENV)
        self.assertNotEqual(s.sender, s.recipient)
        with tempfile.TemporaryDirectory() as folder:
            called = Mock()
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(SMSSetupError):
                    run_scan(scan="2", mode="BASELINE", command=["fake"],
                             status_file=Path(folder) / "status.json",
                             audit_dir=Path(folder) / "audits",
                             settings=None, executor=called,
                             sender=Mock())
            called.assert_not_called()

    def test_messages_fit_exactly_one_ascii_sms_segment(self):
        at = datetime(2026, 10, 12, 0, 15, tzinfo=timezone.utc)
        for scan, name in (("2", "#2 PIPELINE"), ("3", "#3 PRE3"),
                           ("4", "#4 POST3"), ("SEC", "SEC")):
            start = begin_text(scan, "BASELINE", "abcdef12-abc", at)
            end = finish_text(scan, "BASELINE", "abcdef12-abc", "PARTIAL",
                              "records 717/717; changed 4; errors 2", 453.4)
            self.assertIn(name, start)
            self.assertIn(name, end)
            self.assertIn("START", start)
            self.assertIn("END: PARTIAL", end)
            for message in (start, end):
                self.assertTrue(message.isascii())
                self.assertLessEqual(len(message), 155)
        self.assertLessEqual(len(single_sms("X" * 10000)), 155)

    def test_provider_request_once_without_exposing_credentials(self):
        settings = SMSSettings.from_env(self.ENV)
        seen = []

        class Response:
            status = 201

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return b'{"sid":"SMabc123","status":"queued"}'

        def opener(req, timeout):
            seen.append((req, timeout))
            return Response()

        result = submit_sms(settings, "PDUFA scan test", opener=opener)
        self.assertEqual(result["status"], "submitted_not_delivered")
        self.assertEqual(len(seen), 1)
        self.assertIn("/Accounts/AC", seen[0][0].full_url)
        params = parse_qs(seen[0][0].data.decode("ascii"))
        self.assertEqual(params["Body"], ["PDUFA scan test"])
        self.assertEqual(params["To"], [self.ENV["PDUFA_SMS_TO_NUMBER"]])
        self.assertEqual(params["From"], [self.ENV["TWILIO_FROM_NUMBER"]])
        self.assertNotIn(self.ENV["TWILIO_AUTH_TOKEN"], repr(result))
        def ambiguous(*_, **__):
            raise TimeoutError("Unknown provider result")
        with self.assertRaises(SMSSendError):
            submit_sms(settings, "PDUFA scan test", opener=ambiguous)

    def test_full_success_sends_two_messages_and_saves_audit(self):
        settings = SMSSettings.from_env(self.ENV)
        texts = []
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            status_path = root / "status.json"
            audit_dir = root / "audit"

            def sender(_settings, text):
                texts.append(text)
                return {"status": "submitted_not_delivered",
                        "provider_message_id": "SMtest123"}

            def executor(command, cwd, check):
                self.assertEqual(command, ["mock", "--scan-all"])
                self.assertFalse(check)
                status_path.write_text(json.dumps({
                    "status": "COMPLETE",
                    "companies_checked": 717,
                    "companies_due": 717,
                    "new_records": 3,
                    "changed_trials_this_execution": 8,
                    "companies_with_warnings": 0,
                }))
                return SimpleNamespace(returncode=0)

            rc, audit = run_scan(
                scan="2", mode="BASELINE",
                command=["mock", "--scan-all"],
                status_file=status_path, audit_dir=audit_dir,
                settings=settings, sender=sender, executor=executor)
            self.assertEqual(rc, 0)
            self.assertEqual(len(texts), 2)
            self.assertIn("START", texts[0])
            self.assertIn("END: COMPLETE", texts[1])
            self.assertIn("companies 717/717", texts[1])
            self.assertIn("new 3", texts[1])
            self.assertIn("changed 8", texts[1])
            self.assertEqual(audit["coverage_status"], "COMPLETE")
            saved = json.loads((audit_dir / (audit["run_id"] + ".json")).read_text())
            self.assertEqual(saved["start_sms"], "submitted_not_delivered")
            self.assertEqual(saved["end_sms"], "submitted_not_delivered")
            self.assertNotIn(self.ENV["TWILIO_AUTH_TOKEN"], json.dumps(saved))

    def test_nonzero_scan_exit_sends_end_summary(self):
        settings = SMSSettings.from_env(self.ENV)
        texts = []
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            status_path = root / "status.json"

            def executor(*_, **__):
                status_path.write_text(json.dumps({
                    "status": "PARTIAL",
                    "tracked_trials_checked": 208,
                    "tracked_trials_total": 3105,
                    "tracked_trials_with_warnings": 18,
                }))
                return SimpleNamespace(returncode=1)
            rc, audit = run_scan(
                scan="3", mode="DELTA", command=["mock"],
                status_file=status_path, audit_dir=root / "audit",
                settings=settings,
                sender=lambda _, text: (texts.append(text) or {
                    "status": "submitted_not_delivered"}),
                executor=executor)
            self.assertEqual(rc, 1)
            self.assertEqual(len(texts), 2)
            self.assertIn("END: PARTIAL", texts[1])
            self.assertIn("trials 208/3105", texts[1])
            self.assertEqual(audit["coverage_status"], "PARTIAL")

    def test_stale_prior_report_cannot_claim_fresh_completion(self):
        settings = SMSSettings.from_env(self.ENV)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            status = root / "status.json"
            status.write_text(json.dumps({
                "status": "COMPLETE", "companies_checked": 717,
                "companies_due": 717,
            }))
            texts = []
            rc, audit = run_scan(
                scan="4", mode="DELTA", command=["mock"],
                status_file=status, audit_dir=root / "audit",
                settings=settings,
                sender=lambda _, message: (texts.append(message) or {
                    "status": "submitted_not_delivered"}),
                executor=lambda *_, **__: SimpleNamespace(returncode=0))
            self.assertEqual(rc, 3)
            self.assertFalse(audit["fresh_status_report"])
            self.assertEqual(len(texts), 2)
            self.assertIn("END: UNVERIFIED", texts[1])

    def test_start_text_failure_stops_scan(self):
        settings = SMSSettings.from_env(self.ENV)
        with tempfile.TemporaryDirectory() as folder:
            scan = Mock()
            attempts = []
            def sender(*_):
                attempts.append(1)
                raise SMSSendError("not accepted")
            rc, audit = run_scan(
                scan="2", mode="BASELINE", command=["mock"],
                status_file=Path(folder) / "status.json",
                audit_dir=Path(folder) / "audit",
                settings=settings, sender=sender, executor=scan)
            self.assertEqual(rc, 4)
            scan.assert_not_called()
            self.assertEqual(len(attempts), 1)
            self.assertFalse(audit["scan_executed"])
            self.assertEqual(audit["end_sms"], "NOT_SENT_SCAN_NOT_STARTED")

    def test_finish_text_failure_is_recorded_not_retried(self):
        settings = SMSSettings.from_env(self.ENV)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            status = root / "status.json"
            messages = []
            def sender(_, message):
                messages.append(message)
                if len(messages) == 2:
                    raise SMSSendError("unknown delivery status")
                return {"status": "submitted_not_delivered"}
            def executor(*_, **__):
                status.write_text('{"status":"COMPLETE"}')
                return SimpleNamespace(returncode=0)
            rc, audit = run_scan(
                scan="2", mode="DELTA", command=["mock"],
                status_file=status, audit_dir=root / "audit",
                settings=settings, sender=sender, executor=executor)
            self.assertEqual(rc, 4)
            self.assertEqual(len(messages), 2)
            self.assertEqual(audit["end_sms"], "FAILED_OR_UNKNOWN")

    def test_unexpected_scanner_exception_sends_final_text(self):
        settings = SMSSettings.from_env(self.ENV)
        with tempfile.TemporaryDirectory() as folder:
            msgs = []
            def raising(*_, **__):
                raise OSError("source offline")
            rc, audit = run_scan(
                scan="FDA", mode="DEEP", command=["mock"],
                status_file=Path(folder) / "status.json",
                audit_dir=Path(folder) / "audit",
                settings=settings, executor=raising,
                sender=lambda _, message: (msgs.append(message) or {
                    "status": "submitted_not_delivered"}))
            self.assertEqual(rc, 1)
            self.assertEqual(len(msgs), 2)
            self.assertIn("END: FAILED", msgs[1])
            self.assertEqual(audit["coverage_status"], "FAILED")

    def test_timeout_reports_failure_and_sends_finish_text(self):
        settings = SMSSettings.from_env(self.ENV)
        with tempfile.TemporaryDirectory() as folder:
            messages = []
            def timeout_executor(*_, **kwargs):
                self.assertEqual(kwargs["timeout"], 5)
                raise subprocess.TimeoutExpired(cmd=["mock"], timeout=5)
            rc, audit = run_scan(
                scan="4", mode="BASELINE", command=["mock"],
                status_file=Path(folder) / "status.json",
                audit_dir=Path(folder) / "audit", timeout_seconds=5,
                settings=settings, executor=timeout_executor,
                sender=lambda _, message: (messages.append(message) or {
                    "status": "submitted_not_delivered"}))
            self.assertEqual(rc, 1)
            self.assertEqual(len(messages), 2)
            self.assertIn("END: FAILED", messages[1])
            self.assertIn("TimeoutExpired", audit["summary"])

    def test_summary_fail_closed_for_missing_or_incomplete_counts(self):
        state, detail = summarize_report(
            {"status": "COMPLETE", "companies_checked": 4,
             "companies_due": 5, "errors": ["source unavailable"]}, 1, True)
        self.assertEqual(state, "FAILED")
        self.assertIn("companies 4/5", detail)
        self.assertIn("errors 1", detail)
        self.assertEqual(summarize_report({"status": "COMPLETE"}, 0, False)[0],
                         "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
