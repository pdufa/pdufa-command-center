"""Synthetic fixture tests: not real biotechnology investment performance."""
import unittest
from datetime import date, timedelta

from gem_historical_signal_backtest import (
    atr_at, first_signal, replay_trade, run, score_at,
)
from post_phase3_trade_backtest import bars_by_ticker, validate_event


def event():
    return {
        "event_key":"TEST|EXAMPLE_20250930", "ticker":"TEST",
        "nct_id":"NCT01234567", "issuer_cik":"123456",
        "phase3_readout_date":"2025-01-10",
        "phase3_public_date":"2025-01-11",
        "phase3_result":"PRIMARY_MET_VERIFIED",
        "clinical_benefit":"MEANINGFUL_VERIFIED",
        "safety_status":"NO_MAJOR_UNRESOLVED_VERIFIED",
        "phase3_source_url":"https://investors.example/phase3",
        "first_financing_close_date":"2025-02-01",
        "first_financing_public_date":"2025-02-03",
        "first_financing_source_url":
            "https://www.sec.gov/Archives/edgar/data/123456/first.htm",
        "second_financing_close_date":"2025-04-14",
        "second_financing_public_date":"2025-04-15",
        "second_financing_source_url":
            "https://www.sec.gov/Archives/edgar/data/123456/second.htm",
        "second_financing_verdict":
            "TWO_DISTINCT_POST_PHASE3_CLOSES_VERIFIED",
        "pdufa_date":"2025-09-30",
        "pdufa_public_date":"2025-01-20",
        "pdufa_source_url":"https://investors.example/pdufa",
        "pdufa_verdict":"VERIFIED",
        "pdufa_change_status":"NONE_DOCUMENTED",
        "early_fda_action_date":"",
    }


def bars():
    result=[]
    current=date(2025,1,2)
    while current <= date(2025,10,1):
        if current.weekday() < 5:
            i=len(result)
            # Exactly one qualifying late-April breakout after the financing.
            # Price then stabilizes without adverse SMA20 exits.
            price=10.0 if i<85 else 10.31
            vol=210000 if i==85 else 100000
            high=price+.08
            low=price-.08
            result.append({
                "ticker":"TEST","session":current.isoformat(),
                "open":str(round(price,4)),"high":str(round(high,4)),
                "low":str(round(low,4)),"close":str(round(price,4)),
                "volume":str(vol),"source_url":"https://data.example/TEST",
                "adjustment_status":"SPLIT_ADJUSTED_VERIFIED",
            })
        current+=timedelta(days=1)
    return result


