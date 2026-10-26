"""Keep exactly one 8 PM Pacific research scan across PST/PDT changes."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase3_nightly_pacific_gate import (
    SUMMER_CRON, WINTER_CRON, decide, write_outcome,
)


def at(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class PacificNightlyGateTests(unittest.TestCase):
    def test_summer_three_am_utc_runs_eight_pm_pacific(self):
        actual = decide("schedule", SUMMER_CRON, at(2026, 7, 16, 3))
        self.assertTrue(actual["proceed"])
        self.assertEqual(actual["local_zone"], "PDT")
        self.assertEqual(actual["pacific_date"], "2026-07-15")

    def test_summer_four_am_utc_skips_dst_alternate(self):
        actual = decide("schedule", WINTER_CRON, at(2026, 7, 16, 4))
        self.assertFalse(actual["proceed"])
        self.assertEqual(actual["reason"], "OFF_SEASON_DST_ALTERNATE_SKIPPED")

    def test_winter_four_am_utc_runs_eight_pm_pacific(self):
        actual = decide("schedule", WINTER_CRON, at(2026, 1, 16, 4))
        self.assertTrue(actual["proceed"])
        self.assertEqual(actual["local_zone"], "PST")
        self.assertEqual(actual["pacific_date"], "2026-01-15")

    def test_winter_three_am_utc_skips_dst_alternate(self):
        actual = decide("schedule", SUMMER_CRON, at(2026, 1, 16, 3))
        self.assertFalse(actual["proceed"])

    def test_fall_transition_october_31_still_uses_summer(self):
        self.assertTrue(decide("schedule", SUMMER_CRON, at(2026, 11, 1, 3))["proceed"])

    def test_fall_transition_november_1_uses_winter(self):
        self.assertTrue(decide("schedule", WINTER_CRON, at(2026, 11, 2, 4))["proceed"])

    def test_spring_transition_march_7_still_uses_winter(self):
        self.assertTrue(decide("schedule", WINTER_CRON, at(2026, 3, 8, 4))["proceed"])

    def test_spring_transition_march_8_uses_summer(self):
        self.assertTrue(decide("schedule", SUMMER_CRON, at(2026, 3, 9, 3))["proceed"])

    def test_workflow_dispatch_runs_independently_of_cron(self):
        actual = decide("workflow_dispatch", "", at(2026, 10, 26, 19))
        self.assertTrue(actual["proceed"])
        self.assertEqual(actual["reason"], "AUTHORIZED_ON_DEMAND_OR_PR_SOURCE_CHECK")

    def test_pull_request_runs_without_scheduled_cron(self):
        self.assertTrue(decide("pull_request", "", at(2026, 10, 26, 19))["proceed"])

    def test_wrong_schedule_fails_closed(self):
        for value in ("", "0 2 * * *", "@daily", "*/5 * * * *"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                decide("schedule", value, at(2026, 10, 26, 19))

    def test_unknown_event_fails_closed(self):
        with self.assertRaises(ValueError):
            decide("push", "", at(2026, 10, 26, 19))

    def test_naive_clock_fails_closed(self):
        with self.assertRaises(ValueError):
            decide("schedule", SUMMER_CRON, datetime(2026, 7, 16, 3))

    def test_gate_writes_true_and_run_summary(self):
        result = decide("schedule", WINTER_CRON, at(2026, 1, 16, 4))
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "runner" / "github-output.txt"
            summary = Path(temp) / "runner" / "summary.md"
            write_outcome(result, output, summary)
            self.assertIn("proceed=true\n", output.read_text())
            self.assertIn("ENABLED", summary.read_text())
            self.assertIn("America/Los_Angeles", summary.read_text())

    def test_skipped_alternate_has_explicit_summary(self):
        result = decide("schedule", SUMMER_CRON, at(2026, 1, 16, 3))
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "github-output.txt"
            summary = Path(temp) / "github-summary.md"
            write_outcome(result, output, summary)
            self.assertIn("proceed=false\n", output.read_text())
            self.assertIn("SKIPPED", summary.read_text())
            self.assertNotIn("ENABLED", summary.read_text())

    def test_no_access_to_pipeline_or_merging(self):
        result = decide("schedule", SUMMER_CRON, at(2026, 7, 16, 3))
        self.assertTrue(result["proceed"])
        self.assertNotIn("qualified_pipeline_total", result)


if __name__ == "__main__":
    unittest.main()
