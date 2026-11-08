import os
import io
import json
import unittest
import urllib.error
from contextlib import redirect_stdout
from unittest.mock import patch
from scripts.telegram_scan_alert import main, message


class TelegramScanAlertTests(unittest.TestCase):
    def test_pipeline_failure_does_not_claim_completion(self):
        text = message("pipeline-end", "failure", "Archive failed")
        self.assertIn("FAILED / INCOMPLETE", text)
        self.assertNotIn("COMPLETED", text)

    def test_retired_analysis_events_cannot_send_notifications(self):
        for event in ("raas-start", "raas-end", "raas-evidence-change"):
            with self.assertRaises(ValueError):
                message(event, "success", "Historical run")
        self.assertNotIn("RAAS", message("scan-end", "success"))
        self.assertNotIn("RAAS", message("prediction-change", "success"))

    def test_untrusted_links_not_included(self):
        self.assertNotIn("evil.example", message("test", url="https://evil.example/secret"))
        self.assertIn("github.com/pdufa", message("test", url="https://github.com/pdufa/pdufa-command-center/actions/runs/1"))

    def test_unconfigured_manual_test_fails(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            self.assertEqual(main(["--event", "test"]), 1)
            self.assertEqual(main(["--event", "pipeline-start"]), 0)

    def test_diagnostic_reveals_chat_not_found_but_not_token(self):
        token = "12345:super-secret-should-never-print"
        response_body = io.BytesIO(json.dumps({"description": "Bad Request: chat not found"}).encode())
        error = urllib.error.HTTPError(
            url="https://api.telegram.org/bot" + token + "/sendMessage",
            code=400, msg="Bad Request", hdrs={}, fp=response_body)
        output = io.StringIO()
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": token, "TELEGRAM_CHAT_ID": "12345"}):
            with patch("urllib.request.urlopen", side_effect=error):
                with redirect_stdout(output):
                    result = main(["--event", "test"])
        self.assertEqual(result, 1)
        self.assertIn("Chat not found", output.getvalue())
        self.assertNotIn(token, output.getvalue())


if __name__ == "__main__":
    unittest.main()
