"""Unit tests: provider is NEVER contacted in these tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.focus_telnyx_sms import (
    Settings, TelnyxSetupError, TelnyxSubmissionError,
    alert_text, ascii_message, focus_tickers, main, submit_once,
    MAX_SMS_LENGTH,
)


class TelnyxFocusSmsTests(unittest.TestCase):
    GOOD = {
        "TELNYX_API_KEY": "test_placeholder_not_a_credential",
        "TELNYX_FROM_NUMBER": "+15035550100",
        "PDUFA_SMS_TO_NUMBER": "+15035550199",
    }

    def test_setup_is_fail_closed(self):
        with self.assertRaises(TelnyxSetupError):
            Settings.from_env({})
        with self.assertRaises(TelnyxSetupError):
            Settings.from_env({**self.GOOD, "PDUFA_SMS_TO_NUMBER": "5035550199"})
        with self.assertRaises(TelnyxSetupError):
            Settings.from_env({**self.GOOD, "PDUFA_SMS_TO_NUMBER": "+15035550100"})

    def test_canonical_roster_is_required(self):
        actual = focus_tickers()
        self.assertEqual(len(actual), 20)
        self.assertIn("CYTK", actual)
        with tempfile.TemporaryDirectory() as folder:
            other = Path(folder) / "roster.json"
            other.write_text('{"records":[{"ticker":"CYTK"},{"ticker":"CAPR"}]}')
            self.assertEqual(focus_tickers(other), {"CYTK", "CAPR"})
            other.write_text('{"records":[]}')
            with self.assertRaises(TelnyxSetupError):
                focus_tickers(other)

    def test_exact_one_segment_and_required_priority(self):
        m = alert_text("cytk", "high", "New FDA filing " + ("a" * 300))
        self.assertTrue(m.isascii())
        self.assertLessEqual(len(m), MAX_SMS_LENGTH)
        self.assertIn("CYTK", m)
        with self.assertRaises(ValueError):
            alert_text("CYTK", "LOW", "Routine")
        self.assertLessEqual(len(ascii_message("X" * 500)), MAX_SMS_LENGTH)

    def test_one_provider_submission_no_secrets_in_result(self):
        seen = []

        class Response:
            status = 202
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self):
                return b'{"data":{"id":"test-message-id","status":"queued"}}'

        def opener(req, timeout):
            seen.append((req, timeout))
            return Response()

        settings = Settings.from_env(self.GOOD)
        result = submit_once(settings, "FOCUS TEST", opener=opener)
        self.assertEqual(result["status"], "submitted_not_delivered")
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][1], 20)
        req = seen[0][0]
        self.assertEqual(req.full_url, "https://api.telnyx.com/v2/messages")
        self.assertEqual(json.loads(req.data)["to"], self.GOOD["PDUFA_SMS_TO_NUMBER"])
        self.assertEqual(req.get_header("Authorization"), "Bearer " + self.GOOD["TELNYX_API_KEY"])
        self.assertNotIn(self.GOOD["TELNYX_API_KEY"], str(result))
        self.assertNotIn(self.GOOD["PDUFA_SMS_TO_NUMBER"], str(result))

    def test_unknown_result_never_retries(self):
        calls = []
        def timeout(*_args, **_kw):
            calls.append(1)
            raise TimeoutError("ambiguous")
        with self.assertRaises(TelnyxSubmissionError):
            submit_once(Settings.from_env(self.GOOD), "FOCUS TEST", opener=timeout)
        self.assertEqual(len(calls), 1)

    def test_alert_refuses_before_verified_and_non_focus(self):
        with patch.dict("os.environ", self.GOOD, clear=True):
            with patch("scripts.focus_telnyx_sms.submit_once") as submit:
                self.assertEqual(main(["--alert", "--ticker", "CYTK",
                                       "--priority", "HIGH", "--headline", "Test"]), 1)
                submit.assert_not_called()
        with patch.dict("os.environ", {**self.GOOD, "PDUFA_TELNYX_SMS_VERIFIED": "true"}, clear=True):
            with patch("scripts.focus_telnyx_sms.submit_once") as submit:
                self.assertEqual(main(["--alert", "--ticker", "NOTONFOCUS",
                                       "--priority", "HIGH", "--headline", "Test"]), 1)
                submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
