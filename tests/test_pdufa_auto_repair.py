"""Bounded automatic repair must never turn data or code failures into passes."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from pdufa_auto_repair import decide

NOW = datetime(2026, 10, 12, 20, tzinfo=timezone.utc)
SHA = "f" * 40
RUN = {"name": "PDUFA Command Center CI", "event": "push",
       "head_branch": "main", "head_sha": SHA, "run_attempt": 1,
       "conclusion": "failure", "status": "completed", "id": 123}
FAILED = [{"name": "validate", "conclusion": "failure"}]

class AutoRepairTests(unittest.TestCase):
    def check(self, logs="ConnectionResetError: connection reset by peer",
              run=None, jobs=None, manifest=None):
        return decide(RUN if run is None else run,
                      FAILED if jobs is None else jobs,
                      logs, SHA, manifest, NOW)[0]

    def test_one_retry_for_verified_transient_error(self):
        self.assertEqual(self.check(), "rerun")
        self.assertEqual(self.check(run={**RUN, "run_attempt": 2}), "skip")

    def test_never_rerun_scans_or_notification_workflows(self):
        for name in ("PDUFA Nightly Clinical Scans",
                     "PDUFA Nightly FDA SEC Financial Market Issuer Sources",
                     "PDUFA Clinical Scan Completion Email"):
            with self.subTest(name=name):
                self.assertEqual(self.check(run={**RUN, "name": name}), "skip")

    def test_only_current_main_failed_jobs(self):
        for diff in ({"head_sha": "a" * 40}, {"head_branch": "feature"},
                     {"event": "pull_request"}, {"status": "in_progress"},
                     {"conclusion": "success"}, {"run_attempt": 3}):
            self.assertEqual(self.check(run={**RUN, **diff}), "skip")
        self.assertEqual(self.check(jobs=[]), "skip")

    def test_deterministic_errors_fail_closed(self):
        for log in ("AssertionError: expected true", "ModuleNotFoundError: x",
                    "HTTP 403 Forbidden", "Resource not accessible by integration",
                    "FAILED (failures=7)", "Unknown exception", ""):
            with self.subTest(log=log):
                self.assertEqual(self.check(logs=log), "skip")
        self.assertEqual(self.check(logs="AssertionError and ConnectionResetError"), "skip")

    def test_retired_browser_workflows_cannot_trigger_cache_refresh(self):
        p3 = {**RUN, "name": "PRE PHASE 3 Live Acceptance"}
        error = "Source integration failed. Error type: ValueError"
        old = {"generated_at_utc": "2026-10-11T16:00:00+00:00"}
        fresh = {"generated_at_utc": "2026-10-12T16:00:00+00:00"}
        self.assertEqual(self.check(error, p3, manifest=old), "skip")
        self.assertEqual(self.check(error, p3, manifest=fresh), "skip")
        self.assertEqual(self.check(error, manifest=old), "skip")

if __name__ == "__main__":
    unittest.main()
