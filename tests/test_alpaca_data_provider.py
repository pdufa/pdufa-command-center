"""Offline contract and safety checks for Alpaca-only GEM chart monitoring."""
import io
import json
import tempfile
import unittest
from datetime import date,datetime,timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from alpaca_data_provider import (
    alpaca_daily_bars,assess,completed_session,programs_from_membership,
    paper_keys,paper_positions,rsi14,technical_snapshot,get_symbol_report
)
from scripts.alpaca_gem_eod_scan import scan


def candles(end=date(2026,10,16),amount=72,weak=False):
    days=[]
    d=end-timedelta(days=130)
    while d<=end:
        if d.weekday()<5:
            days.append(d)
        d+=timedelta(days=1)
    days=days[-amount:]
    out=[]
    for i,d in enumerate(days):
        price=12+.01*i
        if weak and i>=len(days)-2:
            price-=1.5
        out.append({"session":d,"open":price,
                    "high":price+.2,"low":price-.2,
                    "close":price,"volume":110000})
    return out


def alpaca_response(rows):
    return io.BytesIO(json.dumps({"bars":[{"t":x["session"].isoformat()+"T04:00:00Z",
        "o":x["open"],"h":x["high"],"l":x["low"],
        "c":x["close"],"v":x["volume"]} for x in rows],
        "next_page_token":None}).encode())


