"""Alpaca GEM/JR daily provider tests with a synthetic API response, no network."""
import io
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from alpaca_gem_provider import (
    active_stage_programs, assess_symbol, current_completed_session,
    provider_bars, rsi14
)


def fake_prices():
    out=[]
    dt=date(2026,7,25)
    for i in range(85):
        t=dt+timedelta(days=i)
        if t.weekday()>=5:
            continue
        n=len(out)
        price=20+0.02*n
        out.append({"t":t.isoformat()+"T04:00:00Z","o":price,
                    "h":price+.2,"l":price-.2,"c":price,"v":120000})
    return out


class FakeResponse(io.BytesIO):
    pass


class ProviderTests(unittest.TestCase):
    def test_last_complete_session_uses_eastern_timezone(self):
        et=ZoneInfo("America/New_York")
        self.assertEqual(current_completed_session(
            datetime(2026,10,16,15,40,tzinfo=et)),date(2026,10,15))
        self.assertEqual(current_completed_session(
            datetime(2026,10,16,18,10,tzinfo=et)),date(2026,10,16))
        self.assertEqual(current_completed_session(
            datetime(2026,10,18,12,0,tzinfo=et)),date(2026,10,16))

    def test_exact_programs_do_not_claim_missing_stages(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"gem_stage_membership.json"
            path.write_text(json.dumps({"stages":{
                "GEM":{"entries":{
                    "a":{"status":"ACTIVE","ticker":"SRRK",
                         "exact_program":"SRRK|APITEGROMAB"},
                    "b":{"status":"LEFT","ticker":"NOPE"}
                }},
                "GEM_JR":{"entries":{
                    "c":{"status":"ACTIVE","ticker":"CAPR"}
                }}}}))
            rows=active_stage_programs(path)
            self.assertEqual(len(rows),2)
            self.assertEqual({r["ticker"] for r in rows},{"SRRK","CAPR"})
            self.assertEqual({r["stage"] for r in rows},{"GEM","GEM_JR"})

    def test_sip_split_adjusted_eod_feed_and_entry_evidence_gate(self):
        dates=fake_prices()
        def fake(req, timeout):
            url=req.full_url
            self.assertIn("feed=sip",url)
            self.assertIn("adjustment=split",url)
            self.assertIn("timeframe=1Day",url)
            self.assertEqual(req.get_method(),"GET")
            self.assertEqual(timeout,30)
            return FakeResponse(json.dumps({"bars":dates,"symbol":"TEST",
                                            "next_page_token":None}).encode())
        now=datetime(2026,10,16,18,tzinfo=ZoneInfo("America/New_York"))
        result=assess_symbol("TEST",credentials=("paper","secret"),now=now,
                             verified_events=[],feed="sip",fetch=fake)
        self.assertEqual(result["provider"],"ALPACA")
        self.assertEqual(result["feed"],"sip")
        self.assertEqual(result["alert"],"ENTRY_BLOCKED")
        self.assertEqual(result["source_coverage"],"SIP_CONSOLIDATED")
        self.assertIsInstance(result["technical"]["sma20"],float)
        self.assertIsInstance(result["technical"]["atr14"],float)
        self.assertIsInstance(result["rsi14"],float)
        self.assertEqual(result["historical_source_audit"],"PENDING")
        self.assertEqual(result["trading_orders_placed"],0)

    def test_data_is_stale_not_falsely_presented_as_entry(self):
        dates=fake_prices()
        def fake(req,timeout):
            return FakeResponse(json.dumps({"bars":dates,
                                          "next_page_token":None}).encode())
        now=datetime(2026,12,21,18,tzinfo=ZoneInfo("America/New_York"))
        result=assess_symbol("TEST",credentials=("paper","secret"),now=now,
                             verified_events=[],feed="sip",fetch=fake)
        self.assertEqual(result["alert"],"DATA_BLOCKED")
        self.assertFalse("technical" in result)

    def test_unadjusted_empty_data_does_not_claim_buy(self):
        def fake(req,timeout):
            return FakeResponse(json.dumps({"bars":[],
                                          "next_page_token":None}).encode())
        now=datetime(2026,10,16,18,tzinfo=ZoneInfo("America/New_York"))
        result=assess_symbol("TEST",credentials=("paper","secret"),now=now,
                             feed="sip",fetch=fake)
        self.assertEqual(result["alert"],"DATA_BLOCKED")

    def test_flat_prices_rsi_is_neutral(self):
        prices=[{"close":10.0} for _ in range(50)]
        self.assertEqual(rsi14(prices),50.0)


if __name__=="__main__":
    unittest.main()
