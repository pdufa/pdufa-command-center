"""Shared PDUFA trading-window contract and weekend-safe deadline tests."""
import unittest
from datetime import date, timedelta
from trade_window import (EXIT_BUFFER_DAYS, MIN_NEW_ENTRY_DAYS,
                          calendar_exit_target, is_new_entry_window,
                          latest_weekday_exit)


class TradeWindowContractTests(unittest.TestCase):
    def test_single_exact_exit_rule(self):
        target = date(2026, 11, 18)
        self.assertEqual(EXIT_BUFFER_DAYS, 3)
        self.assertEqual(MIN_NEW_ENTRY_DAYS, 4)
        self.assertEqual(calendar_exit_target(target), date(2026, 11, 15))
        self.assertTrue(is_new_entry_window(4))
        self.assertTrue(is_new_entry_window(91))
        self.assertFalse(is_new_entry_window(3))
        self.assertFalse(is_new_entry_window(None))
        self.assertFalse(is_new_entry_window(True))

    def test_weekend_deadline_moves_earlier_not_later(self):
        # The third calendar day before Wed Nov 18 is Sunday Nov 15;
        # the provisional last weekday exit is Friday Nov 13.
        target = date(2026, 11, 18)
        self.assertEqual(latest_weekday_exit(target), date(2026, 11, 13))
        self.assertLessEqual(latest_weekday_exit(target),
                             calendar_exit_target(target))

    def test_non_weekend_keeps_exact_calendar_cutoff(self):
        target = date(2026, 11, 20)
        self.assertEqual(calendar_exit_target(target), date(2026, 11, 17))
        self.assertEqual(latest_weekday_exit(target), date(2026, 11, 17))

    def test_modules_share_cutoff_not_an_outdated_seven(self):
        from pathlib import Path
        base = Path(__file__).resolve().parents[1]
        for name in ("gem_scans.py", "gem_calibration.py",
                     "post_phase3_unified.py", "post_phase3_priority.py",
                     "post_phase3_lifecycle.py", "post_phase3_trade_backtest.py"):
            self.assertIn("from trade_window import",
                          (base/name).read_text(encoding="utf-8"), name)
        self.assertIn("(-3d, weekday-adjusted)",
                      (base/"post_phase3_lifecycle.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
