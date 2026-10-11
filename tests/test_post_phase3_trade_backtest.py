"""Stage 3 point-in-time equity backtest regression tests.

Synthetic fixtures prove execution timing and audit behavior. They are NOT
real biotech returns and are never included in production output.
"""
import unittest
from datetime import date, timedelta

from post_phase3_trade_backtest import (
    ENTRY_METHODS, EXIT_DAYS, bars_by_ticker, run_backtest, validate_event,
)

TODAY = date(2026, 10, 11)


def historic_event():
    return {
        "event_key":"TEST|DRUG_DISEASE_20260630", "ticker":"TEST",
        "nct_id":"NCT01234567", "issuer_cik":"123456",
        "phase3_readout_date":"2026-01-05",
        "phase3_public_date":"2026-01-07",
        "phase3_result":"PRIMARY_MET_VERIFIED",
        "clinical_benefit":"MEANINGFUL_VERIFIED",
        "safety_status":"NO_MAJOR_UNRESOLVED_VERIFIED",
        "phase3_source_url":"https://investors.example/phase3",
        "first_financing_close_date":"2026-01-16",
        "first_financing_public_date":"2026-01-20",
        "first_financing_source_url":"https://www.sec.gov/Archives/edgar/data/123456/filing1.htm",
        "second_financing_close_date":"2026-02-20",
        "second_financing_public_date":"2026-02-24",
        "second_financing_source_url":"https://www.sec.gov/Archives/edgar/data/123456/filing2.htm",
        "second_financing_verdict":"TWO_DISTINCT_POST_PHASE3_CLOSES_VERIFIED",
        "pdufa_date":"2026-06-30", "pdufa_public_date":"2026-01-09",
        "pdufa_source_url":"https://investors.example/fda-pdufa",
        "pdufa_verdict":"VERIFIED",
        "pdufa_change_status":"NONE_DOCUMENTED",
        "early_fda_action_date":"",
    }


def price_bars():
    bars = []
    d = date(2025, 11, 3)
    while d <= date(2026, 6, 30):
        if d.weekday() < 5:
            close = 15.0 + .005*len(bars)
            bars.append({
                "ticker":"TEST", "session":d.isoformat(),
                "open":str(round(close-.02,4)), "high":str(round(close+.11,4)),
                "low":str(round(close-.15,4)), "close":str(round(close,4)),
                "volume":"100000",
                "source_url":"https://prices.example/daily/TEST",
                "adjustment_status":"SPLIT_ADJUSTED_VERIFIED",
            })
        d += timedelta(days=1)
    return bars


