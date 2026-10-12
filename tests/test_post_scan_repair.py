"""The nightly error repair stage must never modify source data or race scoring."""
import json
from pathlib import Path
from unittest.mock import patch
import unittest

from scripts.post_scan_repair import candidates, repair_current_failures

REPO = "pdufa/pdufa-command-center"
SHA = "a" * 40
RUN = {"name": "PDUFA Command Center CI", "head_branch": "main",
       "head_sha": SHA, "status": "completed", "conclusion": "failure",
       "event": "push", "run_attempt": 1, "id": 123}
JOBS = {"jobs": [{"name": "smoke", "conclusion": "failure"}]}


class PostScanRepairTests(unittest.TestCase):
    def test_only_current_verified_alert_ids_are_candidates(self):
        self.assertEqual(candidates({"github": {"status": "UNAVAILABLE",
                                               "current_failures": [{"id": 1, "workflow": "ci.yml"}]}}), [])
        self.assertEqual(candidates({"github": {"status": "ISSUES_FOUND",
                                               "current_failures": [
                                                   {"id": 123, "workflow": "ci.yml"},
                                                   {"id": 123, "workflow": "ci.yml"},
                                                   {"id": "oops", "workflow": "ci.yml"},
                                                   {"id": 44, "workflow": "not-a-workflow"}]}}), [123])

    def test_transient_fault_can_request_single_failed_job_retry(self):
        alerts = {"github": {"status": "ISSUES_FOUND",
                             "current_failures": [{"id": 123, "workflow": "ci.yml"}]}}
        called = []
        def fake_gh(*args):
            called.append(args)
            if args[0] == "api" and "/jobs?" in args[1]:
                return json.dumps(JOBS)
            if args[0] == "api":
                return json.dumps(RUN)
            if args[:2] == ("run", "view"):
                return "ConnectionResetError: connection reset by peer"
            if args[:2] == ("run", "rerun"):
                return "requested"
            raise AssertionError(args)
        with patch("scripts.post_scan_repair.gh", side_effect=fake_gh):
            result = repair_current_failures(alerts, repo=REPO, current_sha=SHA)
        self.assertEqual(result["rerun_requests"], 1)
        self.assertEqual(result["decisions"][0]["action"], "rerun_requested")
        self.assertEqual(sum(1 for c in called if c[:2] == ("run", "rerun")), 1)

    def test_never_retry_scans_or_deterministic_errors(self):
        alerts = {"github": {"status": "ISSUES_FOUND",
                             "current_failures": [{"id": 123, "workflow": "ci.yml"}]}}
        with patch("scripts.post_scan_repair.gh",
                   side_effect=lambda *args: json.dumps(
                       {**RUN, "name": "PDUFA Nightly Clinical Scans"})) as call:
            result = repair_current_failures(alerts, repo=REPO, current_sha=SHA)
        self.assertEqual(result["rerun_requests"], 0)
        self.assertTrue(all(x.args[0] != "run" for x in call.call_args_list))
        def permanent(*args):
            if args[0] == "api" and "/jobs?" in args[1]:
                return json.dumps(JOBS)
            if args[0] == "api":
                return json.dumps(RUN)
            if args[:2] == ("run", "view"):
                return "AssertionError: expected 7 tabs"
            raise AssertionError("Repair should never be invoked")
        with patch("scripts.post_scan_repair.gh", side_effect=permanent):
            result = repair_current_failures(alerts, repo=REPO, current_sha=SHA)
        self.assertEqual(result["decisions"][0]["action"], "skip")

    def test_workflow_order_and_old_trigger_removal(self):
        root = Path(__file__).resolve().parents[1] / ".github" / "workflows"
        orchestrator = (root / "pdufa-nightly-scoring-then-repair.yml").read_text(encoding="utf-8")
        for name in ("PDUFA Nightly Scan Report Publisher",
                     "PDUFA Nightly FDA SEC Financial Market Issuer Sources"):
            self.assertIn(name, orchestrator)
        self.assertIn("needs: scoring", orchestrator)
        self.assertIn("needs: [scoring, error-check]", orchestrator)
        self.assertLess(orchestrator.index("\n  scoring:"), orchestrator.index("\n  error-check:"))
        self.assertLess(orchestrator.index("\n  error-check:"), orchestrator.index("\n  safe-repair:"))
        old_checker = (root / "pdufa-adhoc-error-check.yml").read_text(encoding="utf-8")
        self.assertNotIn("\n  workflow_run:", old_checker)
        self.assertIn("\n  workflow_dispatch:", old_checker)
        auto = (root / "pdufa-safe-auto-repair.yml").read_text(encoding="utf-8")
        for name in ("'PDUFA Nightly Scan Report Publisher'",
                     "'PDUFA Nightly Clinical Scans'",
                     "'PDUFA Nightly FDA SEC Financial Market Issuer Sources'"):
            self.assertNotIn(name, auto)


if __name__ == "__main__":
    unittest.main()
