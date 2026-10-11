"""Four PDUFA subtab presentation and financing identity regression checks."""
import unittest
from datetime import date

import pandas as pd

from pdufa_display_columns import (
    FRONT, DISPLAY_ORDER_OPTIONS, enrich_exact_trials, finance_style,
    prepare_pdufa_grid, sort_pdufa_grid, sort_pdufa_rows,
)


class PdufaGridTests(unittest.TestCase):
    def test_shared_order_dates_scores_and_cash_runway(self):
        source = pd.DataFrame([{
            "Ticker": "TEST", "NCT ID": "NCT12345678",
            "PDUFA Target": "2026-12-15", "Evidence score /100": 70,
            "Clinical evidence /30": 21, "Primary endpoint p values observed": "0.001",
            "Financing cycle (separate)": "RED — FINANCING CLOSED (HISTORICAL)",
            "cash_runway_months": 18, "Cash runway verified date": "2026-10-01",
        }])
        view = prepare_pdufa_grid(source, as_of=date(2026, 10, 11))
        self.assertEqual(view.columns[:len(FRONT)].tolist(), list(FRONT))
        self.assertEqual(view.loc[0, "Score /100"], 70)
        self.assertEqual(view.loc[0, "Clinical evidence /30"], 21)
        self.assertEqual(view.loc[0, "PDUFA Date"], "2026-12-15")
        self.assertEqual(int(view.loc[0, "Days to PDUFA"]), 65)
        self.assertEqual(view.loc[0, "Date Classification"], "90–61 DAYS")
        self.assertEqual(view.loc[0, "Primary p"], "0.001")
        self.assertEqual(view.loc[0, "F"], "F CLOSED")
        self.assertEqual(view.loc[0, "Cash Runway (months)"], 18)
        self.assertEqual(view.loc[0, "Cash Runway As Of"], "2026-10-01")

    def test_front_column_order_and_score_first_sort_with_no_score_last(self):
        self.assertEqual(
            list(FRONT[:5]),
            ["Ticker", "Score /100", "PDUFA Date", "Days to PDUFA", "Score type"],
        )
        self.assertEqual(DISPLAY_ORDER_OPTIONS, ("Top Score", "Ticker A–Z"))
        frame = pd.DataFrame([
            {"Ticker": "ZZZ", "NCT ID": "NCT00000001",
             "Evidence score /100": 20, "Pre-readout research score /100": 20, "PDUFA Date": "2026-12-01"},
            {"Ticker": "BBB", "NCT ID": "NCT00000002",
             "Evidence score /100": 90, "Pre-readout research score /100": 90, "PDUFA Date": "2026-12-20"},
            {"Ticker": "AAA", "NCT ID": "NCT00000003",
             "Evidence score /100": 90, "Pre-readout research score /100": 90, "PDUFA Date": "2026-12-21"},
            {"Ticker": "CCC", "NCT ID": "NCT00000004",
             "PDUFA Date": ""},
        ])
        for view in ("UNIFIED", "PIPELINE", "PRE PHASE 3", "POST PHASE 3"):
            with self.subTest(view=view):
                displayed = prepare_pdufa_grid(frame, view=view,
                                               as_of=date(2026, 10, 11))
                top = sort_pdufa_grid(displayed, "Top Score")
                self.assertEqual(top["Ticker"].tolist(), ["AAA", "BBB", "ZZZ", "CCC"])
                name = sort_pdufa_grid(displayed, "Ticker A–Z")
                self.assertEqual(name["Ticker"].tolist(), ["AAA", "BBB", "CCC", "ZZZ"])
                self.assertEqual(top.columns[:5].tolist(), list(FRONT[:5]))
                self.assertTrue(pd.isna(top.iloc[-1]["Score /100"]))

    def test_equal_scores_use_numeric_days_before_ticker_with_missing_days_last(self):
        frame = pd.DataFrame([
            {"Ticker": "A_LATER", "Score /100": "90", "Days to PDUFA": "100"},
            {"Ticker": "Z_SOONER", "Score /100": "90", "Days to PDUFA": "9"},
            {"Ticker": "HIGHER", "Score /100": "91", "Days to PDUFA": "180"},
            {"Ticker": "A_UNDATED", "Score /100": "90", "Days to PDUFA": None},
            {"Ticker": "LOWER", "Score /100": "20", "Days to PDUFA": "1"},
            {"Ticker": "UNSCORED_DATED", "Score /100": None, "Days to PDUFA": "3"},
            {"Ticker": "UNSCORED_UNDATED", "Score /100": None, "Days to PDUFA": "unknown"},
        ])
        result = sort_pdufa_grid(frame)
        self.assertEqual(result["Ticker"].tolist(), [
            "HIGHER", "A_LATER", "Z_SOONER", "A_UNDATED", "LOWER",
            "UNSCORED_DATED", "UNSCORED_UNDATED",
        ])
        # Sorting changes the row order, preserving the original field values.
        pd.testing.assert_frame_equal(result[frame.columns].sort_index(), frame)
        self.assertNotIn("_score_sort", result)
        self.assertNotIn("_days_sort", result)

    def test_missing_scores_and_deterministic_ticker_tiebreak(self):
        frame = pd.DataFrame([
            {"Ticker": "ABC", "NCT ID": "NCT00000002", "Score /100": None},
            {"Ticker": "ABC", "NCT ID": "NCT00000001", "Score /100": None},
            {"Ticker": "XYZ", "NCT ID": "NCT00000001", "Score /100": 10},
        ])
        sorted_frame = sort_pdufa_grid(frame)
        self.assertEqual(sorted_frame["NCT ID"].tolist(),
                         ["NCT00000001", "NCT00000001", "NCT00000002"])
        self.assertEqual(sorted_frame["Ticker"].tolist(), ["XYZ", "ABC", "ABC"])
        with self.assertRaises(ValueError):
            sort_pdufa_grid(frame, "Lowest Score")

    def test_legacy_countdown_names_share_score_and_days_descending_order(self):
        for days_column in ("Days to PDUFA", "DAYS TO PDUFA", "days_to_pdufa", "Days Left"):
            with self.subTest(days_column=days_column):
                frame = pd.DataFrame([
                    {"Ticker": "SOON", "Trade Score": "90", days_column: "9"},
                    {"Ticker": "LATER", "Trade Score": "90", days_column: "100"},
                    {"Ticker": "BEST", "Trade Score": "91", days_column: "1"},
                    {"Ticker": "UNDATED", "Trade Score": "90", days_column: None},
                    {"Ticker": "UNSCORED", "Trade Score": None, days_column: "200"},
                ], index=[0, 0, 1, 1, 2])
                result = sort_pdufa_rows(frame)
                self.assertEqual(result["Ticker"].tolist(),
                                 ["BEST", "LATER", "SOON", "UNDATED", "UNSCORED"])
                pd.testing.assert_frame_equal(result, frame.iloc[[2, 1, 0, 3, 4]])

    def test_unscored_countdown_uses_descending_days_and_missing_last(self):
        frame = pd.DataFrame({"Ticker": ["A", "B", "C"],
                              "DAYS TO PDUFA": [9, None, 100]})
        self.assertEqual(sort_pdufa_rows(frame)["Ticker"].tolist(), ["C", "A", "B"])

    def test_missing_data_does_not_become_a_zero_or_financing_close(self):
        source = pd.DataFrame([{
            "Ticker": "TEST", "NCT ID": "NCT12345678",
            "Linked Phase 2 PRIMARY p": "p=0.012",
            "Financing cycle (separate)": "REVIEW — FINANCING UNVERIFIED",
        }])
        view = prepare_pdufa_grid(source, as_of=date(2026, 10, 11))
        self.assertTrue(pd.isna(view.loc[0, "Score /100"]))
        self.assertEqual(view.loc[0, "Score type"], "NOT SCORED")
        self.assertEqual(view.loc[0, "PDUFA Date"], "")
        self.assertTrue(pd.isna(view.loc[0, "Days to PDUFA"]))
        self.assertTrue(pd.isna(view.loc[0, "Primary p"]))
        self.assertEqual(view.loc[0, "F"], "F UNKNOWN")
        self.assertTrue(pd.isna(view.loc[0, "Cash Runway (months)"]))

    def test_exact_trial_join_rejects_drug_conflict_and_duplicates(self):
        base = pd.DataFrame([{
            "Ticker": "AAAA", "NCT ID": "NCT12345678", "Drug": "drug A",
        }])
        bad = [{
            "Ticker": "AAAA", "NCT ID": "NCT12345678",
            "Drug": "drug B", "Evidence score /100": 95,
            "Financing cycle (separate)": "RED — FINANCING CLOSED (HISTORICAL)",
        }]
        rejected = enrich_exact_trials(base, post=bad)
        self.assertTrue(pd.isna(rejected.loc[0, "Evidence score /100"]))
        self.assertTrue(pd.isna(rejected.loc[0, "Financing cycle (separate)"]))
        duplicate = [dict(bad[0], Drug="drug A"), dict(bad[0], Drug="drug A")]
        rejected = enrich_exact_trials(base, post=duplicate)
        self.assertTrue(pd.isna(rejected.loc[0, "Evidence score /100"]))
        good = [dict(bad[0], Drug="drug A")]
        accepted = enrich_exact_trials(base, post=good)
        self.assertEqual(accepted.loc[0, "Evidence score /100"], 95)

    def test_financing_block_colors_have_black_text(self):
        src = pd.DataFrame({"F": ["F START", "F RUN", "F CLOSED", "F UNKNOWN"]})
        rendered = finance_style(src).to_html()
        for color in ("#bbf7d0", "#fef08a", "#fecaca", "#e5e7eb"):
            self.assertIn(color, rendered)
        self.assertIn("color: #000000", rendered)

    def test_each_of_four_tabs_receives_model_specific_score(self):
        """Review triage scores are visibly distinct from clinical evidence."""
        cases = [
            ("PIPELINE", {"Review priority /100": 58,
                          "Review priority status": "REVIEW CANDIDATE"}, 58,
             "PRE: review priority"),
            ("PRE PHASE 3", {"Review priority /100": 47,
                             "Review priority status": "REVIEW CANDIDATE"}, 47,
             "PRE: review priority"),
            ("POST PHASE 3", {"Research priority /100": 34}, 34,
             "POST: research triage"),
            ("UNIFIED", {"Pre-readout research score /100": 81,
                         "Research priority /100": 33}, 81,
             "PRE: reviewed clinical"),
        ]
        for view, evidence, expected, label in cases:
            with self.subTest(view=view):
                frame = pd.DataFrame([{"Ticker": "TEST", **evidence}])
                result = prepare_pdufa_grid(frame, view=view,
                                            as_of=date(2026, 10, 11))
                self.assertEqual(result.columns[:len(FRONT)].tolist(), list(FRONT))
                self.assertEqual(result.loc[0, "Score /100"], expected)
                self.assertEqual(result.loc[0, "Score type"], label)

    def test_clinical_and_evidence_score_overrides_research_priority(self):
        frame = pd.DataFrame([{
            "Ticker": "TEST",
            "Evidence score /100": 74,
            "Research priority /100": 10,
            "Pre-readout research score /100": 88,
            "Review priority /100": 35,
        }])
        expected = {
            "POST PHASE 3": (74, "POST: evidence"),
            "PRE PHASE 3": (88, "PRE: reviewed clinical"),
            "PIPELINE": (88, "PRE: reviewed clinical"),
            "UNIFIED": (74, "POST: evidence"),
        }
        for view, (score, label) in expected.items():
            result = prepare_pdufa_grid(frame, view=view)
            self.assertEqual(result.loc[0, "Score /100"], score)
            self.assertEqual(result.loc[0, "Score type"], label)

    def test_excluded_pre_priority_not_attached_and_invalid_scores_not_used(self):
        frame = pd.DataFrame([{
            "Ticker": "TEST", "Review priority /100": 88,
            "Review priority status": "EXCLUDED — unverified identity",
            "Research priority /100": "not a number",
            "Evidence score /100": 110,
        }])
        for view in ("UNIFIED", "PIPELINE", "PRE PHASE 3", "POST PHASE 3"):
            result = prepare_pdufa_grid(frame, view=view)
            self.assertTrue(pd.isna(result.loc[0, "Score /100"]))
            self.assertEqual(result.loc[0, "Score type"], "NOT SCORED")

    def test_pipeline_exact_trial_join_carries_review_priority_score(self):
        pipeline = pd.DataFrame([{
            "Ticker": "TEST", "NCT ID": "NCT12345678", "Drug": "Alpha",
        }])
        pre = [{
            "Ticker": "TEST", "NCT ID": "NCT12345678", "Drug": "Alpha",
            "Review priority /100": 62, "Review priority status": "REVIEW CANDIDATE",
            "Priority stage /30": 30, "Priority identity /15": 15,
        }]
        matched = enrich_exact_trials(pipeline, pre=pre)
        displayed = prepare_pdufa_grid(matched, view="PIPELINE",
                                       as_of=date(2026, 10, 11))
        self.assertEqual(displayed.loc[0, "Score /100"], 62)
        self.assertEqual(displayed.loc[0, "Score type"], "PRE: review priority")
        self.assertEqual(displayed.loc[0, "Priority stage /30"], 30)



if __name__ == "__main__":
    unittest.main()
