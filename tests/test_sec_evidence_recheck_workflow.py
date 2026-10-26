"""Static safeguards for independent, research-only SEC evidence rechecks."""
from pathlib import Path
import re
import unittest

WORKFLOW = (Path(__file__).resolve().parents[1]
            / ".github/workflows/pdufa-sec-financing-evidence-recheck.yml")


def job_section(source: str, name: str) -> str:
    match = re.search(r"(?m)^  " + re.escape(name) + r":\\s*$", source)
    if match is None:
        raise AssertionError("Missing workflow job: " + name)
    rest = source[match.end():]
    next_job = re.search(r"(?m)^  [a-z][a-z0-9-]*:\\s*$", rest)
    return source[match.start(): match.end() + next_job.start() if next_job else len(source)]


class SecRecheckWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_independent_live_research_failure_does_not_skip_required_claim_comparison(self):
        lead = job_section(self.workflow, "live-recheck")
        claim = job_section(self.workflow, "unresolved-claim-recheck")
        self.assertIn("needs: offline-tests", lead)
        self.assertIn("needs: [offline-tests, live-recheck]", claim)
        self.assertIn("always() && github.event_name != 'pull_request'", claim)
        self.assertIn("needs['offline-tests'].result == 'success'", claim)
        self.assertNotIn("needs['live-recheck'].result == 'success'", claim)
        self.assertIn("scripts.targeted_verification_repair", claim)
        self.assertIn("Source run:", claim)
        self.assertIn("Still unresolved:", claim)
        self.assertNotIn("all 36 unresolved", claim)

    def test_offline_claim_guards_run_before_live_source_access(self):
        offline = job_section(self.workflow, "offline-tests")
        self.assertIn("test_provisional_financing_sec_recheck.py", offline)
        self.assertIn("test_targeted_verification_repair.py", offline)
        self.assertIn("test_sec_evidence_recheck_workflow.py", offline)
        self.assertIn("test_sec_search_discovery.py", offline)
        self.assertIn("Check SEC researcher identity", self.workflow)
        self.assertIn("SEC_USER_AGENT must include a real contact email", self.workflow)

    def test_rechecks_are_research_only_without_publish_scan_or_trade_changes(self):
        self.assertIn("contents: read", self.workflow)
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("git push ", self.workflow)
        self.assertNotIn("/dispatches", self.workflow)
        self.assertNotIn("source_claim_verified = 'YES'", self.workflow)
        self.assertIn("No original ledger, model or trade gate was changed.", self.workflow)
        # This rechecks only saved canonical findings using a source-run ID.
        self.assertIn("--source-run-id", self.workflow)
        self.assertIn("data/pdufa_source_report.json", self.workflow)


if __name__ == "__main__":
    unittest.main()
