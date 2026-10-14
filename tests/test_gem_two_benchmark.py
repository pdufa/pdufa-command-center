"""Two released-results/second-financing benchmarks, then advisory candidate ranking."""
import unittest
from unittest.mock import patch

from gem_two_benchmark import (
    WEIGHTS, assess, assign_ranks, phase3_results_released, second_financing_closed,
)
from gem_scans import build_gem_scans

DATE = "2026-10-13"


def sample(ticker="AAA", runway=18, days=50, financed=True):
    return {
        "Ticker": ticker, "Drug": "Program " + ticker,
        "Exact event": ticker + "|PROGRAM_20261130",
        "NCT ID": "NCT01234567",
        "Entry qualification": "REVIEW — ENTRY BLOCKED",
        "Phase 3 evidence": "VERIFIED SUCCESS — SOURCE LINKED",
        "2nd Financing Completed": (
            "YES — VERIFIED (HISTORICAL)" if financed else "NOT VERIFIED"
        ),
        "Verified 2nd financing close date": "2026-10-05" if financed else "",
        "Clinical evidence /30": 30, "Trading setup /20": 16,
        "Market activity /10": 7, "Financing evidence /20": 0,
        "PDUFA verification": "VERIFIED — SOURCE LINKED",
        "Days to PDUFA": days, "Cash runway (months)": runway,
        "Cash runway trend": "", "Evidence score /100": 70,
        "As of Pacific": DATE,
    }


def event(ticker="AAA", state="VERIFIED_SUCCESS", **changes):
    e = {
        "ticker": ticker, "nct_id": "NCT01234567",
        "phase3_status": state, "phase3_date": "2026-09-01",
        "trial_evidence_url": "https://issuer.example.com/phase3/results",
        "conflict_flag": "NONE", "new_dilution_flag": "NO",
    }
    e.update(changes)
    return e


class TwoBenchmarkPriorityTests(unittest.TestCase):
    def test_weights_total_100_and_only_two_positive_benchmarks(self):
        self.assertEqual(sum(WEIGHTS.values()), 100)
        result = assess(sample(), event(), as_of=DATE)
        self.assertTrue(result["Two-benchmark eligible"])
        self.assertEqual(result["Two-benchmark priority /100"], 82)
        self.assertEqual(result["Two-benchmark rank"], None)
        self.assertIn("QUALIFIED", result["Two-benchmark entry status"])

    def test_release_means_actual_result_not_phase3_start_or_registry_completion(self):
        row = sample()
        for change in (
            {"phase3_status": "RESULTS_REVIEW"},
            {"phase3_status": "PHASE3_COMPLETED"},
            {"trial_evidence_url": ""},
            {"phase3_date": "2026-11-20"},
            {"ticker": "WRONG"},
            {"nct_id": "NCT87654321"},
        ):
            with self.subTest(change=change):
                self.assertFalse(phase3_results_released(
                    row, event(**change), as_of=DATE
                ))
        self.assertTrue(phase3_results_released(row, event(), as_of=DATE))

    def test_unevidenced_second_financing_never_unlocks_rank(self):
        row = sample(financed=False)
        found = assess(row, event(), as_of=DATE)
        self.assertFalse(found["Two-benchmark eligible"])
        self.assertIsNone(found["Two-benchmark priority /100"])
        self.assertIn("PENDING", found["Benchmark 2 — Financing #2 closed"])
        row = sample()
        row["Verified 2nd financing close date"] = ""
        self.assertFalse(second_financing_closed(row, event(), as_of=DATE))
        row["Verified 2nd financing close date"] = "2026-01-01"
        self.assertFalse(second_financing_closed(row, event(), as_of=DATE))

    def test_runway_under_12_or_unknown_does_not_block_two_benchmarks(self):
        for value in (None, 4, 8, 11):
            with self.subTest(months=value):
                r = assess(sample(runway=value), event(), as_of=DATE)
                self.assertTrue(r["Two-benchmark eligible"])
                self.assertIsNotNone(r["Two-benchmark priority /100"])
                self.assertTrue("runway" in r["Two-benchmark risk flags"].lower())

    def test_dilution_and_unverified_market_or_fda_are_advisory(self):
        r = sample(runway=None, days=None)
        r["PDUFA verification"] = "REVIEW — DATE UNVERIFIED"
        r["Trading setup /20"] = 0
        a = assess(r, event(new_dilution_flag="YES"),
                   as_of=DATE, feed_current=False, sec_current=False)
        self.assertTrue(a["Two-benchmark eligible"])
        self.assertEqual(a["Dilution overhang /15"], 0)
        self.assertEqual(a["Trading activity /20"], 0)
        self.assertEqual(a["PDUFA timing /5"], 0)
        self.assertIn("dilution", a["Two-benchmark risk flags"].lower())
        self.assertIn("SEC rescan", a["Two-benchmark risk flags"])

    def test_negative_phase3_readout_is_ranked_low_and_flagged_not_suppressed(self):
        e = event(state="VERIFIED_FAILURE")
        a = assess(sample(), e, as_of=DATE)
        self.assertTrue(a["Two-benchmark eligible"])
        self.assertEqual(a["Phase 3 quality /30"], 0)
        self.assertIn("negative outcome", a["Two-benchmark risk flags"])

    def test_expired_pdufa_is_warning_not_third_positive_benchmark(self):
        a = assess(sample(days=0), event(), as_of=DATE)
        self.assertTrue(a["Two-benchmark eligible"])
        self.assertEqual(a["PDUFA timing /5"], 0)
        self.assertIn("pre-decision setup expired", a["Two-benchmark risk flags"])

    def test_rank_eligible_candidates_by_scored_quality_not_cash_gate(self):
        a = sample("AAA", runway=24)
        b = sample("BBB", runway=8)
        c = sample("CCC", financed=False)
        rows = []
        for row in (b, c, a):
            row.update(assess(row, event(row["Ticker"]), as_of=DATE))
            rows.append(row)
        ranked = assign_ranks(rows)
        self.assertEqual([r["Ticker"] for r in ranked], ["AAA", "BBB"])
        self.assertEqual([r["Two-benchmark rank"] for r in ranked], [1, 2])
        self.assertIsNone(c["Two-benchmark rank"])

    def test_scanner_primary_shortlist_does_not_inherit_old_financial_gate(self):
        row = sample()
        e = event()
        with (
            patch("gem_scans.build_queue", return_value=(
                [row], {"feed_current": True, "as_of": DATE},
            )),
            patch("gem_scans._event_map", return_value={
                row["Exact event"]: e,
            }),
            patch("gem_scans.load_snapshots", return_value={}),
            patch("gem_scans.load_runway_history", return_value={}),
            patch("gem_scans.sec_recheck_current", return_value=False),
        ):
            out, status = build_gem_scans("does-not-exist", as_of=DATE)
        self.assertEqual(status["two_benchmark_candidate_count"], 1)
        self.assertEqual(out[0]["Two-benchmark rank"], 1)
        self.assertIsNone(out[0]["Post-Financing rank"])
        self.assertIn("Cash runway unknown", out[0]["Two-benchmark risk flags"])


if __name__ == "__main__":
    unittest.main()