class SignalResearchTests(unittest.TestCase):
    def test_event_is_valid(self):
        reason, dates=validate_event(event())
        self.assertEqual(reason,"")
        self.assertEqual(dates["pdufa_date"],date(2025,9,30))

    def test_zero_real_inputs_never_claims_success(self):
        trades, summaries, audit=run([],[],year=2025)
        self.assertEqual(trades,[])
        self.assertTrue(summaries)
        self.assertEqual(audit["completed_trades"],0)
        self.assertEqual(audit["status"],"NO_VERIFIED_HISTORICAL_BACKTEST")
        self.assertTrue(all(x["win_rate_pct"]=="" for x in summaries))

    def test_source_verified_signal_is_next_open_only(self):
        history,_=bars_by_ticker(bars())
        _,dates=validate_event(event())
        s=first_signal(history["TEST"],dates,threshold=60,
                       volume_threshold=1.5,base_atr_width=3,
                       min_dollars=250000)
        self.assertIsNotNone(s)
        i,_,stop=s
        self.assertGreater(history["TEST"][i]["session"],
                           dates["second_financing_public_date"])
        self.assertGreater(history["TEST"][i+1]["session"],
                           history["TEST"][i]["session"])
        self.assertGreater(stop,0)

    def test_empty_price_history_blocks_not_wins(self):
        trades,_,audit=run([event()],[],score_thresholds=(60,),
                           volume_thresholds=(1.5,),base_widths=(3,),
                           exit_days=(3,))
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0]["status"],"BLOCKED")
        self.assertEqual(trades[0]["reason"],"MISSING_SPLIT_ADJUSTED_OHLCV")
        self.assertEqual(audit["completed_trades"],0)

    def test_realistic_replay_returns_or_explicit_nontrade(self):
        trades, summaries, audit=run(
            [event()],bars(),score_thresholds=(60,),
            volume_thresholds=(1.5,),base_widths=(3,),exit_days=(3,))
        self.assertEqual(len(trades),1)
        self.assertIn(trades[0]["status"],("COMPLETED","NO_SIGNAL"))
        if trades[0]["status"]=="COMPLETED":
            self.assertGreater(trades[0]["entry_date"],
                               trades[0]["entry_signal_date"])
            self.assertLessEqual(trades[0]["exit_date"],"2025-09-27")
        self.assertEqual(audit["candidate_event_rows"],1)
        self.assertEqual(summaries[0]["status"],"EXPLORATORY_UNDER_30")

    def test_pre_funding_spike_never_qualifies(self):
        source=bars()
        for k,row in enumerate(source):
            if k==45:
                row.update(close="10.31",high="10.39",open="10.31",
                           low="10.23",volume="220000")
        history,_=bars_by_ticker(source)
        _,dates=validate_event(event())
        signal=first_signal(history["TEST"],dates,threshold=60,
                            volume_threshold=1.5,base_atr_width=3,
                            min_dollars=250000)
        if signal:
            self.assertGreater(history["TEST"][signal[0]]["session"],
                               dates["second_financing_public_date"])

    def test_early_fda_action_not_reported_as_profitable_exit(self):
        x=event()
        x["early_fda_action_date"]="2025-06-01"
        trades,_,_=run([x],bars(),score_thresholds=(60,),
                       volume_thresholds=(1.5,),base_widths=(3,),
                       exit_days=(3,))
        self.assertNotEqual(trades[0]["exit_reason"],"MANDATORY_PDUFA_CUTOFF"
                            if trades[0]["status"]=="CENSORED" else
                            "__NEVER__")
        if trades[0]["status"]=="CENSORED":
            self.assertEqual(trades[0]["net_return_pct"],"")

    def test_invalid_adjustment_blocks_whole_ticker(self):
        b=bars()
        b[40]["adjustment_status"]="RAW"
        trades,_,_=run([event()],b,score_thresholds=(60,),
                       volume_thresholds=(1.5,),base_widths=(3,),
                       exit_days=(3,))
        self.assertEqual(trades[0]["reason"],"INVALID_PRICE_HISTORY")

    def test_missing_cutoff_price_cannot_be_filled_from_months_earlier(self):
        old=[b for b in bars() if b["session"]<"2025-07-01"]
        trades,_,_=run([event()],old,score_thresholds=(60,),
                       volume_thresholds=(1.5,),base_widths=(3,),
                       exit_days=(3,))
        self.assertEqual(trades[0]["reason"],"MISSING_CUTOFF_PRICE_DATA")

    def test_long_gap_in_trading_history_blocks_trade(self):
        broken=[b for b in bars()
                if not "2025-06-01"<=b["session"]<="2025-06-30"]
        trades,_,_=run([event()],broken,score_thresholds=(60,),
                       volume_thresholds=(1.5,),base_widths=(3,),
                       exit_days=(3,))
        self.assertEqual(trades[0]["reason"],"UNAUDITED_PRICE_SESSION_GAP")

    def test_market_cap_filter_off_for_2026_as_requested(self):
        trades, summary, audit=run([],[],year=2026,
                                    market_caps=None)
        self.assertFalse(audit["market_cap_filter_active"])
        self.assertIsNone(audit["market_cap_min_usd"])
        self.assertEqual(audit["completed_trades"],0)
        self.assertEqual(len(summary),54)

    def test_market_cap_filter_remains_opt_in_for_future(self):
        unfiltered,_,audit=run(
            [event()],bars(),year=2025,market_caps=None,
            score_thresholds=(60,),volume_thresholds=(1.5,),
            base_widths=(3,),exit_days=(3,))
        self.assertNotEqual(unfiltered[0]["reason"],
                            "MISSING_VERIFIED_HISTORICAL_MARKET_CAP")
        self.assertFalse(audit["market_cap_filter_active"])
        filtered,_,audit=run(
            [event()],bars(),year=2025,market_caps=[],
            score_thresholds=(60,),volume_thresholds=(1.5,),
            base_widths=(3,),exit_days=(3,))
        self.assertEqual(filtered[0]["status"],"BLOCKED")
        self.assertEqual(filtered[0]["reason"],
                         "MISSING_VERIFIED_HISTORICAL_MARKET_CAP")
        self.assertTrue(audit["market_cap_filter_active"])

    def test_completed_trade_has_dollar_and_percent_profit_loss(self):
        history,_=bars_by_ticker(bars())
        result=replay_trade(history["TEST"],(84,80,9.85),
                            date(2025,9,30),None,3,10,
                            investment_usd=10000)
        self.assertEqual(result["status"],"COMPLETED")
        self.assertEqual(result["hypothetical_investment_usd"],10000)
        self.assertLessEqual(result["hypothetical_cost_usd"],10000)
        self.assertEqual(result["hypothetical_shares"],
                         int(10000/result["entry_price"]))
        self.assertAlmostEqual(
            result["hypothetical_profit_loss_usd"],
            result["hypothetical_shares"]*
            (result["exit_price"]-result["entry_price"]),delta=.15)
        self.assertAlmostEqual(
            result["net_return_pct"],
            100*(result["exit_price"]/result["entry_price"]-1),
            delta=.01)
        self.assertAlmostEqual(
            result["return_on_allocation_pct"],
            100*result["hypothetical_profit_loss_usd"]/10000,
            delta=.01)
        self.assertIn("gross_return_pct",result)
        self.assertIn("net_profit_per_share_usd",result)

    def test_stop_or_early_fda_censor_never_claims_pnl(self):
        history,_=bars_by_ticker(bars())
        result=replay_trade(history["TEST"],(84,80,9.85),
                            date(2025,9,30),date(2025,6,1),3,10,
                            investment_usd=10000)
        self.assertEqual(result["status"],"CENSORED")
        self.assertNotIn("hypothetical_profit_loss_usd",result)
        self.assertNotIn("net_return_pct",result)

    def test_invalid_investment_rejected(self):
        with self.assertRaisesRegex(ValueError,"Investment"):
            run([],[],investment_usd=0)
        with self.assertRaisesRegex(ValueError,"Investment"):
            run([],[],investment_usd=float("nan"))

    def test_no_future_calendar_events(self):
        x=event()
        x["pdufa_date"]="2027-09-30"
        x["pdufa_public_date"]="2025-01-20"
        trades,_,_=run([x],bars(),year=2027,score_thresholds=(60,),
                       volume_thresholds=(1.5,),base_widths=(3,),
                       exit_days=(3,))
        self.assertEqual(trades[0]["reason"],"FUTURE_PDUFA_NOT_COMPLETED")


if __name__=="__main__":
    unittest.main()
