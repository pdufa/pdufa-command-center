"""Operational read-only SCANS view must not present an old report as today's scan."""
import unittest
from datetime import datetime, timezone

from overnight_status_ui import (
    pacific_schedule_for, run_delay_minutes, source_matches_run,
    choose_run, stage_rows,
)

TITLE = "ALL + GEM — PDUFA overnight"
PATH = ".github/workflows/pdufa-overnight-sequential.yml"


class OvernightStatusTests(unittest.TestCase):
    def test_pacific_clock_and_late_dispatch(self):
        run = {"created_at": "2026-10-17T09:09:49Z"}
        expected = pacific_schedule_for(run["created_at"])
        self.assertEqual(expected.isoformat(), "2026-10-16T22:00:00-07:00")
        self.assertEqual(run_delay_minutes(run), 250)
        winter = pacific_schedule_for("2026-12-17T07:15:00Z")
        self.assertEqual(winter.isoformat(), "2026-12-16T22:00:00-08:00")
        self.assertEqual(run_delay_minutes({"created_at": "2026-12-17T06:00:00Z"}), 0)
        self.assertIsNone(pacific_schedule_for("2026-10-17T18:00:00Z"))

    def test_only_exact_latest_github_chain_wins(self):
        a = dict(id=11, path=PATH, display_title=TITLE,
                 event="workflow_dispatch", created_at="2026-10-17T09:09:49Z")
        b = dict(id=12, path=PATH, display_title=TITLE,
                 event="workflow_dispatch", created_at="2026-10-18T05:02:00Z")
        spam = dict(id=90, path="other.yml", display_title=TITLE,
                    event="push", created_at="2026-10-19T05:02:00Z")
        result = choose_run([a, b, spam], {"latest_run_id": 11}, {"latest_run_id": 11})
        self.assertEqual(result["id"], 12)
        self.assertFalse(source_matches_run(result, {"latest_run_id": 11, "schema_version": 2}))
        self.assertTrue(source_matches_run(result, {"latest_run_id": 12, "schema_version": 2}))
        self.assertFalse(source_matches_run(result, {"latest_run_id": 12, "schema_version": 1}))

    def test_published_fallback_does_not_invent_actual_times(self):
        choice = choose_run([], {"latest_run_id": 99,
                                 "latest_run_url": "https://github.com/pdufa/pdufa-command-center/actions/runs/99"},
                            {"latest_run_id": 99, "schema_version": 2})
        self.assertEqual(choice["id"], 99)
        self.assertTrue(choice["data_only"])
        self.assertIsNone(run_delay_minutes(choice))
        self.assertTrue(source_matches_run(choice, {"latest_run_id": 99, "schema_version": 2}))

    def test_every_job_preserves_its_own_stage_state(self):
        jobs = [
            {"name": "clinical / PIPELINE", "status": "completed",
             "conclusion": "success",
             "started_at": "2026-10-17T09:10:00Z",
             "completed_at": "2026-10-17T09:12:00Z"},
            {"name": "sources / SEC", "status": "completed",
             "conclusion": "failure"},
        ]
        rows = stage_rows(jobs)
        self.assertEqual(rows[0]["Stage"], "Clinical")
        self.assertEqual(rows[0]["GitHub execution"], "SUCCESS")
        self.assertEqual(rows[0]["Duration"], "2 min")
        self.assertEqual(rows[1]["GitHub execution"], "FAILURE")
        self.assertEqual(rows[1]["Duration"], "—")


if __name__ == "__main__":
    unittest.main()
