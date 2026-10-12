"""Surveillance must never claim success when scheduled collectors were skipped."""
import unittest
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from scripts.surveillance_schedule import (
    SCHEDULES, REQUIRED_STEPS, mode_for_schedule, mode_for_trigger,
    verify_run_steps, make_run_record,
)


class SurveillanceScheduleTests(unittest.TestCase):
    def test_timezone_aware_schedule_keeps_pacific_wall_clock(self):
        local = ZoneInfo("America/Los_Angeles")
        self.assertEqual(
            datetime(2026, 7, 10, 5, 15, tzinfo=local).astimezone(timezone.utc).hour, 12
        )
        self.assertEqual(
            datetime(2026, 1, 10, 5, 15, tzinfo=local).astimezone(timezone.utc).hour, 13
        )

    def test_each_cron_selects_one_mode_regardless_of_queue_delay(self):
        self.assertEqual(SCHEDULES, {
            "15 5 * * *": "daily",
            "0 4 * * 0": "weekly",
            "30 4 1 * *": "monthly",
        })
        for expression, mode in SCHEDULES.items():
            self.assertEqual(mode_for_schedule(expression), mode)
            self.assertEqual(mode_for_trigger("schedule", expression), mode)

    def test_unknown_schedules_fail_instead_of_successfully_skipping_scans(self):
        for invalid in ("", "15 12 * * *", "15 13 * * *", "0 0 * * *"):
            with self.assertRaises(ValueError):
                mode_for_schedule(invalid)

    def test_manual_dispatch_modes_and_invalid_event(self):
        for mode in ("daily", "weekly", "monthly", "full"):
            self.assertEqual(mode_for_trigger("workflow_dispatch", manual_mode=mode), mode)
        for mode in ("", "skip", "bad"):
            with self.assertRaises(ValueError):
                mode_for_trigger("workflow_dispatch", manual_mode=mode)
        with self.assertRaises(ValueError):
            mode_for_trigger("push", "15 5 * * *")

    def test_fails_closed_when_any_required_scan_step_is_skipped(self):
        for mode, required in REQUIRED_STEPS.items():
            successful = {name: {"outcome": "success"} for name in required}
            self.assertEqual(verify_run_steps(mode, successful)["status"], "COMPLETE")
            for name in required:
                incomplete = dict(successful)
                incomplete[name] = {"outcome": "skipped"}
                with self.subTest(mode=mode, step=name):
                    with self.assertRaisesRegex(ValueError, name):
                        verify_run_steps(mode, incomplete)

    def test_audit_record_is_grounded_in_step_results(self):
        steps = {name: {"outcome": "success"} for name in REQUIRED_STEPS["daily"]}
        steps["recheck_weekly"] = {"outcome": "skipped"}
        record = make_run_record(
            "daily", steps, "schedule", "15 5 * * *", "123",
            finished_at="2026-10-10T15:00:00+00:00",
        )
        self.assertEqual(record["github_run_id"], "123")
        self.assertEqual(record["step_outcomes"]["recheck_weekly"], "skipped")
        self.assertEqual(record["required_steps"], list(REQUIRED_STEPS["daily"]))

    def test_legacy_surveillance_workflow_removed_until_verified_baseline(self):
        root = Path(__file__).resolve().parents[1]
        self.assertFalse((root / ".github/workflows/surveillance.yml").exists())
        # Keep the date resolver as historical source code, but no scheduled
        # scanner may restart while coverage and SMS transport are unverified.
        self.assertTrue((root / "scripts/surveillance_schedule.py").is_file())
        config = (root / "config/scan_234.json").read_text(encoding="utf-8")
        self.assertIn('"automation_enabled": false', config)
        self.assertIn('"notifications_active": false', config)


if __name__ == "__main__":
    unittest.main()
