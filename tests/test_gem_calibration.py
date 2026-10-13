"""Synthetic regression fixtures only: NEVER stock performance evidence."""
import unittest
from datetime import date, timedelta

from gem_calibration import (
    STAGES, candidate_weights, calibrate, validate_snapshot,
)
from gem_scans import WEIGHTS


AS_OF = date(2026, 10, 13)


def record(*, stage="Post-Financing", signal="2026-02-17"):
    return {
        "event_key": "TEST|DRUG_20260630", "ticker": "TEST",
        "nct_id": "NCT01234567", "issuer_cik": "12345",
        "stage": stage, "signal_date": signal,
        "phase3_public_date": "2026-01-05",
        "phase3_source_url": "https://issuer.example/clinical",
        "second_financing_public_date": "2026-02-03",
        "second_financing_source_url":
            "https://www.sec.gov/Archives/edgar/data/12345/filing2.htm",
        "pdufa_date": "2026-06-30", "pdufa_public_date": "2026-01-20",
        "pdufa_source_url": "https://issuer.example/pdufa",
        "market_source_url": "https://prices.example/daily",
        "early_fda_action_date": "",
        "phase3_verdict": "PRIMARY_MET_BENEFIT_SAFETY_VERIFIED",
        "financing_verdict": "TWO_DISTINCT_POST_PHASE3_CLOSES_VERIFIED",
        "no_unresolved_dilution": "YES",
        "price_base_verdict": "VERIFIED",
        "normalized_volume_verdict": "VERIFIED",
        "market_quote_verdict": "SOURCED_RECENT",
        "pdufa_verdict": "VERIFIED", "conflict_flag": "NONE",
        "Clinical evidence /30": "30", "Financing evidence /20": "20",
        "Trading setup /20": "20", "PDUFA evidence /15": "15",
        "Market activity /10": "10",
    }


def market_bars():
    bars = []
    t = date(2025, 12, 1)
    while t <= date(2026, 6, 30):
        if t.weekday() < 5:
            price = 10 + .007 * len(bars)
            bars.append({
                "ticker": "TEST", "session": t.isoformat(),
                "open": str(price), "high": str(price+1),
                "low": str(price-1), "close": str(price+.1),
                "volume": "100000",
                "source_url": "https://prices.example/daily",
                "adjustment_status": "SPLIT_ADJUSTED_VERIFIED",
            })
        t += timedelta(days=1)
    return bars


class GemCalibrationRegressionTests(unittest.TestCase):
    def test_empty_historical_inputs_cannot_tune(self):
        out = calibrate([], [], as_of=AS_OF)
        self.assertEqual(out["status"], "NO_HISTORICAL_FEATURES_OR_PRICES")
        self.assertEqual(out["valid_completed_trades"], 0)
        self.assertTrue(all(not x["calibrated"] for x in out["stages"].values()))
        self.assertTrue(all(x["selected_hypothesis"] is None
                            for x in out["stages"].values()))

    def test_postfinancing_pdufa_minus_three_exit_not_minus_fourteen(self):
        out = calibrate([record()], market_bars(), as_of=AS_OF)
        self.assertEqual(out["valid_completed_trades"], 1)
        self.assertEqual(out["stages"]["Post-Financing"]["completed_trades"], 1)
        self.assertEqual(out["stages"]["Post-Financing"]["status"],
                         "INSUFFICIENT_SCORE_DISCRIMINATION")
        self.assertEqual(out["status"], "NO_STAGE_PASSES_HOLDOUT_REQUIREMENTS")
        self.assertTrue(all(not row["calibrated"] for row in out["stages"].values()))

    def test_pdufa_beyond_ninety_days_is_allowed_for_financing_to_exit_strategy(self):
        r = record(stage="PDUFA")
        reason, decoded = validate_snapshot(r, AS_OF)
        self.assertEqual(reason, "")
        self.assertGreater((decoded["pdufa"] - decoded["signal"]).days, 90)

    def test_signal_on_exit_day_is_not_new_entry(self):
        r = record(stage="PDUFA", signal="2026-06-27")
        reason, _ = validate_snapshot(r, AS_OF)
        self.assertEqual(reason, "INSIDE_PDUFA_MINUS_3_EXIT_WINDOW")

    def test_same_day_disclosure_is_not_same_day_execution(self):
        r = record()
        r["signal_date"] = r["second_financing_public_date"]
        reason, _ = validate_snapshot(r, AS_OF)
        self.assertEqual(reason, "")
        # Last-known public financing date is a signal; execution is the
        # next actual market-session OPEN, never that source publication day.
        out = calibrate([r], market_bars(), as_of=AS_OF)
        self.assertEqual(out["valid_completed_trades"], 1)

    def test_second_financing_source_and_timing_must_be_attested(self):
        r = record()
        r["second_financing_public_date"] = "2026-03-01"
        reason, _ = validate_snapshot(r, AS_OF)
        self.assertEqual(reason, "FINANCING_PUBLICATION_OR_SEC_IDENTITY_UNVERIFIED")
        r = record()
        r["second_financing_source_url"] = "https://www.sec.gov/Archives/edgar/data/5555/other.htm"
        reason, _ = validate_snapshot(r, AS_OF)
        self.assertEqual(reason, "FINANCING_PUBLICATION_OR_SEC_IDENTITY_UNVERIFIED")

    def test_early_fda_actions_are_censored_not_fabricated_positive(self):
        r = record()
        r["early_fda_action_date"] = "2026-05-01"
        out = calibrate([r], market_bars(), as_of=AS_OF)
        self.assertEqual(out["valid_completed_trades"], 0)
        self.assertEqual(out["excluded_reasons"]["CENSORED_EARLY_FDA_ACTION"], 1)

    def test_source_and_price_history_required(self):
        empty = calibrate([record()], [], as_of=AS_OF)
        self.assertEqual(empty["valid_completed_trades"], 0)
        self.assertIn("NO_VERIFIED_HISTORICAL_BARS", empty["excluded_reasons"])
        bars = market_bars()
        bars[0]["adjustment_status"] = "UNKNOWN"
        out = calibrate([record()], bars, as_of=AS_OF)
        self.assertEqual(out["valid_completed_trades"], 0)
        self.assertIn("TEST", out["invalid_price_tickers"])

    def test_stage_hypotheses_are_valid_but_not_live_production_changes(self):
        for stage in STAGES:
            hypotheses = candidate_weights(stage)
            self.assertEqual(hypotheses["LIVE_V1"], WEIGHTS[stage])
            self.assertTrue(all(sum(weights.values()) == 100
                                for weights in hypotheses.values()))

    def test_calibration_ui_is_wired_into_scans(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        ui = (root / "gem_scans_ui.py").read_text(encoding="utf-8")
        self.assertIn("render_gem_calibration(root)", ui)
        self.assertIn("PDUFA −3", (root/"gem_calibration_ui.py").read_text(encoding="utf-8"))
