"""Offline guardrails for the top-level SCANS monitor."""
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import scan_activity_dashboard as viewer

ROOT = Path(__file__).resolve().parents[1]


class ScanActivityDashboardTests(unittest.TestCase):
    def test_scans_navigation_is_top_level_without_removing_pdufa_subtab(self):
        src = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('nav_options = ["PDUFA", "SCANS", "2. PDUFA CALENDAR"]', src)
        self.assertIn('elif page == "SCANS":\n    # Separate top navigation', src)
        self.assertIn('    render_scans_activity()\n\nelif page == "2. PDUFA CALENDAR":', src)
        self.assertIn('["GEM", "PIPELINE", "PRE PHASE 3", "POST PHASE 3", "SCANS", "WT"]', src)
        self.assertIn("render_nightly_scan_report()", src)

    def test_both_gems_workflow_logs_are_pinned_in_both_scans_pages(self):
        activity = (ROOT / "scan_activity_dashboard.py").read_text(encoding="utf-8")
        nested = (ROOT / "nightly_scan_dashboard.py").read_text(encoding="utf-8")
        for workflow in ("gem-research-quality.yml", "gem-financing-full-coverage.yml"):
            self.assertIn('"/workflows/' + workflow + '"', activity)
            self.assertIn('"/actions/workflows/' + workflow + '"', nested)
        self.assertIn("GEMS SCANS — DIRECT LOG LINKS", activity)
        self.assertIn("GEMS — GITHUB SCAN LOGS", nested)
        self.assertIn("They remain", activity)
        self.assertIn("GEMS PHASE 3 / RESEARCH SCAN", nested)
        self.assertIn("GEMS FINANCING AUDIT SCAN", nested)

    def test_live_and_finished_statuses_are_not_trade_certifications(self):
        for status, conclusion, expected in (
            ("in_progress", None, "Running"),
            ("queued", None, "Queued"),
            ("pending", None, "Queued"),
            ("completed", "success", "Completed"),
            ("completed", "failure", "Failed"),
            ("completed", "cancelled", "Cancelled"),
            ("completed", "skipped", "Skipped"),
        ):
            with self.subTest(status=status, conclusion=conclusion):
                self.assertEqual(viewer._state(
                    {"status": status, "conclusion": conclusion}), expected)

    def test_run_history_uses_pacific_dates_24h_and_deduplicates(self):
        now = datetime(2026, 10, 14, 19, 0, tzinfo=timezone.utc)
        def item(id_, created_at, status="completed", name="GEMS"):
            return {"id": id_, "created_at": created_at, "status": status,
                    "conclusion": "success" if status == "completed" else None,
                    "_label": name}
        runs = [
            item(111, "2026-10-14T18:30:00Z"),
            item(112, "2026-10-13T18:30:00Z"),  # more than 24h old
            item(111, "2026-10-14T18:30:00Z"),  # duplicate across workflows
            item(113, "2026-10-14T17:30:00Z", "in_progress", "SEC sources"),
            item(None, "2026-10-14T17:00:00Z"),
        ]
        rows = viewer._rows_for_window(runs, now, 24)
        self.assertEqual([r["id"] for r in rows], [111, 113])
        self.assertIn("PDT", rows[0]["started"])
        self.assertEqual(rows[1]["status"], "Running")
        self.assertTrue(rows[0]["url"].startswith("https://github.com/pdufa/"))

    def test_no_arbitrary_or_invalid_github_job_links(self):
        self.assertEqual(viewer._run_url("12345"), "")
        self.assertEqual(viewer._run_url(-1), "")
        self.assertEqual(viewer._job_url(111, "2"), "")
        self.assertEqual(viewer._job_url(111, 123),
                         "https://github.com/pdufa/pdufa-command-center/actions/runs/111/job/123")

    def test_public_dashboard_cannot_start_scan_or_execute_trades(self):
        src = (ROOT / "scan_activity_dashboard.py").read_text(encoding="utf-8")
        for forbidden in ("Request(url, data=", "method=\"POST\"", "subprocess.run(",
                          "GenUI", "place_order(", "requests.post(", "dispatches"):
            self.assertNotIn(forbidden, src)
        self.assertIn("read-only", src.lower())
        self.assertIn("NOT certify", src)


if __name__ == "__main__":
    unittest.main()
