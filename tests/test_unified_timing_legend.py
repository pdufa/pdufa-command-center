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

    def test_legend_sits_below_each_matching_count_before_table(self):
        source = (Path(__file__).resolve().parents[1]
                  / "unified_clinical_trading.py").read_text(encoding="utf-8")
        for metric, dataframe in (
            ('st.metric("Matching programs", len(df))',
             'pdufa_dataframe(finance_style(df.head(150))'),
            ('st.metric("Matching pre-readout programs", len(pre3))',
             'pdufa_dataframe(finance_style(pre3.head(150))'),
            ('st.metric("Matching candidates", len(post3))',
             'pdufa_dataframe(finance_style(post3.head(150))'),
        ):
            with self.subTest(metric=metric):
                pos = source.index(metric)
                legend = source.index(
                    'st.markdown(_timing_legend_html(), unsafe_allow_html=True)', pos
                )
                table = source.index(dataframe, pos)
                self.assertLess(pos, legend)
                self.assertLess(legend, table)
        self.assertEqual(
            source.count('st.markdown(_timing_legend_html(), unsafe_allow_html=True)'), 3
        )


if __name__ == "__main__":
    unittest.main()
