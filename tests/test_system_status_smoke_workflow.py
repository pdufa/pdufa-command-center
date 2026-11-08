"""The PR gate checks the code under review, not an old production alias."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]

class SystemStatusSmokeWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = (ROOT / '.github/workflows/system-status-production-smoke.yml').read_text()

    def test_required_check_identity_and_full_validator_are_preserved(self):
        self.assertIn('name: Production page, 15 sections, science/outcome privacy guards', self.workflow)
        self.assertIn("python3 -m unittest discover -s tests -p 'test_*production_smoke.py' -v", self.workflow)
        self.assertIn('python3 ../../scripts/check_system_status_production.py --base-url http://127.0.0.1:3012', self.workflow)
        self.assertNotIn('continue-on-error:', self.workflow)

    def test_pr_builds_real_server_without_secrets_and_always_cleans_it_up(self):
        self.assertIn("if: github.event_name == 'pull_request'", self.workflow)
        self.assertIn('npm ci --ignore-scripts --no-audit --no-fund', self.workflow)
        self.assertIn('npm run build', self.workflow)
        self.assertIn('next start --hostname 127.0.0.1 --port 3012', self.workflow)
        self.assertIn('trap cleanup EXIT', self.workflow)
        self.assertIn('kill "$server_pid"', self.workflow)
        self.assertIn('time.monotonic() + 60', self.workflow)
        self.assertNotIn('secrets.', self.workflow)

    def test_main_and_manual_runs_still_require_full_production_validation(self):
        self.assertIn("if: github.event_name != 'pull_request'", self.workflow)
        self.assertIn('for attempt in $(seq 1 8)', self.workflow)
        self.assertIn('if python3 scripts/check_system_status_production.py; then exit 0; fi', self.workflow)
        self.assertIn('if [ "$attempt" -eq 8 ]; then exit 1; fi', self.workflow)
        self.assertIn('sleep 20', self.workflow)
        self.assertNotIn('workflow_run:', self.workflow)

if __name__ == '__main__':
    unittest.main()
