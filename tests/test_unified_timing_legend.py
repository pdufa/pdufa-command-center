"""Keep the unified dashboard countdown and financing key close to Matching programs."""
import unittest
from pathlib import Path

from pdufa_date_gradient import COUNTDOWN_BANDS
from pdufa_display_columns import FINANCE_PALETTE
from unified_clinical_trading import _timing_legend_html


class TimelineLegendTests(unittest.TestCase):
    def test_legend_shows_exact_cell_color_bands(self):
        markup = _timing_legend_html()
        for color in [band[2] for band in COUNTDOWN_BANDS]:
            with self.subTest(color=color):
                self.assertIn(f"background:{color}", markup)
        for label, color in [("Started", FINANCE_PALETTE["green"]),
                             ("Running", FINANCE_PALETTE["yellow"]),
                             ("Closed", FINANCE_PALETTE["red"]),
                             ("Unverified", FINANCE_PALETTE["unknown"])]:
            with self.subTest(label=label):
                self.assertIn(label, markup)
                self.assertIn(f"background:{color}", markup)
        self.assertIn("DAYS TO PDUFA", markup)
        self.assertIn("FINANCING TIMELINE (F)", markup)
        self.assertIn("29–0 days", markup)
        self.assertIn("Past / unknown", markup)
        self.assertIn("not FDA approval probability", markup)

    def test_three_stage_cards_share_one_horizontal_grid(self):
        source = (Path(__file__).resolve().parents[1]
                  / "unified_clinical_trading.py").read_text(encoding="utf-8")
        self.assertIn(
            'pipeline_col, gemjr_col, gem_col = st.columns([1, 1, 1], gap="small", wrap=False)',
            source)
        for column, panel in (
            ("pipeline_col", "overview_pipeline_panel"),
            ("gemjr_col", "overview_gemjr_panel"),
            ("gem_col", "overview_gem_panel"),
        ):
            with self.subTest(column=column):
                self.assertIn(
                    f'with {column}, st.container(border=True, key="{panel}")',
                    source)
        self.assertEqual(source.count('key="overview_panels"'), 1)
        self.assertLess(source.index("with pipeline_col"),
                        source.index("with gemjr_col"))
        self.assertLess(source.index("with gemjr_col"),
                        source.index("with gem_col"))
        self.assertNotIn("overview_pre3_panel", source)
        self.assertNotIn("overview_post3_panel", source)
        self.assertIn('gap="small", wrap=False)', source)
        self.assertNotIn("grid-template-columns:repeat(4", source)

    def test_evidence_and_timeline_remain_separate_from_stage_cards(self):
        source = (Path(__file__).resolve().parents[1]
                  / "unified_clinical_trading.py").read_text(encoding="utf-8")
        self.assertIn('    with st.expander("PDUFA TIMELINE", expanded=True):', source)
        self.assertLess(
            source.index('key="overview_gem_panel"'),
            source.index('    with st.expander("PDUFA TIMELINE"'))
        self.assertEqual(source.count('render_dashboard_sheet('), 2)
        self.assertEqual(
            source.count('st.markdown(_timing_legend_html(), unsafe_allow_html=True)'), 2)
        self.assertIn("render_gem_potential(root=root, compact=True", source)
        self.assertIn("two post-readout financing closures", source)

    def test_legend_sits_below_each_matching_count_before_table(self):
        source = (Path(__file__).resolve().parents[1]
                  / "unified_clinical_trading.py").read_text(encoding="utf-8")
        for metric in (
            'st.metric("Matching programs", len(df))',
            'st.metric("Matching source leads", len(post3))',
        ):
            with self.subTest(metric=metric):
                pos = source.index(metric)
                legend = source.index(
                    'st.markdown(_timing_legend_html(), unsafe_allow_html=True)', pos)
                table = source.index("render_dashboard_sheet(", pos)
                self.assertLess(pos, legend)
                self.assertLess(legend, table)


if __name__ == "__main__":
    unittest.main()
