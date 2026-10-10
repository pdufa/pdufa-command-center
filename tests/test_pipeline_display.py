import unittest
from datetime import date

import pandas as pd

from pipeline_display import DATE_BANDS, prepare_pipeline, filter_pipeline, chart_rows


AS_OF = date(2026, 10, 9)


def example_records():
    rows = []
    for i in range(15):
        rows.append({
            "record_id": f"EVENT|{i}",
            "ticker": f"BIO{i:02d}",
            "company": f"Company {i}",
            "drug": f"Drug {i}",
            "indication": "Condition",
            "nct_id": "",
            "current_stage": "PDUFA Decision" if i < 12 else "FDA Acceptance",
            "stage_tags": ("FDA Acceptance", "PDUFA Decision"),
            "pdufa_date": "2026-10-20",
        })
    rows.append({
        "record_id": "TRIAL|NCT00000001",
        "ticker": "BIO15",
        "company": "Company 15",
        "drug": "Phase 3 Drug",
        "indication": "Condition",
        "nct_id": "NCT00000001",
        "current_stage": "Phase 3",
        "stage_tags": ("Phase 3",),
        "pdufa_date": "",
    })
    return prepare_pipeline(pd.DataFrame(rows), AS_OF)


class PipelineDisplayTests(unittest.TestCase):
    def test_no_click_no_stages_or_dates_is_zero(self):
        frame = example_records()
        for stages, bands in (
            ([], []),
            (["PDUFA Decision"], []),
            ([], ["0–30 DAYS"]),
        ):
            shown = chart_rows(filter_pipeline(frame, stages, bands))
            self.assertEqual(len(shown), 0)
            self.assertIn("Ticker", shown.columns)

    def test_exact_stage_and_window_show_12_not_15(self):
        frame = example_records()
        shown = chart_rows(filter_pipeline(
            frame, ["PDUFA Decision"], ["0–30 DAYS"]
        ))
        self.assertEqual(len(shown), 12)
        self.assertTrue(shown["Current Stage"].eq("PDUFA Decision").all())
        self.assertEqual(
            len(filter_pipeline(frame, ["FDA Acceptance"], ["0–30 DAYS"])),
            3,
        )

    def test_missing_dates_only_match_undated_band(self):
        frame = example_records()
        trials = chart_rows(filter_pipeline(
            frame, ["Phase 3"], ["NO PDUFA YET"]
        ))
        self.assertEqual(len(trials), 1)
        self.assertEqual(trials["NCT ID"].iloc[0], "NCT00000001")
        self.assertEqual(
            len(filter_pipeline(frame, ["Phase 3"], ["0–30 DAYS"])), 0
        )

    def test_row_count_and_stage_date_counts_identical(self):
        frame = example_records()
        selected = filter_pipeline(frame, ["PDUFA Decision", "FDA Acceptance"], ["0–30 DAYS"])
        result = chart_rows(selected)
        self.assertEqual(len(result), len(selected))
        self.assertEqual(sum(selected["current_stage"].value_counts()), len(result))
        self.assertEqual(sum(selected["DATES"].value_counts()), len(result))

    def test_stage_and_date_controls_are_both_present_above_chart(self):
        from pathlib import Path
        source = Path("app.py").read_text(encoding="utf-8")
        start = source.index('elif page == "PIPELINE":')
        end = source.index('elif page == "DISEASE & MARKET HORIZON":', start)
        section = source[start:end]
        self.assertIn('st.multiselect(\n            "STAGES"', section)
        self.assertIn('st.multiselect(\n            "DATES"', section)
        self.assertLess(section.index('selected_dates ='), section.index('### PIPELINE TRIALS / PROGRAMS'))
        self.assertLess(section.index('### PIPELINE TRIALS / PROGRAMS'), section.index('STAGES / DATES count audit'))
        self.assertIn('if not applied:', section)
        self.assertIn('empty_chart', section)


if __name__ == "__main__":
    unittest.main()
