"""Regression tests: GitHub cron starts are not guaranteed to be on time."""
import unittest
from datetime import datetime, timezone

from scripts.surveillance_schedule import mode_for_schedule


def at(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class SurveillanceScheduleTests(unittest.TestCase):
    def test_delayed_summer_daily_runs_only_correct_utc_variant(self):
        late = at(2026, 7, 10, 20)
        self.assertEqual(mode_for_schedule("15 12 * * *", late), "daily")
        self.assertEqual(mode_for_schedule("15 13 * * *", late), "skip")

    def test_delayed_winter_daily_runs_only_correct_utc_variant(self):
        late = at(2026, 1, 10, 20)
        self.assertEqual(mode_for_schedule("15 12 * * *", late), "skip")
        self.assertEqual(mode_for_schedule("15 13 * * *", late), "daily")

    def test_delay_past_utc_midnight_does_not_drop_scan(self):
        after_midnight = at(2026, 7, 11, 1)
        self.assertEqual(mode_for_schedule("15 12 * * *", after_midnight), "daily")

    def test_sunday_four_am_handles_spring_dst(self):
        late = at(2026, 3, 8, 18)
        self.assertEqual(mode_for_schedule("0 11 * * 0", late), "weekly")
        self.assertEqual(mode_for_schedule("0 12 * * 0", late), "skip")

    def test_sunday_four_am_handles_fall_dst(self):
        late = at(2026, 11, 1, 18)
        self.assertEqual(mode_for_schedule("0 11 * * 0", late), "skip")
        self.assertEqual(mode_for_schedule("0 12 * * 0", late), "weekly")

    def test_first_of_month_is_only_monthly_trigger(self):
        july_first = at(2026, 7, 1, 20)
        jan_first = at(2026, 1, 1, 20)
        self.assertEqual(mode_for_schedule("30 11 1 * *", july_first), "monthly")
        self.assertEqual(mode_for_schedule("30 12 1 * *", july_first), "skip")
        self.assertEqual(mode_for_schedule("30 12 1 * *", jan_first), "monthly")

    def test_unknown_cron_is_rejected(self):
        self.assertEqual(mode_for_schedule("0 0 * * *", at(2026, 7, 10, 20)), "skip")
        self.assertEqual(mode_for_schedule("", at(2026, 7, 10, 20)), "skip")

    def test_naive_now_fails_closed(self):
        with self.assertRaises(ValueError):
            mode_for_schedule("15 12 * * *", datetime(2026, 7, 10, 20))


if __name__ == "__main__":
    unittest.main()
