"""GEM trading view must fail closed on unverified event or market evidence."""
import json
import unittest
from datetime import date, timedelta

from gem_trading_advisory import (
    TRADE_COLUMNS, assess_gem_trade, attach_trade_fields, _rsi_14,
)


class GemTradingAdvisoryTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 10, 14)
        days = []
        d = self.today
        while len(days) < 35:
            if d.weekday() < 5:
                days.append(d)
            d -= timedelta(days=1)
        days.reverse()
        self.bars = [
            {"date": str(d), "close": 20 + i * .01 + (.4 if i % 2 == 0 else -.4),
             "volume": 600000}
            for i, d in enumerate(days)
        ]
        self.market = {"ABC": {
            "ticker": "ABC", "market_status": "MARKET_UPDATED",
            "last_session": str(days[-1]),
            "last_close_usd": str(self.bars[-1]["close"]),
            "relative_volume": "1.8",
            "market_source": "https://example.com/source",
            "price_bars_json": json.dumps(self.bars),
        }}
        self.row = {"Ticker": "ABC", "_eligible": True,
                    "GEM Status": "ELIGIBLE — RANKED; MANUAL REVIEW",
                    "Planned Exit (-3 days)": "2026-12-11"}
        self.status = {"feed_current": True, "sec_financing_source_current": True}

    def assess(self, row=None, market=None, status=None, today=None):
        return assess_gem_trade(row or self.row,
                                self.market if market is None else market,
                                self.status if status is None else status,
                                today or self.today)

    def test_all_rows_get_exported_trade_fields(self):
        watch = dict(self.row, _eligible=False)
        result = attach_trade_fields([self.row, watch], self.market,
                                     self.status, self.today)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(c in result[0] for c in TRADE_COLUMNS))
        self.assertEqual(result[1]["Trade assessment"],
                         "WAIT — BENCHMARKS UNVERIFIED")

    def test_no_buy_signal_with_35_close_only_bars(self):
        p = self.assess()
        self.assertTrue(p["fresh"])
        self.assertIsNotNone(p["sma20"])
        self.assertIsNone(p["sma50"])
        self.assertIsNone(p["macd"])
        self.assertIn("ATR: no high/low", p["gaps"])
        self.assertNotIn("BUY", p["recommendation"])

    def test_stale_market_data_blocks_entry(self):
        old_date = date(2026, 10, 9)
        self.assertEqual(self.assess(today=old_date)["date"], None)
        future = self.assess(today=date(2026, 10, 20))
        self.assertFalse(future["fresh"])
        self.assertEqual(future["recommendation"],
                         "WAIT — REFRESH MARKET DATA")

    def test_missing_sec_refresh_blocks_entry(self):
        p = self.assess(status={"feed_current": True,
                                "sec_financing_source_current": False})
        self.assertEqual(p["recommendation"], "WAIT — SOURCE RECHECK")

    def test_exit_warning_overrides_other_checks(self):
        row = dict(self.row, **{"GEM Status": "EXIT / FDA DECISION WARNING"})
        self.assertEqual(self.assess(row=row)["recommendation"],
                         "EXIT RISK — REVIEW NOW")

    def test_inconsistent_price_blocks_entry(self):
        market = {"ABC": dict(self.market["ABC"], last_close_usd="9999")}
        p = self.assess(market=market)
        self.assertEqual(p["recommendation"], "WAIT — REFRESH MARKET DATA")
        self.assertEqual(p["bars"], [])

    def test_rsi_flat_is_neutral(self):
        self.assertEqual(_rsi_14([15.0] * 35), 50.0)


if __name__ == "__main__":
    unittest.main()
