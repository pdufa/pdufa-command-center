"""WT stage tables never promote candidates or infer missing information."""
import ast
import unittest
from pathlib import Path

import pandas as pd

from stage_wt_tables import selected_stage_rows, stage_rows

ROOT = Path(__file__).resolve().parents[1]


class StageWTTests(unittest.TestCase):
    def test_pipeline_ticker_with_two_trials_remains_two_programs(self):
        rows = pd.DataFrame([
            {"record_id": "PIPE-A", "ticker": "ABCD", "drug": "drug1",
             "indication": "A", "nct_id": "NCT00000001",
             "current_stage": "Phase 3", "pdufa_date": ""},
            {"record_id": "PIPE-B", "ticker": "ABCD", "drug": "drug2",
             "indication": "B", "nct_id": "NCT00000002",
             "current_stage": "Phase 2", "pdufa_date": ""},
            {"record_id": "PIPE-A", "ticker": "ABCD", "drug": "drug1",
             "indication": "A", "nct_id": "NCT00000001",
             "current_stage": "Phase 3", "pdufa_date": ""},
        ])
        x = selected_stage_rows(rows, "PIPELINE", ["ABCD"], [])
        self.assertEqual(len(x["watch"]), 2)
        self.assertEqual(len(x["trade"]), 0)
        self.assertEqual({r["Trial / Program"] for r in x["watch"]},
                         {"NCT00000001", "NCT00000002"})

    def test_gem_jr_label_never_creates_a_gem_stock(self):
        jr = [{"Ticker": "LEAD", "Exact program": "EVENT-A",
               "GEM status": "AWAITING FINANCING",
               "Still needed": "2nd SEC financing close"}]
        self.assertEqual(len(selected_stage_rows(jr, "GEM JR", ["LEAD"], [])["watch"]), 1)
        self.assertEqual(selected_stage_rows([], "GEM", ["LEAD"], ["LEAD"])["trade"], [])
        self.assertIn("2nd SEC financing close",
                      stage_rows(jr, "GEM JR")[0]["Missing / Next action"])

    def test_gem_verified_rows_are_source_scoped_not_ticker_joins(self):
        verified = [{"Ticker": "CLEAR", "Drug": "exact1",
                     "Exact program": "PROGRAM-1",
                     "Trade status": "RESEARCH-QUALIFIED / ENTRY GATES ON HOLD"}]
        x = selected_stage_rows(verified, "GEM",
                                ["CLEAR", "OTHER"], ["CLEAR", "OTHER"])
        self.assertEqual([r["Ticker"] for r in x["watch"]], ["CLEAR"])
        self.assertEqual([r["Ticker"] for r in x["trade"]], ["CLEAR"])
        self.assertIn("ENTRY GATES ON HOLD", x["trade"][0]["Evidence / Qualification"])

    def test_invalid_or_missing_tickers_not_added(self):
        source = [{"Ticker": "not a ticker", "Drug": "x"},
                  {"Ticker": None, "Drug": "y"},
                  {"Ticker": "OK", "Drug": "z"}]
        self.assertEqual([r["Ticker"] for r in stage_rows(source, "PIPELINE")], ["OK"])

    def test_ui_only_connects_existing_stage_collections(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        junior = (ROOT / "gem_jr_ui.py").read_text(encoding="utf-8")
        gem = (ROOT / "gem_potential_ui.py").read_text(encoding="utf-8")
        wt = (ROOT / "stage_wt_tables.py").read_text(encoding="utf-8")
        for path in ("app.py", "gem_jr_ui.py", "gem_potential_ui.py",
                     "stage_wt_tables.py"):
            source = (ROOT / path).read_text(encoding="utf-8")
            ast.parse(source, filename=path)
        self.assertIn('render_stage_wt_tables(\n                    "PIPELINE", prepared', app)
        self.assertIn('"GEM JR", active + held, namespace="gem_jr"', junior)
        self.assertIn('"GEM", source_cleared, namespace="gem"', gem)
        self.assertNotIn('gem_jr_col, gem_col = st.columns', app)
        self.assertIn('with st.container(border=True, key="gem_jr_shared_block")', app)
        self.assertIn('with st.container(border=True, key="gem_shared_block")', app)
        self.assertIn('st.dataframe(', wt)
        self.assertIn('render_ticker_toggle_panel(', wt)
        self.assertIn('st.session_state.get("trading_tickers", [])', wt)


if __name__ == "__main__":
    unittest.main()