class ProviderTests(unittest.TestCase):
    def test_paper_only_and_missing_keys(self):
        with self.assertRaises(ValueError):
            paper_keys({"ALPACA_PAPER":"false","ALPACA_API_KEY":"a",
                        "ALPACA_SECRET_KEY":"b"})
        with self.assertRaises(ValueError):
            paper_keys({"ALPACA_PAPER":"true"})
        self.assertEqual(paper_keys({"ALPACA_PAPER":"true",
                                    "ALPACA_API_KEY":"a",
                                    "ALPACA_SECRET_KEY":"b"}),("a","b"))

    def test_market_close_and_weekend_gate(self):
        z=ZoneInfo("America/New_York")
        self.assertEqual(completed_session(
            datetime(2026,10,16,15,30,tzinfo=z)),date(2026,10,15))
        self.assertEqual(completed_session(
            datetime(2026,10,16,17,30,tzinfo=z)),date(2026,10,16))
        self.assertEqual(completed_session(
            datetime(2026,10,18,10,tzinfo=z)),date(2026,10,16))

    def test_stage_exact_program_identity_and_dedupe_only_for_api(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/"membership.json"
            file.write_text(json.dumps({"stages":{
                "GEM":{"entries":{
                    "a":{"ticker":"CAPR","status":"ACTIVE","exact_program":"CAPR|A"},
                    "b":{"ticker":"CAPR","status":"ACTIVE","exact_program":"CAPR|B"},
                    "c":{"ticker":"SRRK","status":"LEFT"}}},
                "GEM_JR":{"entries":{
                    "d":{"ticker":"MLYS","status":"ACTIVE"}}}
            }}))
            records=programs_from_membership(file)
            self.assertEqual(len(records),3)
            self.assertEqual({x["ticker"] for x in records},{"CAPR","MLYS"})
            self.assertEqual(len([r for r in records if r["ticker"]=="CAPR"]),2)

    def test_alpaca_sip_requests_split_adjusted_and_never_posts(self):
        rows=candles()
        def fake(req,timeout):
            url=req.full_url
            self.assertEqual(req.get_method(),"GET")
            self.assertIn("feed=sip",url)
            self.assertIn("adjustment=split",url)
            self.assertIn("timeframe=1Day",url)
            self.assertEqual(timeout,30)
            return alpaca_response(rows)
        result=alpaca_daily_bars("CAPR",("k","s"),
                                 as_of=date(2026,10,16),opener=fake)
        self.assertEqual(len(result),len(rows))
        self.assertEqual(result[-1]["session"],date(2026,10,16))
        self.assertGreater(technical_snapshot(result)["atr14"],0)

    def test_unaudited_clinical_timing_never_produces_entry(self):
        r=assess("CAPR",candles(),[],as_of=date(2026,10,16))
        self.assertEqual(r["signal"],"ENTRY_BLOCKED")
        self.assertEqual(r["provider"],"ALPACA")
        self.assertFalse(r["market_cap_filter_active"])
        self.assertIsNone(r["paper_position"])

    def test_paper_position_stays_until_exit_rule(self):
        pos={"CAPR":{"held":True}}
        r=assess("CAPR",candles(),[],positions=pos,
                 as_of=date(2026,10,16))
        self.assertEqual(r["signal"],"STAY_REVIEW")
        self.assertEqual(r["position_scope"],"ALPACA_PAPER_ONLY")
        r=assess("CAPR",candles(weak=True),[],positions=pos,
                 as_of=date(2026,10,16))
        self.assertEqual(r["signal"],"EXIT_WARNING")
        self.assertEqual(r["reason"],"TWO_CLOSES_BELOW_SMA20")

    def test_old_or_empty_data_is_blocked(self):
        old=candles(end=date(2026,8,14))
        self.assertEqual(assess("CAPR",old,[],as_of=date(2026,10,16))["signal"],
                         "DATA_BLOCKED")
        self.assertEqual(assess("CAPR",[],[],as_of=date(2026,10,16))["signal"],
                         "DATA_BLOCKED")

    def test_active_trading_setup_requires_verified_events(self):
        rows=candles()
        last=rows[-1]
        # A separate fabricated test fixture ONLY: breakout and volume
        # must not be confused with an empirical stock recommendation.
        last.update(open=13.0,high=13.4,low=12.95,close=13.32,volume=380000)
        prior_high=max(x["high"] for x in rows[-11:-1])
        self.assertGreater(last["close"],prior_high)
        dates={"phase3_public_date":date(2026,1,2),
               "second_financing_public_date":date(2026,2,3),
               "pdufa_date":date(2026,12,3),
               "early_fda_action_date":None}
        with patch("alpaca_data_provider.validate_event",return_value=("",dates)):
            r=assess("CAPR",rows,[{"ticker":"CAPR","event_key":"CAPR|A"}],
                     as_of=date(2026,10,16))
        self.assertIn(r["signal"],("WAIT","ENTRY_SETUP_RECHECK"))
        self.assertIsInstance(r["entry_score_preview"],int)

    def test_position_api_is_get_only_and_scrubs_account_fields(self):
        def fake(req,timeout):
            self.assertEqual(req.get_method(),"GET")
            self.assertIn("/v2/positions",req.full_url)
            return io.BytesIO(json.dumps([
                {"symbol":"CAPR","qty":"5","avg_entry_price":"10",
                 "account_id":"secret-account"}]).encode())
        positions=paper_positions(("k","s"),opener=fake)
        self.assertEqual(positions["CAPR"]["held"],True)
        self.assertNotIn("account_id",positions["CAPR"])

    def test_systemwide_scan_uses_each_unique_active_ticker(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/"member.json"
            file.write_text(json.dumps({"stages":{"GEM":{"entries":{
                "a":{"status":"ACTIVE","ticker":"CAPR"},
                "b":{"status":"ACTIVE","ticker":"CAPR"}}},
                "GEM_JR":{"entries":{"c":{"status":"ACTIVE","ticker":"MLYS"}}}}}))
            calls=[]
            def fake(symbol,keys,events,**kwargs):
                calls.append(symbol)
                return {"ticker":symbol,"signal":"ENTRY_BLOCKED","reason":"NO_SOURCE"}
            result=scan(membership=file,events=[],credentials=("k","s"),
                        as_of=date(2026,10,16),get_report=fake,positions={})
            self.assertEqual(result["active_programs"],3)
            self.assertEqual(result["unique_tickers"],2)
            self.assertEqual(sorted(calls),["CAPR","MLYS"])
            self.assertEqual(result["orders_placed"],0)


if __name__=="__main__":
    unittest.main()
