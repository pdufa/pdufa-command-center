import os
import unittest
from unittest.mock import patch
from scripts.telegram_scan_alert import main, message


class TelegramScanAlertTests(unittest.TestCase):
    def test_pipeline_failure_does_not_claim_completion(self):
        text = message("pipeline-end", "failure", "Archive failed")
        self.assertIn("FAILED / INCOMPLETE", text)
        self.assertNotIn("COMPLETED", text)

    def test_raas_success_is_workflow_success_only(self):
        text = message("raas-end", "success", "Review source artifacts")
        self.assertIn("RAAS ACCURACY", text)
        self.assertIn("Workflow status: success", text)

    def test_untrusted_links_not_included(self):
        self.assertNotIn("evil.example", message("test", url="https://evil.example/secret"))
        self.assertIn("github.com/pdufa", message("test", url="https://github.com/pdufa/pdufa-command-center/actions/runs/1"))

    def test_unconfigured_manual_test_fails(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            self.assertEqual(main(["--event", "test"]), 1)
            self.assertEqual(main(["--event", "pipeline-start"]), 0)

if __name__ == "__main__":
    unittest.main()
