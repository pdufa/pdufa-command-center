"""Candidate ticker discovery is a research queue, never a buy/entry list."""
import unittest
from datetime import date
import pandas as pd

from pre_phase3_trading import trading_research_queue


def row(**updates):
    r = {
        "Ticker": "OLMA",
        "Drug": "Sample phase 3 therapy",
        "Indication": "Sample indication",
        "NCT ID": "NCT12345678",
        "Primary Completion": "2026-11-15",
        "Primary Completion Type": "ESTIMATED",
        "Market Cap": 800_000_000,
        "Program Identity": "VERIFIED",
        "Phase 2 p Evidence": "NOT VERIFIED",
        "Source": "https://clinicaltrials.gov/study/NCT12345678",
    }
    r.update(updates)
    return r


class TradingResearchQueueTests(unittest.TestCase):
    def setUp(self):
        self.day = date(2026, 10, 10)

    def test_candidate_is_visible_but_never_entry_ready(self):
        q = trading_research_queue(pd.DataFrame([row()]), self.day)
        self.assertEqual(q["Ticker"].tolist(), ["OLMA"])
        self.assertEqual(q["Completion Date Precision"].tolist(), ["DAY"])
        self.assertTrue((q["Issuer Readout Date"] == "NOT VERIFIED").all())
        self.assertTrue(q["Trading Entry Gate"].str.contains("NOT ENTRY-READY").all())
        self.assertEqual(q.iloc[0]["Financing / Dilution"], "NOT CHECKED")
        self.assertEqual(q.iloc[0]["Price / Liquidity"], "NOT CHECKED")
        self.assertEqual(q.iloc[0]["Registry Source"],
                         "https://clinicaltrials.gov/study/NCT12345678")

    def test_month_only_does_not_invent_a_day_or_topline_date(self):
        q = trading_research_queue(pd.DataFrame([row(
            **{"Primary Completion": "2026-11"})]), self.day, 90)
        self.assertEqual(q.iloc[0]["Registry Primary Completion"], "2026-11")
        self.assertEqual(q.iloc[0]["Completion Date Precision"], "MONTH ONLY")
        self.assertEqual(q.iloc[0]["Issuer Readout Date"], "NOT VERIFIED")

    def test_window_excludes_past_and_distant_trial_completion(self):
        q = trading_research_queue(pd.DataFrame([
            row(**{"NCT ID": "NCT10000001", "Primary Completion": "2026-09-30"}),
            row(**{"NCT ID": "NCT10000002", "Primary Completion": "2026-12-31"}),
            row(**{"NCT ID": "NCT10000003", "Primary Completion": "2027-05-01"}),
        ]), self.day, 90)
        self.assertEqual(q["NCT ID"].tolist(), ["NCT10000002"])

    def test_month_window_overlap_handles_uncertain_day(self):
        # The registry specifies month only; the exact completion day is unknown.
        q = trading_research_queue(pd.DataFrame([
            row(**{"NCT ID": "NCT10000001", "Primary Completion": "2026-10"}),
            row(**{"NCT ID": "NCT10000002", "Primary Completion": "2026-09"}),
        ]), self.day, 90)
        self.assertEqual(q["NCT ID"].tolist(), ["NCT10000001"])

    def test_same_ticker_can_have_separate_trial_programs(self):
        q = trading_research_queue(pd.DataFrame([
            row(), row(), row(**{"NCT ID": "NCT12345679", "Drug": "Second therapy"}),
        ]), self.day)
        self.assertEqual(len(q), 2)
        self.assertEqual(q["Ticker"].nunique(), 1)

    def test_invalid_nct_and_missing_completion_are_excluded(self):
        q = trading_research_queue(pd.DataFrame([
            row(**{"NCT ID": "NOT_NCT"}),
            row(**{"Primary Completion": ""}),
        ]), self.day)
        self.assertTrue(q.empty)

    def test_missing_queue_and_unsupported_window_are_safe(self):
        self.assertTrue(trading_research_queue(pd.DataFrame(), self.day).empty)
        with self.assertRaises(ValueError):
            trading_research_queue(pd.DataFrame([row()]), self.day, 22)

    def test_source_reviewed_phase2_and_phase3_scores_appear_next_to_ticker(self):
        q = trading_research_queue(pd.DataFrame([row(**{
            "Phase 2 Clinical Score /25": 18.0,
            "Phase 3 Pre-Readout Score /75": 57.0,
            "Combined Pre-Readout Score /100": 75.0,
            "Combined Score Status": "COMBINED RESEARCH SCORE — NOT A PROBABILITY",
            "Input Coverage %": 69.2,
            "Basic Design Safeguards /5": 4,
        })]), self.day)
        self.assertEqual(q.columns[0], "Ticker")
        self.assertEqual(q.columns[1], "PRE PHASE 3 Score /100")
        self.assertEqual(float(q.iloc[0]["PRE PHASE 3 Score /100"]), 75)
        self.assertEqual(float(q.iloc[0]["Phase 2 Clinical /25"]), 18)
        self.assertEqual(float(q.iloc[0]["Phase 3 Pre-Readout /75"]), 57)
        self.assertEqual(float(q.iloc[0]["Documented Inputs %"]), 69.2)
        self.assertEqual(float(q.iloc[0]["Basic Design Safeguards /5"]), 4)
        self.assertIn("NOT A PROBABILITY", q.iloc[0]["PRE PHASE 3 Score Status"])
        self.assertIn("NOT ENTRY-READY", q.iloc[0]["Trading Entry Gate"])

    def test_no_invented_score_for_missing_or_unverified_clinical_assessment(self):
        rows = [
            row(),
            row(**{
                "NCT ID": "NCT10000002",
                "Combined Pre-Readout Score /100": 80,
                "Phase 2 Clinical Score /25": 20,
                "Phase 3 Pre-Readout Score /75": 60,
                "Combined Score Status": "NOT SCORED — NEEDS REVIEW",
                "Input Coverage %": 46.2,
            }),
            row(**{
                "NCT ID": "NCT10000003",
                "Combined Pre-Readout Score /100": 80,
                "Phase 2 Clinical Score /25": 20,
                "Phase 3 Pre-Readout Score /75": 55,  # mismatched total
                "Combined Score Status": "COMBINED RESEARCH SCORE — NOT A PROBABILITY",
            }),
        ]
        q = trading_research_queue(pd.DataFrame(rows), self.day)
        self.assertTrue(q["PRE PHASE 3 Score /100"].isna().all())
        self.assertTrue(q["Phase 2 Clinical /25"].isna().all())
        self.assertTrue(q["Phase 3 Pre-Readout /75"].isna().all())
        self.assertTrue(q["PRE PHASE 3 Score Status"].str.startswith("NOT SCORED").all())
        self.assertEqual(float(q.loc[q["NCT ID"].eq("NCT10000002"),
                                     "Documented Inputs %"].iloc[0]), 46.2)

    def test_source_app_exposes_candidates_without_hidden_toggle(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        section = src.split("def render_pre_phase3():", 1)[1].split("query_event =", 1)[0]
        self.assertIn("PRE PHASE 3 — STOCK CANDIDATES TO RESEARCH", section)
        self.assertIn("trading_research_queue(", section)
        self.assertIn("PRE PHASE 3 SCORE /100", section)
        self.assertLess(section.index("_input_rows, _input_counts = audit_pre_readout_inputs("),
                        section.index("_trade_shortlist = trading_research_queue("))
        self.assertIn("pre_phase3_trade_research_table_v1", section)
        self.assertIn("pre_phase3_add_watchlist_v1", section)
        self.assertIn("DOWNLOAD PRE PHASE 3 RESEARCH WATCHLIST", section)
        self.assertLess(section.index("PRE PHASE 3 — STOCK CANDIDATES TO RESEARCH"),
                        section.index("INPUT AVAILABILITY — BEFORE THE PHASE 3 READOUT"))

if __name__ == "__main__":
    unittest.main()
