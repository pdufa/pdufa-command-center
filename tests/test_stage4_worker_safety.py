"""Regression tests for the Stage 4 development worker's safety boundary."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Stage4WorkerSafetyTests(unittest.TestCase):
    def test_queue_workflow_does_not_have_write_permissions(self):
        workflow = (ROOT / ".github/workflows/stage4-budget-gated-agent.yml").read_text()
        self.assertIn("contents: read", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("pull-requests: write", workflow)

    def test_queue_workflow_has_no_ai_credentials(self):
        workflow = (ROOT / ".github/workflows/stage4-budget-gated-agent.yml").read_text()
        for secret in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN:"):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, workflow)

    def test_queue_worker_never_claims_spending_authority(self):
        worker = (ROOT / "scripts/stage4_budget_gate.py").read_text()
        self.assertIn('"ai_calls": 0', worker)
        self.assertIn("awaiting_executor_and_billing_guard", worker)


if __name__ == "__main__":
    unittest.main()
