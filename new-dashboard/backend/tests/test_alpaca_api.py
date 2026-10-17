"""Offline checks for the isolated Alpaca backend; no real account required."""
import os
import sys
import unittest
from unittest.mock import patch
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import alpaca_api as api


class AlpacaAPITests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "DASHBOARD_API_TOKEN": "server-secret",
            "ALPACA_API_KEY": "paper-demo",
            "ALPACA_SECRET_KEY": "paper-secret",
            "ALPACA_PAPER": "true",
            "ALPACA_FEED": "iex",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_status_is_not_live_verification(self):
        result = api.status("server-secret")
        self.assertTrue(result["configured"])
        self.assertFalse(result["tested_live"])
        self.assertFalse(result["source"]["is_consolidated"])

    def test_rejects_missing_or_invalid_server_token(self):
        for bad in (None, "", "not-the-token"):
            with self.assertRaises(HTTPException) as err:
                api.status(bad)
            self.assertEqual(err.exception.status_code, 401)

    def test_without_server_token_env_configuration_fails_closed(self):
        del os.environ["DASHBOARD_API_TOKEN"]
        with self.assertRaises(HTTPException) as err:
            api.status("anything")
        self.assertEqual(err.exception.status_code, 503)

    def test_live_brokerage_mode_rejected(self):
        os.environ["ALPACA_PAPER"] = "false"
        with self.assertRaises(HTTPException) as err:
            api.status("server-secret")
        self.assertEqual(err.exception.status_code, 503)

    def test_missing_keys_rejected(self):
        del os.environ["ALPACA_API_KEY"]
        with self.assertRaises(HTTPException) as err:
            api.status("server-secret")
        self.assertEqual(err.exception.status_code, 503)

    def test_invalid_ticker_rejected(self):
        for invalid in ("", "AAPL/../", "AAPL?", "TOO-LONG-SYMBOL"):
            with self.assertRaises(HTTPException):
                api._symbol(invalid)

    def test_indicators_never_fabricate_rvol_or_vwap(self):
        bars = []
        for index in range(80):
            value = 10 + (index / 10)
            bars.append({"time": f"2026-01-{index % 28 + 1:02}T00:00:00Z",
                         "open": value, "high": value + 1, "low": value - 1,
                         "close": value + 0.2, "volume": 10000 + index})
        result = api._indicators(bars, "iex")
        self.assertIsNotNone(result["values"]["sma20"])
        self.assertIsNotNone(result["values"]["sma50"])
        self.assertIsNotNone(result["values"]["rsi14"])
        self.assertIsNotNone(result["values"]["atr14"])
        self.assertIsNotNone(result["values"]["macd_12_26_9"])
        self.assertIsNone(result["values"]["rvol20"])
        self.assertIsNone(result["values"]["vwap_session"])
        self.assertEqual(result["available_count"], 5)
        self.assertEqual(result["possible_count"], 7)
        self.assertFalse(result["source"]["is_consolidated"])

    def test_insufficient_history_marks_inputs_unavailable(self):
        result = api._indicators([], "iex")
        self.assertEqual(result["available_count"], 0)
        self.assertTrue(all(value is None for value in result["values"].values()))

    def test_sip_feed_labels_consolidation_without_inventing_rvol(self):
        os.environ["ALPACA_FEED"] = "sip"
        result = api.status("server-secret")
        self.assertTrue(result["source"]["is_consolidated"])
        result = api._indicators([], "sip")
        self.assertIsNone(result["values"]["rvol20"])


if __name__ == "__main__":
    unittest.main()
