"""Four PDUFA subtab presentation and financing identity regression checks."""
import unittest
from datetime import date

import pandas as pd

from pdufa_display_columns import (
    FRONT, enrich_exact_trials, finance_style, prepare_pdufa_grid,
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
