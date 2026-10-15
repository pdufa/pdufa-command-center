"""Regression checks for real round question-mark help icons in #2/#3/#4."""
import re
import unittest
from pathlib import Path

import pandas as pd

from pdufa_circled_help_grid import dashboard_sheet_html
from pdufa_table_headers import column_help


class RealCircledHelpTests(unittest.TestCase):
    def test_each_header_has_a_real_css_circle_to_the_right(self):
        frame = pd.DataFrame({
            "Ticker": ["TEST"],
            "Days to PDUFA": [75],
            "F": ["F START"],
            "Drug": ["Example drug"],
        })
        rendered = dashboard_sheet_html(frame, list(frame.columns), height=310)
        self.assertEqual(rendered.count('class="pdufa-circled-help"'), 4)
        self.assertEqual(rendered.count('class="pdufa-th-sort"'), 4)
        self.assertIn('border-radius:50%', rendered)
        self.assertIn('>?</span>', rendered)
        self.assertNotIn("\u20dd", rendered)
        for title in frame.columns:
            header = re.search(
                r'<th[^>]*class="col_heading[^"]*"[^>]*>(.*?)</th>',
                rendered, flags=re.S,
            )
            self.assertIsNotNone(header)
            rendered = rendered.replace(header.group(0), "", 1)
            self.assertIn(f'<span class="pdufa-th-label">{title}</span>', header.group(1))
            self.assertLess(header.group(1).index(title),
                            header.group(1).index('class="pdufa-circled-help"'))
        self.assertIn(column_help("Days to PDUFA"), dashboard_sheet_html(frame, list(frame)))

    def test_finance_and_pdufa_colors_survive_custom_help_headers(self):
        frame = pd.DataFrame({
            "Ticker": ["ABC", "DEF"],
            "Days to PDUFA": [75, 10],
            "F": ["F START", "F CLOSED"],
        })
        rendered = dashboard_sheet_html(frame, list(frame.columns))
        for color in ("#86efac", "#f87171", "#bbf7d0", "#fecaca"):
            self.assertIn(color, rendered)
        self.assertIn('class="pdufa-help-grid"', rendered)
        self.assertIn('table-layout:auto', rendered)
        self.assertIn('addEventListener(\'click\'', rendered)

    def test_escape_markup_in_cell_and_help_content(self):
        rendered = dashboard_sheet_html(
            pd.DataFrame({"Drug": ["<script>alert(1)</script>"]}), ["Drug"]
        )
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("border-radius:50%", rendered)

    def test_all_three_panels_use_real_circled_help_renderer(self):
        source = (Path(__file__).resolve().parents[1]
                  / "unified_clinical_trading.py").read_text(encoding="utf-8")
        for name in ("overview_pipeline_panel", "overview_gemjr_panel"):
            at = source.index(f'key="{name}"')
            self.assertIn("render_dashboard_sheet(", source[at:at + 1800])
        self.assertEqual(source.count("render_dashboard_sheet("), 2)
        self.assertIn("render_gem_potential(root=root, compact=True", source)


if __name__ == "__main__":
    unittest.main()
