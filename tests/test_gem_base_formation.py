"""EOD base observations should be reproducible, source-gated and never auto-trade."""
import json
import unittest
from datetime import date, timedelta
from pathlib import Path

from gem_base_analysis import detect_closing_base, base_chart_frame
from gem_trading_advisory import assess_gem_trade, attach_trade_fields

ROOT = Path(__file__).resolve().parents[1]


def history():
    prices = [
        10.0, 10.4, 10.5, 10.6, 10.45, 10.55, 10.5, 10.4, 10.3, 10.2,
        10.01, 10.4, 10.5, 10.65, 10.35, 10.42, 10.44, 10.43, 10.45, 10.44,
    ]
    start = date(2026, 9, 1)
    days = []
    d = start
    while len(days) < 21:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return [
        {"date": d, "close": c, "volume": 1_000_000 if i < 15 else 400_000}
        for i, (d, c) in enumerate(zip(days[:20], prices))
    ] + [{"date": days[-1], "close": 10.48, "volume": 300_000}]


class BaseFormationTests(unittest.TestCase):
    def test_repeated_support_range_and_volume_dry_up(self):
        base = detect_closing_base(history(), fresh=True)
        self.assertEqual(base["status"], "BASE FORMING — PRELIMINARY")
        self.assertEqual(base["support"], 10)
        self.assertEqual(base["resistance"], 10.65)
        self.assertEqual(base["touches"], 2)
        self.assertLessEqual(base["width_pct"], 18)
        self.assertLessEqual(base["contraction"], .75)
        self.assertLessEqual(base["volume_ratio"], .85)
        self.assertFalse(base["confirmed_breakout"])

    def test_bull_breakout_requires_close_above_prior_resistance_and_volume(self):
        h = history()
        h[-1].update(close=11, volume=2_000_000)
        base = detect_closing_base(h, fresh=True)
        self.assertTrue(base["confirmed_breakout"])
        self.assertEqual(base["status"], "BREAKOUT CANDIDATE — VOLUME CONFIRMED")
        h[-1]["volume"] = 600_000
        base = detect_closing_base(h, fresh=True)
        self.assertFalse(base["confirmed_breakout"])
        self.assertEqual(base["status"], "ABOVE BASE — BREAKOUT VOLUME NOT CONFIRMED")

    def test_breakdown_is_warning_and_levels_do_not_include_today(self):
        h = history()
        h[-1]["close"] = 9
        base = detect_closing_base(h, fresh=True)
        self.assertTrue(base["support_break"])
        self.assertEqual(base["support"], 10)
        self.assertEqual(base["status"], "SUPPORT BREAK — REVIEW")

    def test_stale_and_insufficient_data_fail_closed(self):
        self.assertIn("NOT AVAILABLE", detect_closing_base(history()[:20], fresh=True)["status"])
        h = history()
        h[-1].update(close=11, volume=2_000_000)
        base = detect_closing_base(h, fresh=False)
        self.assertIn("STALE", base["status"])
        self.assertFalse(base["confirmed_breakout"])
        self.assertFalse(base["support_break"])

    def test_no_lookahead_levels_on_older_bars(self):
        h = history()
        # Duplicate a 30-session lead-in for chart history.
        earlier = [
            {"date": date(2026, 7, 1) + timedelta(days=i),
             "close": 9.3 + i / 100, "volume": 800_000}
            for i in range(30)
        ]
        h = earlier + h
        plotted = base_chart_frame(h, detect_closing_base(h, fresh=True))
        self.assertTrue(all(x["Base support (closing)"] is None
                            for x in plotted[:-21]))
        self.assertEqual(plotted[-1]["Base support (closing)"], 10)
        self.assertTrue(any(x["SMA 50"] is not None for x in plotted))

    def test_market_inconsistency_cannot_generate_base_labels(self):
        h = history()
        today = h[-1]["date"]
        record = {
            "ticker": "BASE", "last_session": str(today),
            "market_status": "MARKET_UPDATED", "market_source": "https://example.org/eod",
            "last_close_usd": "10.48",
            "relative_volume": "0.7",
            "price_bars_json": json.dumps([{**x, "date": str(x["date"])} for x in h]),
        }
        row = {"Ticker": "BASE", "_eligible": False}
        profile = assess_gem_trade(row, {"BASE": record}, {}, today)
        self.assertEqual(profile["base"]["status"], "BASE FORMING — PRELIMINARY")
        result = attach_trade_fields([row], {"BASE": record}, {}, today)[0]
        self.assertEqual(result["Base support"], 10)
        self.assertEqual(result["Base status"], "BASE FORMING — PRELIMINARY")
        self.assertEqual(result["Trade assessment"], "WAIT — BENCHMARKS UNVERIFIED")
        record["last_close_usd"] = "99"
        invalid = assess_gem_trade(row, {"BASE": record}, {}, today)
        self.assertIsNone(invalid["base"]["support"])
        self.assertIn("NOT AVAILABLE", invalid["base"]["status"])

    def test_base_charts_present_for_gem_jr_gem_and_stock_pages(self):
        jr = (ROOT / "gem_jr_ui.py").read_text()
        gem = (ROOT / "gem_potential_ui.py").read_text()
        master = (ROOT / "gem_trading_advisory.py").read_text()
        stock = (ROOT / "pages/01_Stock_Chart.py").read_text()
        self.assertIn("render_base_chart_for_ticker(", jr)
        self.assertIn("render_base_chart_for_ticker(", gem)
        self.assertIn("render_base_formation_chart(p)", master)
        self.assertIn("render_base_chart_for_ticker(", stock)
        self.assertIn('"ATR@tv-basicstudies"', stock)
        self.assertIn('"MASimple@tv-basicstudies"', stock)
        self.assertIn('"VWAP@tv-basicstudies"', stock)
        self.assertIn('height=240 if compact else 285', master)


if __name__ == "__main__":
    unittest.main()
