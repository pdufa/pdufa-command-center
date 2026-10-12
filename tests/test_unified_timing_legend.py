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

    def test_three_sheets_share_one_responsive_grid(self):
        source = (Path(__file__).resolve().parents[1]
                  / "unified_clinical_trading.py").read_text(encoding="utf-8")
        self.assertIn(
            'pipeline_col, pre3_col, post3_col = st.columns(3, gap="small")',
            source,
        )
        for column, panel in (
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
        self.assertLess(source.index("with pipeline_col"),
                        source.index("with pre3_col"))
        self.assertLess(source.index("with pre3_col"),
                        source.index("with post3_col"))
        # Three across on large screens; wrap to two then one on narrower screens.
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))", source)
        self.assertIn("@media (max-width:1250px)", source)
        self.assertIn("grid-template-columns:repeat(2,minmax(0,1fr))", source)
        self.assertIn("@media (max-width:800px)", source)
        self.assertIn("grid-template-columns:minmax(0,1fr)", source)
        # Only the overview row wraps; nested PDUFA timeline metrics do not.
        self.assertIn(":has(.st-key-overview_pipeline_panel)", source)
        self.assertIn('a, b, c = st.columns(3)', source)

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