class TradeBacktest(unittest.TestCase):
    def setUp(self):
        self.event = historic_event()
        self.bars = price_bars()

    def run_one(self, **kwargs):
        return run_backtest([self.event], self.bars, as_of=TODAY, **kwargs)

    def test_valid_case_all_four_entries_three_exits(self):
        trades, summary, audit = self.run_one()
        self.assertEqual(len(trades), len(ENTRY_METHODS)*len(EXIT_DAYS))
        self.assertEqual(len(summary), 12)
        self.assertEqual(audit["status"], "EXPLORATORY_ONLY_NOT_CALIBRATED")
        self.assertEqual(audit["completed_scenarios"], 12)
        self.assertTrue(all(t["status"]=="COMPLETED" for t in trades))
        self.assertTrue(all(s["status"]=="EXPLORATORY_FEWER_THAN_30_TRADES"
                            for s in summary))
        self.assertTrue(all(s["events_attempted"]==1 for s in summary))

    def test_next_session_open_after_signal(self):
        trades, _, _ = self.run_one()
        for trade in trades:
            self.assertGreater(date.fromisoformat(trade["entry_date"]),
                               date.fromisoformat(trade["entry_signal_date"]))
        second = next(x for x in trades if x["entry_method"]=="SECOND_FINANCING"
                      and x["exit_days_before_pdufa"]==7)
        self.assertGreater(date.fromisoformat(second["entry_date"]),
                           date.fromisoformat(self.event["second_financing_public_date"]))

    def test_post_second_base_requires_multiple_observed_sessions(self):
        trades, _, _ = self.run_one()
        second = next(x for x in trades if x["entry_method"]=="SECOND_FINANCING"
                      and x["exit_days_before_pdufa"]==7)
        based = next(x for x in trades if x["entry_method"]=="POST_SECOND_FINANCING_BASE"
                      and x["exit_days_before_pdufa"]==7)
        self.assertGreater(date.fromisoformat(based["entry_date"]),
                           date.fromisoformat(second["entry_date"]))
        after = [d for d in self.bars if
                 date.fromisoformat(self.event["second_financing_public_date"])
                 < date.fromisoformat(d["session"])
                 <= date.fromisoformat(based["entry_signal_date"])]
        self.assertGreaterEqual(len(after), 10)

    def test_exit_cutoffs_are_on_or_before_target(self):
        trades, _, _ = self.run_one()
        for row in trades:
            self.assertLessEqual(date.fromisoformat(row["exit_date"]),
                                 date.fromisoformat(row["exit_target_date"]))
            self.assertGreater(date.fromisoformat(row["exit_date"]),
                               date.fromisoformat(row["entry_date"]))

    def test_slippage_penalizes_return(self):
        base, _, _ = self.run_one(slippage_bps=0)
        pessimistic, _, _ = self.run_one(slippage_bps=50)
        for x,y in zip(base,pessimistic):
            self.assertGreater(x["net_return_pct"], y["net_return_pct"])

    def test_earlier_fda_action_censors_later_windows_not_profitable(self):
        self.event["early_fda_action_date"]="2026-06-10"
        trades, _, audit = self.run_one()
        self.assertEqual(audit["early_action_censored_scenarios"], 8)
        self.assertEqual(audit["completed_scenarios"], 4)
        for row in trades:
            if row["exit_days_before_pdufa"] in (14,7):
                self.assertEqual(row["status"], "CENSORED_EARLY_FDA_ACTION")
                self.assertEqual(row["net_return_pct"], "")
            else:
                self.assertEqual(row["status"], "COMPLETED")

    def test_stale_postdated_financing_publication_blocks_entry(self):
        self.event["second_financing_public_date"]="2026-07-01"
        _, _, audit = self.run_one()
        self.assertEqual(audit["completed_scenarios"], 0)

    def test_wrong_issuer_cik_sec_financing_fails(self):
        self.event["second_financing_source_url"] = (
            "https://www.sec.gov/Archives/edgar/data/999999/otherissuer.htm")
        trades, _, audit = self.run_one()
        self.assertEqual(audit["completed_scenarios"], 0)
        self.assertTrue(all(r["reason"]=="MISSING_PRIMARY_SOURCE_LINK" for r in trades))

    def test_ticker_identity_mismatch_fails(self):
        self.event["ticker"]="ELSE"
        reason,_=validate_event(self.event)
        self.assertEqual(reason,"UNVERIFIED_EXACT_EVENT_IDENTITY")

    def test_registry_nct_missing_fails(self):
        self.event["nct_id"]=""
        trades,_,audit=self.run_one()
        self.assertEqual(audit["completed_scenarios"],0)
        self.assertTrue(all(x["status"]=="BLOCKED" for x in trades))

    def test_second_financing_not_explicitly_verified_fails(self):
        self.event["second_financing_verdict"]="OFFERING_ANNOUNCED"
        trades,_,audit=self.run_one()
        self.assertEqual(audit["completed_scenarios"],0)
        self.assertTrue(all("REGULATORY_REVIEW" in x["reason"] for x in trades))

    def test_unknown_clinical_benefit_not_fake_pass(self):
        self.event["clinical_benefit"]="NOT_VERIFIED"
        _,_,audit=self.run_one()
        self.assertEqual(audit["completed_scenarios"],0)

    def test_duplicate_event_keys_block_all(self):
        trades,_,audit=run_backtest(
            [self.event,self.event], self.bars, as_of=TODAY)
        self.assertEqual(audit["completed_scenarios"],0)
        self.assertTrue(all(x["reason"]=="DUPLICATE_EXACT_EVENT_KEY" for x in trades))

    def test_adjustment_not_verified_rejects_entire_quote_history(self):
        self.bars[45]["adjustment_status"]="UNKNOWN"
        _,_,audit=self.run_one()
        self.assertEqual(audit["completed_scenarios"],0)
        self.assertIn("TEST",audit["price_tickers_invalid"])

    def test_duplicate_price_session_rejects_prices(self):
        self.bars.append(dict(self.bars[30]))
        _,_,audit=self.run_one()
        self.assertEqual(audit["completed_scenarios"],0)
        self.assertIn("TEST",audit["price_tickers_invalid"])

    def test_no_prices_or_events_never_invents_wins(self):
        trades,summary,audit=run_backtest([],[],as_of=TODAY)
        self.assertEqual(trades,[])
        self.assertEqual(audit["status"],"NOT_READY_NO_EVENT_AND_PRICE_HISTORY")
        self.assertTrue(all(s["status"]=="NO_VALID_TRADES" for s in summary))
        self.assertTrue(all(s["win_rate_pct"]=="" for s in summary))

    def test_missing_future_exit_window_never_marked_complete(self):
        trades,_,audit=run_backtest([self.event],self.bars,
                                   as_of=date(2026,5,1))
        self.assertEqual(audit["completed_scenarios"],0)
        self.assertTrue(all(x["reason"]=="EXIT_TARGET_NOT_YET_HISTORICAL" for x in trades))

    def test_future_price_cannot_be_accessed_at_research_asof(self):
        _,_,audit=self.run_one()
        self.assertEqual(audit["future_price_rows_excluded"],0)
        _,_,audit=run_backtest([self.event], self.bars,
                               as_of=date(2026,6,1))
        self.assertGreater(audit["future_price_rows_excluded"],0)
        self.assertTrue(any("EXIT_TARGET_NOT_YET_HISTORICAL" in k
                            for k in audit["blocker_reasons"]))

    def test_historical_price_gap_blocks_scenario(self):
        self.bars=[b for b in self.bars if not "2026-04" in b["session"]]
        _,_,audit=self.run_one()
        self.assertEqual(audit["completed_scenarios"],0)
        self.assertTrue(any("EXIT_SESSION_MISSING" in k
                            for k in audit["blocker_reasons"]))

    def test_not_enough_prior_liquidity_bars(self):
        self.bars=[b for b in self.bars if b["session"]>="2026-01-01"]
        trades,_,_=self.run_one()
        readout=[x for x in trades if x["entry_method"]=="READOUT_BENCHMARK"]
        self.assertTrue(all(x["reason"]=="PRIOR20_DOLLAR_LIQUIDITY_NOT_VERIFIED" for x in readout))

    def test_zero_and_negative_price_invalid(self):
        self.bars[7]["open"]="0"
        _,_,audit=self.run_one()
        self.assertEqual(audit["completed_scenarios"],0)

    def test_insufficient_source_history_never_assumes_success(self):
        self.event["pdufa_source_url"]=""
        _,_,audit=self.run_one()
        self.assertEqual(audit["completed_scenarios"],0)

    def test_invalid_args_rejected(self):
        with self.assertRaises(ValueError):
            self.run_one(slippage_bps=-1)
        with self.assertRaises(ValueError):
            self.run_one(exit_days=(0,7))
        with self.assertRaises(ValueError):
            self.run_one(min_daily_dollars=float("nan"))
