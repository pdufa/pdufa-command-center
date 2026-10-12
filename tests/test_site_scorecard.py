"""Fail-closed checks for the operational site scorecard."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from site_scorecard import _status_workflow, build_checks, summarize


class SiteScorecardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "app.py").write_text("pass\n", encoding="utf-8")
        (self.root / "smoke_test.py").write_text("pass\n", encoding="utf-8")
        (self.root / "data").mkdir()
        self.now = datetime(2026, 10, 12, 18, 0, tzinfo=timezone.utc)

    def _save(self, filename, data):
        (self.root / "data" / filename).write_text(json.dumps(data), encoding="utf-8")

    def test_missing_checks_remain_unknown_without_invented_success(self):
        checks, report, status = build_checks(root=self.root, now=self.now, workflows={})
        totals = summarize(checks)
        self.assertEqual(totals["maximum"], 100)
        self.assertEqual(totals["earned"], 10)
        self.assertGreater(totals["unknown"], 0)

    def test_partial_scan_success_never_awards_full_source_coverage(self):
        report = {
            "updated_at_utc": "2026-10-12T17:00:00Z",
            "status": "PARTIAL",
            "verification": {"artifact_integrity": "PASS", "all_source_coverage": "NOT_VERIFIED"},
            "missing_required_source_families": ["SEC financing and dilution verification"],
            "scans": [{"scan": str(n), "artifact_integrity": "PASS", "errors_count": 0}
                      for n in (2, 3, 4)],
        }
        self._save("nightly_scan_report.json", report)
        self._save("step7_live_status.json", {"generated_at_utc": "2026-10-12T17:00:00Z"})
        checks, _, _ = build_checks(root=self.root, now=self.now, workflows={})
        coverage = next(c for c in checks if c["Category"] == "Source coverage")
        self.assertEqual((coverage["Status"], coverage["Earned"]), ("FAIL", 0))
        self.assertEqual(summarize(checks)["earned"], 35)

    def test_manual_push_run_does_not_prove_ad_hoc_email_audit(self):
        recent = {
            "status": "completed", "conclusion": "success", "head_branch": "main",
            "event": "push", "created_at": "2026-10-12T17:30:00Z",
            "updated_at": "2026-10-12T17:35:00Z",
        }
        state, _, _ = _status_workflow(
            {"pdufa-adhoc-error-check.yml": {"runs": [recent], "error": ""}},
            "pdufa-adhoc-error-check.yml", self.now, event="workflow_dispatch")
        self.assertEqual(state, "UNKNOWN")

    def test_latest_failed_ci_does_not_reuse_older_green(self):
        good = {"status": "completed", "conclusion": "success", "head_branch": "main",
                "created_at": "2026-10-12T16:00:00Z", "updated_at": "2026-10-12T16:05:00Z"}
        bad = {"status": "completed", "conclusion": "failure", "head_branch": "main",
               "created_at": "2026-10-12T17:00:00Z", "updated_at": "2026-10-12T17:05:00Z"}
        state, _, _ = _status_workflow(
            {"ci.yml": {"runs": [good, bad], "error": ""}}, "ci.yml", self.now)
        self.assertEqual(state, "FAIL")

    def test_stale_success_is_not_pass(self):
        stale = {"status": "completed", "conclusion": "success", "head_branch": "main",
                 "created_at": "2026-09-01T17:00:00Z", "updated_at": "2026-09-01T17:10:00Z"}
        state, _, _ = _status_workflow(
            {"ci.yml": {"runs": [stale], "error": ""}}, "ci.yml", self.now)
        self.assertEqual(state, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
