"""Unit tests for the isolated read-only Alpaca enrichment adapter."""
import unittest
from unittest.mock import patch

from app.alpaca_enrichment import MarketDataError, daily_history, latest_daily_bars


class AlpacaEnrichmentTests(unittest.TestCase):
    def test_missing_symbols_preserved(self):
        with patch("app.alpaca_enrichment._get", return_value={"bars": {"ABC": {"c": 3.0, "v": 100}}}) as get:
            result = latest_daily_bars(["abc", "xyz", "abc"])
        self.assertEqual(list(result), ["ABC", "XYZ"])
        self.assertEqual(result["ABC"]["status"], "retrieved")
        self.assertEqual(result["XYZ"]["status"], "missing")
        self.assertEqual(result["ABC"]["feed"], "iex")
        self.assertEqual(get.call_args.args[0], "/v2/stocks/bars/latest")

    def test_invalid_symbols_do_not_call_network(self):
        with patch("app.alpaca_enrichment._get") as get:
            with self.assertRaises(ValueError):
                latest_daily_bars(["AAPL?"])
            with self.assertRaises(ValueError):
                latest_daily_bars([f"A{i}" for i in range(26)])
            get.assert_not_called()

    def test_history_rejects_truncated_results(self):
        with patch("app.alpaca_enrichment._get", return_value={"bars": [{"c": 1}], "next_page_token": "more"}):
            with self.assertRaises(MarketDataError):
                daily_history("AAPL")

    def test_history_empty_is_missing(self):
        with patch("app.alpaca_enrichment._get", return_value={"bars": [], "next_page_token": None}):
            self.assertEqual(daily_history("AAPL")["status"], "missing")


if __name__ == "__main__":
    unittest.main()
