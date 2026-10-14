"""Three-level GEM list regressions: exact scores, underlying data, and W/T controls."""
from pathlib import Path
import unittest

from gem_nested_master_ui import FACTOR_FIELDS, _score_check, _unique_sources, score_factor_inputs

ROOT = Path(__file__).resolve().parents[1]


def _row(eligible=True):
    return {
        "_eligible": eligible,
        "GEM Score /100": 84 if eligible else None,
        "Phase 3 Quality /30": 25 if eligible else None,
        "Financial Runway /20": 17 if eligible else None,
        "Trading Activity /20": 17 if eligible else None,
        "Dilution /15": 15 if eligible else None,
        "Hedge-Fund Accumulation /10": 6 if eligible else None,
        "PDUFA Timing /5": 4 if eligible else None,
        "Cash Runway (months)": 18,
        "Days to PDUFA": 22,
        "Planned Exit (-3 days)": "2026-11-01",
        "Phase 3 Source": "https://issuer.example/trial",
        "Financing Source": "https://www.sec.gov/filing",
        "PDUFA Source": "https://issuer.example/fda",
        "Hedge-Fund Source Links": "https://www.sec.gov/13f",
    }


class NestedGEMTests(unittest.TestCase):
    def test_100_point_factor_allocation_is_unchanged(self):
        self.assertEqual([max_points for _, _, max_points in FACTOR_FIELDS],
                         [30, 20, 20, 15, 10, 5])
        self.assertEqual(sum(cap for _, _, cap in FACTOR_FIELDS), 100)

    def test_score_checks_actual_factor_sum(self):
        row = _row()
        self.assertTrue(_score_check(row))
        row["GEM Score /100"] = 83
        self.assertFalse(_score_check(row))
        self.assertIsNone(_score_check(_row(False)))

    def test_trading_arithmetic_uses_real_12_8_formula(self):
        item = {"Trading setup /20": 15, "Market activity /10": 10}
        table = score_factor_inputs(item, _row(), "Trading Activity /20")
        self.assertIn("9.00 / 12", table[0]["Contribution / rule"])
        self.assertIn("8.00 / 8", table[1]["Contribution / rule"])
        self.assertEqual(table[-1]["Actual saved value"], "17 / 20")

    def test_unverified_candidate_never_displays_a_score(self):
        row = _row(False)
        source = {"Trading setup /20": 20, "Market activity /10": 10}
        table = score_factor_inputs(source, row, "Trading Activity /20")
        self.assertEqual(table[-1]["Actual saved value"],
                         "Not scored — entry benchmarks pending")
        self.assertIn("not scored", table[0]["Contribution / rule"])

    def test_ambiguous_event_identity_never_cross_joins_sources(self):
        items = [
            {"Exact event": "ABCD|NCT1", "Clinical evidence /30": 20},
            {"Exact event": "ABCD|NCT1", "Clinical evidence /30": 28},
            {"Exact event": "ABCD|NCT2", "Clinical evidence /30": 12},
        ]
        mapping = _unique_sources(items)
        self.assertNotIn("ABCD|NCT1", mapping)
        self.assertEqual(mapping["ABCD|NCT2"]["Clinical evidence /30"], 12)

    def test_gem_first_tab_and_shared_wt_buttons(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        overview = (ROOT / "unified_clinical_trading.py").read_text(encoding="utf-8")
        ui = (ROOT / "gem_nested_master_ui.py").read_text(encoding="utf-8")
        self.assertIn('["GEM", "PIPELINE", "PRE PHASE 3"', app)
        self.assertIn('previous_subtab == "UNIFIED OVERVIEW"', app)
        self.assertIn("render_gem_nested_master(root=root, selections_ready=True, compact=True)", overview)
        block = '#1 GEM — THREE-LEVEL NESTED MASTER LIST (show / hide)'
        self.assertIn(block, overview)
        self.assertIn('if st.toggle(', overview)
        self.assertIn('key="overview_show_gem_master"', overview)
        # GEM is the first sibling of the three existing cards.
        self.assertIn('gem_col, pipeline_col, pre3_col, post3_col = st.columns([1, 1, 1, 1]', overview)
        self.assertIn('with st.expander("PDUFA TIMELINE", expanded=True)', overview)
        self.assertIn('with st.expander("SOURCE MATCH & SCORE COVERAGE AUDIT"', overview)
        self.assertIn('st.download_button("EXPORT COMBINED TRIAL VIEW"', overview)
        self.assertIn('st.download_button("EXPORT PRE3 PROGRAMS"', overview)
        self.assertIn('st.download_button("EXPORT TRADING CANDIDATES"', overview)
        # The show/hide control and drill-down live inside #1, next to #2–#4.
        entrypoint = overview.index('with gem_col, st.container(')
        entry = overview[entrypoint:overview.index('with pipeline_col, st.container(', entrypoint)]
        self.assertIn(block, entry)
        self.assertIn('render_gem_nested_master(root=root, selections_ready=True, compact=True)', entry)
        self.assertIn('value=False, key="overview_show_gem_master"', entry)
        self.assertIn('key="overview_gem_panel"', entry)
        self.assertIn('st.markdown("### #2-PIPELINE")', overview)

        self.assertIn("### GEM — STOCK → FACTORS → SOURCE INPUTS", ui)
        self.assertIn("_init_browser_selection", ui)
        self.assertIn('args=(ticker, "watch")', ui)
        self.assertIn('args=(ticker, "trade")', ui)
        self.assertIn('pd.DataFrame(matching).reindex(columns=MASTER_COLUMNS + TRADE_COLUMNS)', ui)
        self.assertIn("render_gem_trade_panel(", ui)
        self.assertIn("attach_trade_fields(", ui)
        self.assertIn("factor_col.button(", ui)
        self.assertIn("score_factor_inputs(", ui)


if __name__ == "__main__":
    unittest.main()
