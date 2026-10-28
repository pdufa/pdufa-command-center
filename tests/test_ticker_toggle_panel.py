"""Watch/Trading toggles stay ticker-level, compact, and shared across #2/#3/#4."""
from supported_dashboard_checks import run_frontend_contract
import ast
import json
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
from ticker_toggle_panel import (
    ROWS_PER_PAGE, clean_ticker, parse_saved, serialize_selections,
    ticker_universe, toggle_membership,
)


class TickerToggleTests(unittest.TestCase):
    def test_unique_tickers_across_duplicate_trials_and_case(self):
        sample = pd.DataFrame({"Ticker": ["tern", "TERN", "XFOR", "BIVI", None, "", "??"]})
        self.assertEqual(ticker_universe(sample), ["BIVI", "TERN", "XFOR"])
        self.assertEqual(ticker_universe([
            {"ticker": "OCGN"}, {"Ticker": "ocgn"}, {"Ticker": "XFOR"},
        ]), ["OCGN", "XFOR"])

    def test_invalid_ticker_does_not_add_or_crash(self):
        self.assertEqual(clean_ticker(" "), "")
        self.assertEqual(clean_ticker("?"), "")
        self.assertEqual(toggle_membership(["TERN"], "???"), ["TERN"])

    def test_watch_and_trade_are_independent_ticker_sets(self):
        selections = {"watchlist": ["TERN"], "trading_tickers": ["OCGN"]}
        selections["watchlist"] = toggle_membership(selections["watchlist"], "OCGN")
        self.assertEqual(selections["trading_tickers"], ["OCGN"])
        self.assertEqual(selections["watchlist"], ["OCGN", "TERN"])
        selections["trading_tickers"] = toggle_membership(selections["trading_tickers"], "OCGN")
        self.assertEqual(selections["watchlist"], ["OCGN", "TERN"])
        self.assertEqual(selections["trading_tickers"], [])

    def test_browser_save_load_and_malformed_payload(self):
        stored = serialize_selections({
            "watchlist": ["tern", "TERN", "XFOR"],
            "trading_tickers": ["OCGN"],
        })
        self.assertEqual(parse_saved(stored), {
            "watch": ["TERN", "XFOR"], "trade": ["OCGN"],
        })
        self.assertIsNone(parse_saved('{"watch":["TERN"]}'))
        self.assertIsNone(parse_saved("not json"))
        self.assertIsNone(parse_saved({"version": 1, "watch": "", "trade": []}))

    def test_supported_wt_preserves_selection_scope_without_creating_hidden_studies(self):
        """Retained product contract, executed against supported Next.js code."""
        self.assertGreater(run_frontend_contract('wt-chart-checkbox-map.test.cjs'), 0)
        self.assertGreater(run_frontend_contract('gem-original-checkbox-groups.test.cjs'), 0)

    def test_buttons_are_manual_labels_not_broker_orders(self):
        source = (ROOT / "ticker_toggle_panel.py").read_text(encoding="utf-8")
        self.assertIn("NOT a broker transaction", source)
        self.assertIn("green W/T selected / white not selected", source)


if __name__ == "__main__":
    unittest.main()
