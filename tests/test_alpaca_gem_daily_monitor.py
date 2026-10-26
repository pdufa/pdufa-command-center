"""Offline regression tests: never call Alpaca or submit any orders."""
from __future__ import annotations
import io
import json
import unittest
from datetime import date, timedelta
from urllib.error import HTTPError

from scripts.alpaca_gem_watchlist import (
    add_symbol, get_watchlist, paper_credentials, AlpacaUnavailable
)
from scripts.alpaca_gem_daily_monitor import (
    evaluate, market_snapshot, clean_bars, collect
)


def fixture_bars(start=date(2026,3,1),n=140, *,break_sma=False):
    d=start
    out=[]
    i=0
    while len(out)<n:
        if d.weekday()<5:
            price=10.0 if not break_sma or len(out)<n-2 else 7.5
            out.append({
                "session":d.isoformat(), "open":price,
                "high":price+.12, "low":price-.12,
                "close":price, "volume":100000
            })
        d+=timedelta(days=1)
    return out


def response(payload):
    return io.BytesIO(json.dumps(payload).encode())


class WatchlistClientTests(unittest.TestCase):
    def test_paper_only(self):
        with self.assertRaisesRegex(AlpacaUnavailable,"Paper-only"):
            paper_credentials({"ALPACA_PAPER":"false",
                               "ALPACA_API_KEY":"key",
                               "ALPACA_SECRET_KEY":"secret"})
        self.assertEqual(
            paper_credentials({"ALPACA_PAPER":"true",
                               "ALPACA_API_KEY":"key",
                               "ALPACA_SECRET_KEY":"secret"}),
            ("key","secret"))

    def test_get_by_name_is_get_only(self):
        def fake(req,timeout):
            self.assertEqual(req.get_method(),"GET")
            self.assertEqual(timeout,25)
            self.assertIn("watchlists%3Aby_name",req.full_url.replace(":", "%3A"))
            return response({"assets":[{"symbol":"SRRK"}]})
        found=get_watchlist(credentials=("key","secret"),opener=fake)
        self.assertEqual(found["assets"][0]["symbol"],"SRRK")

    def test_add_existing_ticker_does_not_write(self):
        calls=[]
        def fake(req,timeout):
            calls.append(req.get_method())
            return response({"assets":[{"symbol":"SRRK"}]})
        add_symbol("srrk", credentials=("key","secret"),opener=fake)
        self.assertEqual(calls,["GET"])

    def test_explicit_add_only_posts_to_named_watchlist(self):
        calls=[]
        def fake(req,timeout):
            calls.append((req.get_method(),req.full_url))
            if len(calls)==1:
                return response({"assets":[{"symbol":"SRRK"}]})
            self.assertEqual(req.get_method(),"POST")
            self.assertIn("watchlists:by_name",req.full_url)
            self.assertEqual(json.loads(req.data),{"symbol":"ABEO"})
            return response({"assets":[{"symbol":"SRRK"},{"symbol":"ABEO"}]})
        result=add_symbol("abeo",credentials=("key","secret"),opener=fake)
        self.assertEqual(len(calls),2)
        self.assertEqual(result["assets"][-1]["symbol"],"ABEO")

    def test_invalid_ticker_blocks_before_http(self):
        def fake(*_args,**_kwargs):
            self.fail("network should never be accessed")
        with self.assertRaises(ValueError):
            add_symbol("XXX/PLACE",credentials=("key","secret"),opener=fake)


class DailyMonitorTests(unittest.TestCase):
    def test_market_data_require_minimum_window(self):
        self.assertEqual(clean_bars(fixture_bars(n=25)),[])
        self.assertIsNotNone(market_snapshot(clean_bars(fixture_bars())))

    def test_no_verified_events_never_buy(self):
        bars=fixture_bars()
        today=date.fromisoformat(bars[-1]["session"])
        r=evaluate("SRRK",bars,[],{},today=today)
        self.assertEqual(r["stage"],"WATCHING_ENTRY")
        self.assertEqual(r["alert"],"ENTRY_BLOCKED")
        self.assertFalse(r["market_cap_filter_active"])

    def test_paper_position_exit_warning_uses_two_closes(self):
        bars=fixture_bars(break_sma=True)
        today=date.fromisoformat(bars[-1]["session"])
        positions={"SRRK":{"qty":"1","avg_entry_price":"10"}}
        r=evaluate("SRRK",bars,[],positions,today=today)
        self.assertEqual(r["stage"],"PAPER_POSITION_MONITOR")
        self.assertEqual(r["alert"],"EXIT_WARNING")
        self.assertEqual(r["reason"],"TWO_CLOSES_BELOW_SMA20")
        self.assertEqual(r["trailing_stop"],"UNAVAILABLE_POSITION_ENTRY_DATE")

    def test_not_a_paper_position_no_exit_alert(self):
        bars=fixture_bars(break_sma=True)
        today=date.fromisoformat(bars[-1]["session"])
        positions={"SRRK":{"qty":"0","avg_entry_price":"10"}}
        r=evaluate("SRRK",bars,[],positions,today=today)
        self.assertEqual(r["alert"],"ENTRY_BLOCKED")

    def test_stale_price_blocks_every_signal(self):
        bars=fixture_bars()
        today=date.fromisoformat(bars[-1]["session"])+timedelta(days=10)
        r=evaluate("SRRK",bars,[],{},today=today)
        self.assertEqual(r["stage"],"DATA_BLOCKED")
        self.assertEqual(r["alert"],"NONE")

    def test_broken_or_duplicate_history_blocks(self):
        b=fixture_bars()
        b[-1]["close"]=-2
        self.assertEqual(clean_bars(b),[])
        b=fixture_bars()
        b[-1]["session"]=b[-2]["session"]
        self.assertEqual(clean_bars(b),[])


if __name__=="__main__":
    unittest.main()
