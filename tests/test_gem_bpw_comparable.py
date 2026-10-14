"""The BPW-style coverage comparison is factual and not a synthetic score."""
import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from gem_bpw_comparable import CAPABILITIES, POLICY, build_comparable


AS_OF = date(2026, 10, 13)


class GemBPWComparableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def row(self, ticker="TEST", eligible=True):
        return {
            "Ticker": ticker, "Drug": "Example",
            "Exact event": ticker+"|DRUG_20270101",
            "Two-benchmark eligible": eligible,
            "Two-benchmark rank": 1 if eligible else None,
            "Two-benchmark priority /100": 75 if eligible else None,
            "Benchmark 1 — Phase 3 released": "PASS — VERIFIED RESULTS RELEASE",
            "Benchmark 2 — Financing #2 closed": (
                "PASS — TWO POST-READOUT CLOSES" if eligible
                else "PENDING — SECOND CLOSE UNVERIFIED"
            ),
            "PDUFA verification": "VERIFIED — SOURCE LINKED",
            "Cash runway (months)": 8.0,
            "Cash runway gate": "HOLD — UNDER 12 MONTHS",
            "GEM 3 dilution status": "ALERT — NEW OR UNRESOLVED DILUTION",
            "Market activity /10": 8,
            "Rating status": "RATED",
            "Hedge-fund signal": "SOURCE-VERIFIED QUARTERLY 13F HOLDINGS",
            "Hedge-fund managers holding": 1,
            "Hedge-fund managers adding": 1,
            "Cash runway trend": "DECLINING",
            "Phase 3 quality /30": 22,
            "Two-benchmark risk flags": "Under 12 months",
            "PDUFA date": "2027-01-01",
        }

    def test_source_coverage_not_equated_to_bpw_prediction(self):
        report = build_comparable(
            self.root, [self.row(), self.row("OTHER", False)],
            as_of=AS_OF, hedge_report={
                "manager_count": 4, "managers_complete": 3,
                "collector_status": "PARTIAL",
            },
        )
        self.assertEqual(report["gem_observed_program_rows"], 2)
        self.assertEqual(report["gem_two_benchmark_eligible"], 1)
        self.assertFalse(report["same_input_score_comparison_performed"])
        self.assertFalse(report["similarity_percentage_supported"])
        self.assertFalse(report["strategy_returns_validated"])
        self.assertEqual(report["hedge_fund_manager_roster"], 4)
        self.assertEqual(report["hedge_fund_managers_complete"], 3)
        fields = {x["key"]: x for x in report["capability_matrix"]}
        self.assertEqual(fields["clinical"]["observed_gem_rows"], 2)
        self.assertEqual(fields["financing"]["observed_gem_rows"], 1)
        self.assertEqual(fields["runway"]["observed_gem_rows"], 2)
        self.assertEqual(fields["hedge"]["observed_gem_rows"], 2)
        self.assertEqual(fields["insider"]["observed_gem_rows"], 0)
        self.assertEqual(fields["poa"]["observed_gem_rows"], 0)
        self.assertIsNone(report["ranked_two_benchmark_candidates"][0]["BPW PoA score"])
        self.assertIn("EXACTLY TWO ENTRY BENCHMARKS", POLICY)

    def test_market_cap_only_recent_verified_source(self):
        with (self.root / "phase_pipeline_market_caps.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "ticker", "market_cap", "market_cap_source",
                "market_cap_checked_at", "market_cap_status",
            ])
            writer.writeheader()
            writer.writerows([
                {"ticker": "TEST", "market_cap": "130000000",
                 "market_cap_source": "https://api.nasdaq.com/test",
                 "market_cap_checked_at": "2026-10-11T09:00:00+00:00",
                 "market_cap_status": "VERIFIED"},
                {"ticker": "OTHER", "market_cap": "25000000",
                 "market_cap_source": "https://api.nasdaq.com/test",
                 "market_cap_checked_at": "2026-05-10",
                 "market_cap_status": "VERIFIED"},
            ])
        report = build_comparable(
            self.root, [self.row(), self.row("OTHER", False)], as_of=AS_OF
        )
        fields = {x["key"]: x for x in report["capability_matrix"]}
        self.assertEqual(fields["market_cap"]["observed_gem_rows"], 1)
        self.assertEqual(report["ranked_two_benchmark_candidates"][0][
            "Market capitalization USD"], 130000000.0)

    def test_empty_historical_files_never_report_returns_validated(self):
        (self.root/"post_phase3_historical_trade_events.csv").write_text(
            "event_key,ticker,first_financing_close_date\n", encoding="utf-8")
        (self.root/"post_phase3_historical_adjusted_ohlcv.csv").write_text(
            "ticker,session,close\n", encoding="utf-8")
        report = build_comparable(self.root, [self.row()], as_of=AS_OF)
        self.assertEqual(report["historical_linked_event_rows"], 0)
        self.assertEqual(report["historical_price_bar_rows"], 0)
        self.assertFalse(report["strategy_returns_validated"])

    def test_no_rows_does_not_imply_complete_feature_parity(self):
        report = build_comparable(self.root, [], as_of=AS_OF)
        self.assertEqual(report["gem_two_benchmark_eligible"], 0)
        self.assertEqual(report["ranked_two_benchmark_candidates"], [])
        self.assertTrue(all(x["data_coverage_pct"] is None for x
                            in report["capability_matrix"]))


if __name__ == "__main__":
    unittest.main()
