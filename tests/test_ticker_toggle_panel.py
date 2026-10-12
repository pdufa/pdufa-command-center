"""Watch/Trading toggles stay ticker-level, compact, and shared across #2/#3/#4."""
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

    def test_every_section_has_first_columns_and_shared_callbacks(self):
        self.assertLessEqual(ROWS_PER_PAGE, 10)
        module = (ROOT / "ticker_toggle_panel.py").read_text(encoding="utf-8")
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        unified = (ROOT / "unified_clinical_trading.py").read_text(encoding="utf-8")
        for filename, content in (("ticker_toggle_panel.py", module),
                                  ("app.py", app),
                                  ("unified_clinical_trading.py", unified)):
            ast.parse(content, filename=filename)
        self.assertIn('st.button("−" if symbol in watch else "+"', module)
        self.assertIn('st.button("−" if symbol in trade else "+"', module)
        self.assertIn('on_click=_toggle, args=(symbol, "watch")', module)
        self.assertIn('on_click=_toggle, args=(symbol, "trade")', module)
        self.assertIn('render_ticker_toggle_panel("pipeline_2", prepared', app)
        self.assertIn('render_ticker_toggle_panel("pre3_3", tab', app)
        for marker in ("overview_2", "overview_3", "overview_4", "post3_4"):
            self.assertIn(f'render_ticker_toggle_panel("{marker}"', unified)
        self.assertIn("streamlit-js-eval==1.0.0",
                      (ROOT / "requirements.txt").read_text())

    def test_buttons_are_manual_labels_not_broker_orders(self):
        source = (ROOT / "ticker_toggle_panel.py").read_text(encoding="utf-8")
        self.assertIn("NOT a broker transaction", source)
        self.assertIn("green − selected / white + add", source)


if __name__ == "__main__":
    unittest.main()
