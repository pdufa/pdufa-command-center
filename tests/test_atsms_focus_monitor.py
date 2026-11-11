"""Deterministic ATSMS unit tests; never call a broker or live market source."""
import importlib.util
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("atsms_focus_monitor",ROOT/"scripts/atsms_focus_monitor.py")
atsms=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(atsms)
NOW=datetime(2026,11,11,18,30,tzinfo=timezone.utc)

def sample_bars():
    base=[10,10.12,9.94,10.12,9.96,10.04,9.95,10.13,10,10.08]
    prices=[9.1+.011*i+(.06 if i%2 else 0) for i in range(80)] + base + [10.35]
    start=date(2026,8,12)
    return [{"date":(start+timedelta(days=i)).isoformat(),"open":p,
      "high":p+.1,"low":p-.1,"close":p,"volume":600000 if i==90 else 250000}
      for i,p in enumerate(prices)]

def rosterfile(path,records):
    path.write_text(json.dumps({"schemaVersion":1,"asOf":"2026-11-10",
        "records":records}),encoding="utf-8")

class ATSMSTests(unittest.TestCase):
    def test_complete_eight_technical_checks_never_authorize_trade(self):
        bars=sample_bars()
        result=atsms.calculate_metrics(bars,bars[-1]["date"])
        self.assertIsNotNone(result)
        self.assertEqual(result["technical"],"BUY_SETUP")
        self.assertEqual(result["passed"],8)
        self.assertEqual([c["code"] for c in result["checks"]],
            ["BASE","LOWS","BREAKOUT","TREND","RVOL","RSI","LIQUIDITY","ATR"])
        bad=atsms.calculate_metrics(bars,bars[-2]["date"])
        self.assertIsNone(bad)
        self.assertIsNone(atsms.calculate_metrics(bars[-40:],bars[-1]["date"]))
    def test_wait_if_volume_signal_fails(self):
        b=sample_bars();b[-1]["volume"]=20000
        met=atsms.calculate_metrics(b,b[-1]["date"])
        self.assertEqual(met["technical"],"WAIT")
        self.assertFalse(next(c for c in met["checks"] if c["code"]=="RVOL")["pass"])
    def test_focus_roster_exact_nct_dedupe_and_add_remove(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"focus.json"
            entries=[
                {"ticker":"SVRA","nct":"NCT04544293","recordedPdufaDate":"2026-11-22"},
                {"ticker":"CAPR","nct":"NCT05126758","recordedPdufaDate":None},
            ]
            rosterfile(f,entries)
            rows,asof=atsms.snapshot_roster(f,NOW)
            self.assertEqual(len(rows),2)
            self.assertEqual(asof,"2026-11-10")
            self.assertEqual(rows[0]["pdufa"],"2026-11-22")
            rosterfile(f,entries+[dict(entries[0])])
            with self.assertRaisesRegex(ValueError,"duplicated"):
                atsms.snapshot_roster(f,NOW)
            rosterfile(f,[entries[1]])
            self.assertEqual(len(atsms.snapshot_roster(f,NOW)[0]),1)
            rosterfile(f,[{**entries[1],"ticker":"SVRA/OTHER"}])
            with self.assertRaisesRegex(ValueError,"invalid"):
                atsms.snapshot_roster(f,NOW)
    def test_pdufa_unknown_blackout_and_passed_fail_closed(self):
        c={"ticker":"SVRA","nct":"NCT04544293"}
        self.assertEqual(atsms.pdufa_gate({**c,"pdufa":"2026-11-22"},NOW)["status"],"BLACKOUT")
        self.assertEqual(atsms.pdufa_gate({**c,"pdufa":"2027-02-22"},NOW)["status"],"CLEAR")
        self.assertEqual(atsms.pdufa_gate({**c,"pdufa":None},NOW)["status"],"UNVERIFIED")
        self.assertEqual(atsms.pdufa_gate({**c,"pdufa":"2026-11-10"},NOW)["status"],"PAST")
        b=sample_bars();met=atsms.calculate_metrics(b,b[-1]["date"])
        market={"metrics":met,"minute":{"close":20.0,"volume":10000,"asOf":NOW.isoformat()}}
        blocked=atsms.study_record({**c,"pdufa":"2026-11-22"},market,NOW)
        self.assertEqual(blocked["entry"],"BLOCKED_PDUFA")
        self.assertEqual(blocked["technical"],"BUY_SETUP")
        self.assertFalse(blocked["executionEnabled"])
        allowed=atsms.study_record({**c,"pdufa":"2027-02-22"},market,NOW)
        self.assertEqual(allowed["entry"],"TECHNICAL_WATCH_ONLY")
        self.assertFalse(allowed["executionEnabled"])
        missing=atsms.study_record({**c,"pdufa":None},market,NOW)
        self.assertEqual(missing["entry"],"BLOCKED_UNVERIFIED_OR_PAST")
    def test_intraday_stale_bar_not_represented_as_live(self):
        b=sample_bars()
        request1={"bars":{"SVRA":[{"t":x["date"]+"T00:00:00Z","o":x["open"],
          "h":x["high"],"l":x["low"],"c":x["close"],"v":x["volume"]} for x in b]}}
        old={"bars":{"SVRA":{"t":"2026-11-10T20:59:00Z","c":12,"v":300}}}
        ctx={"localDay":"2026-11-11","expectedCompletedDay":b[-1]["date"],"session":"REGULAR"}
        received=atsms.collect_market(["SVRA"],ctx,NOW,("not-a-live-key","not-a-live-secret"),
            fetch=lambda path,params: request1 if path=="/v2/stocks/bars" else old)
        self.assertIsNone(received["SVRA"]["minute"])
        self.assertEqual(len(received["SVRA"]["bars"]),len(b))
    def test_signal_changes_only_notify_on_transition_from_prior_stored_evidence(self):
        sample={"nct":"NCT04544293","ticker":"SVRA","entry":"TECHNICAL_WATCH_ONLY","exit":"RISK_WARNING"}
        first,changes=atsms.transitions([sample],None)
        self.assertEqual(changes,[])
        repeated,changes=atsms.transitions([sample],{"signals":first})
        self.assertEqual(changes,[])
        waiting={"nct":"NCT04544293","ticker":"SVRA","entry":"WAIT","exit":"NO_TRIGGER_OBSERVED"}
        waiting_state,_=atsms.transitions([waiting],{"signals":first})
        state,changes=atsms.transitions([sample],{"signals":waiting_state})
        self.assertEqual(len(changes),2)
        self.assertEqual({x["event"] for x in changes},{"TECHNICAL_WATCH_ONLY","RISK_WARNING"})
    def test_no_alpaca_credentials_report_unconfigured_but_not_successful_signals(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"focus.json"
            rosterfile(f,[{"ticker":"SVRA","nct":"NCT04544293","recordedPdufaDate":"2026-11-22"}])
            fake={"session":"REGULAR","localDay":"2026-11-11","expectedCompletedDay":"2026-11-10"}
            with patch.dict(os.environ,{"ALPACA_API_KEY":"","ALPACA_SECRET_KEY":"",
                "APCA_API_KEY_ID":"","APCA_API_SECRET_KEY":""}):
                report=atsms.run(NOW,roster=f,session_override=fake)
            self.assertEqual(report["status"],"ALPACA_CREDENTIALS_NOT_CONFIGURED")
            self.assertEqual(report["focusTrials"],1)
            self.assertEqual(report["trials"][0]["technical"],"UNAVAILABLE")
            self.assertFalse(report["brokerOrdersEnabled"])
    def test_exchange_calendar_holiday_and_regular_vs_extended(self):
        class Stamp:
            def to_pydatetime(self):
                return datetime(2026,11,11,21,0,tzinfo=timezone.utc)
        class Cal:
            def __init__(self,allowed): self.allowed=allowed
            def is_session(self,day): return self.allowed
            def session_close(self,day): return Stamp()
            def previous_session(self,day): return date(2026,11,10)
            def date_to_session(self,day): return date(2026,11,11)
        self.assertIsNone(atsms.market_context(datetime(2026,11,11,8,50,tzinfo=timezone.utc),Cal(True)))
        self.assertIsNone(atsms.market_context(NOW,Cal(False)))
        self.assertEqual(atsms.market_context(datetime(2026,11,11,10,0,tzinfo=timezone.utc),Cal(True))["session"],"PREMARKET")
        self.assertEqual(atsms.market_context(NOW,Cal(True))["session"],"REGULAR")
        self.assertEqual(atsms.market_context(datetime(2026,11,11,22,30,tzinfo=timezone.utc),Cal(True))["session"],"AFTERHOURS")

if __name__=="__main__":
    unittest.main()
