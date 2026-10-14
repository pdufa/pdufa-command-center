"""Provisional GEM entry/exit scores must preserve source gates and coverage."""
import json
import unittest
from datetime import date, timedelta

from gem_trading_advisory import (
    TRADE_COLUMNS, _score_gem_trade, assess_gem_trade, attach_trade_fields,
)


def trading_fixture():
    today = date(2026, 10, 14)
    dates = []
    day = today
    while len(dates) < 65:
        if day.weekday() < 5:
            dates.append(day)
        day -= timedelta(days=1)
    dates.reverse()
    bars = [
        {"date": str(d), "close": round(12 + i * .06 + (.15 if i % 2 else -.15), 2),
         "volume": 800000}
        for i, d in enumerate(dates)
    ]
    market = {"TEST": {
        "ticker": "TEST", "market_status": "MARKET_UPDATED",
        "market_source": "https://example.com/daily",
        "last_session": str(today),
        "last_close_usd": str(bars[-1]["close"]),
        "relative_volume": "1.8",
        "price_bars_json": json.dumps(bars),
    }}
    row = {
        "Ticker": "TEST", "_eligible": True,
        "GEM Score /100": 84,
        "PDUFA Date Verified": True, "Days to PDUFA": 45,
        "GEM Status": "ELIGIBLE — RANKED; MANUAL REVIEW",
        "Risks / Evidence Gaps": "No flagged issue in saved data",
    }
    status = {"feed_current": True, "sec_financing_source_current": True}
    return row, market, status, today


class GemTradingScoreTests(unittest.TestCase):
    def test_scores_export_separately_and_preserve_gem_quality(self):
        row, market, status, today = trading_fixture()
        result = attach_trade_fields([row], market, status, today)[0]
        self.assertEqual(result["GEM Score /100"], 84)
        self.assertEqual(result["Entry Coverage /100"], 80)
        self.assertEqual(result["Exit Coverage /100"], 85)
        self.assertIsInstance(result["Entry Score /100"], int)
        self.assertIsInstance(result["Exit Risk /100"], int)
        self.assertTrue(all(column in result for column in TRADE_COLUMNS))
        self.assertIn("N/A/20", result["Entry Score Breakdown"])
        self.assertIn("N/A/15", result["Exit Risk Breakdown"])
        self.assertIn("PROVISIONAL", result["Entry Score Status"])

    def test_entry_score_responds_to_volume_but_never_auto_buys(self):
        row, market, status, today = trading_fixture()
        fresh = attach_trade_fields([row], market, status, today)[0]
        market["TEST"]["relative_volume"] = "0.9"
        weak = attach_trade_fields([row], market, status, today)[0]
        self.assertEqual(fresh["Entry Score /100"] - weak["Entry Score /100"], 10)
        self.assertNotIn("BUY", fresh["Trade assessment"])
        self.assertLessEqual(fresh["Entry Score /100"], fresh["Entry Coverage /100"])

    def test_invalid_or_stale_sources_fail_closed(self):
        row, market, status, today = trading_fixture()
        status["sec_financing_source_current"] = False
        found = attach_trade_fields([row], market, status, today)[0]
        self.assertIsNone(found["Entry Score /100"])
        self.assertIsNone(found["Exit Risk /100"])
        self.assertEqual(found["Entry Coverage /100"], 0)
        status["sec_financing_source_current"] = True
        market["TEST"]["last_close_usd"] = "999"
        found = attach_trade_fields([row], market, status, today)[0]
        self.assertIsNone(found["Entry Score /100"])
        self.assertIsNone(found["Exit Risk /100"])

    def test_watch_only_can_have_research_exit_risk_but_not_entry(self):
        row, market, status, today = trading_fixture()
        row["_eligible"] = False
        found = attach_trade_fields([row], market, status, today)[0]
        self.assertIsNone(found["Entry Score /100"])
        self.assertIsNotNone(found["Exit Risk /100"])
        self.assertIn("NOT ELIGIBLE", found["Entry Score Status"])
        self.assertIn("NO POSITION ASSUMED", found["Exit Risk Status"])

    def test_hard_fda_exit_overrides_entry_score(self):
        row, market, status, today = trading_fixture()
        row["Days to PDUFA"] = 2
        found = attach_trade_fields([row], market, status, today)[0]
        self.assertIsNone(found["Entry Score /100"])
        self.assertIn("NO NEW ENTRY", found["Entry Score Status"])
        self.assertIn("HARD EXIT WARNING", found["Exit Risk Status"])

    def test_negative_clinical_risk_blocks_entry_score(self):
        row, market, status, today = trading_fixture()
        row["Risks / Evidence Gaps"] = "Verified Phase 3 negative outcome — serious clinical risk"
        found = attach_trade_fields([row], market, status, today)[0]
        self.assertIsNone(found["Entry Score /100"])
        self.assertIn("NOT ELIGIBLE", found["Entry Score Status"])
        self.assertGreaterEqual(found["Exit Risk /100"], 20)

    def test_unverified_pdufa_never_receives_timing_points(self):
        row, market, status, today = trading_fixture()
        row["PDUFA Date Verified"] = False
        found = attach_trade_fields([row], market, status, today)[0]
        self.assertEqual(found["Entry Coverage /100"], 65)
        self.assertEqual(found["Exit Coverage /100"], 60)
        self.assertIn("N/A/15", found["Entry Score Breakdown"])
        self.assertIn("N/A/25", found["Exit Risk Breakdown"])


if __name__ == "__main__":
    unittest.main()
