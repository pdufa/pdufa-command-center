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

    def test_four_cards_share_one_horizontal_grid(self):
        source = (Path(__file__).resolve().parents[1]
                  / "unified_clinical_trading.py").read_text(encoding="utf-8")
        self.assertIn(
            'gem_col, pipeline_col, pre3_col, post3_col = st.columns([1, 1, 1, 1], gap="small")',
            source,
        )
        for column, panel in (
            ("gem_col", "overview_gem_panel"),
            ("pipeline_col", "overview_pipeline_panel"),
            ("pre3_col", "overview_pre3_panel"),
            ("post3_col", "overview_post3_panel"),
        ):
            with self.subTest(column=column):
                self.assertIn(
                    f'with {column}, st.container(border=True, key="{panel}")',
                    source,
                )
        self.assertEqual(source.count('key="overview_panels"'), 1)
        self.assertLess(source.index("with gem_col"),
                        source.index("with pipeline_col"))
        self.assertLess(source.index("with pipeline_col"),
                        source.index("with pre3_col"))
        self.assertLess(source.index("with pre3_col"),
                        source.index("with post3_col"))
        # All four stay adjacent on mobile through sideways scrolling.
        self.assertIn("grid-template-columns:repeat(4,minmax(280px,1fr))", source)
        self.assertIn('.st-key-overview_panels {overflow-x:auto;}', source)
        self.assertNotIn("grid-template-columns:repeat(2", source)
        self.assertNotIn("grid-template-columns:minmax(0,100%)", source)
        self.assertIn('width:100% !important;', source)
        self.assertIn('gap:0 !important;', source)
        self.assertIn('padding-inline:0.375rem !important;', source)
        # Only the overview row scrolls; nested timeline metrics keep their layout.
        self.assertIn(":has(.st-key-overview_pipeline_panel)", source)
        self.assertIn('a, b, c = st.columns(3)', source)

    def test_equal_height_cards_without_stretching_post3_timeline(self):
        source = (Path(__file__).resolve().parents[1]
                  / "unified_clinical_trading.py").read_text(encoding="utf-8")
        # Cards fill the height of their responsive row; no fixed pixel height.
        self.assertIn("align-items:stretch !important", source)
        self.assertIn("align-self:stretch !important", source)
        self.assertIn("flex:1 1 auto", source)
        self.assertIn("height:100%", source)
        self.assertIn("display:flex !important", source)
        self.assertIn('[data-testid="stVerticalBlockBorderWrapper"]:has(', source)
        self.assertIn("flex-direction:column !important", source)
        # The expanded all-program timeline must be below the equal-height
        # cards; otherwise #4 would make all three unreasonably tall.
        self.assertIn('    with st.expander("PDUFA TIMELINE", expanded=True):', source)
        self.assertNotIn('            with st.expander("PDUFA TIMELINE"', source)
        self.assertLess(
            source.index('key="overview_trading_export"'),
            source.index('    with st.expander("PDUFA TIMELINE"'),
        )
        self.assertEqual(source.count('render_dashboard_sheet('), 3)
        self.assertEqual(
            source.count('st.markdown(_timing_legend_html(), unsafe_allow_html=True)'), 3,
        )

    def test_legend_sits_below_each_matching_count_before_table(self):
        source = (Path(__file__).resolve().parents[1]
                  / "unified_clinical_trading.py").read_text(encoding="utf-8")
        for metric in (
            'st.metric("Matching programs", len(df))',
            'st.metric("Matching pre-readout programs", len(pre3))',
            'st.metric("Matching candidates", len(post3))',
        ):
            with self.subTest(metric=metric):
                pos = source.index(metric)
                legend = source.index(
                    'st.markdown(_timing_legend_html(), unsafe_allow_html=True)', pos
                )
                table = source.index("render_dashboard_sheet(", pos)
                self.assertLess(pos, legend)
                self.assertLess(legend, table)
        self.assertEqual(
            source.count('st.markdown(_timing_legend_html(), unsafe_allow_html=True)'), 3
        )


if __name__ == "__main__":
    unittest.main()
