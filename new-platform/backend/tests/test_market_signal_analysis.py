"""Tests for research-only price and IEX volume signals."""
import unittest
from app.market_signal_analysis import summarize_daily_bars


class MarketSignalTests(unittest.TestCase):
    def test_complete_history(self):
        bars = [{"close": 10 + i, "volume": 100 + i} for i in range(20)]
        result = summarize_daily_bars(bars)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["return20Pct"], 190.0)
        self.assertEqual(result["averageVolume20"], 109.5)
        self.assertEqual(result["volumeRatio20"], round(119 / 109.5, 4))
        self.assertIsNone(result["recommendation"])

    def test_missing_data_is_not_imputed(self):
        result = summarize_daily_bars([{"close": 10, "volume": 100}])
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(result["return20Pct"])

    def test_zero_volume_does_not_divide(self):
        result = summarize_daily_bars([{"close": 10, "volume": 0}] * 20)
        self.assertIsNone(result["volumeRatio20"])


if __name__ == "__main__":
    unittest.main()
