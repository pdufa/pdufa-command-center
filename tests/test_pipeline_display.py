from supported_dashboard_checks import run_frontend_contract
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
    def test_cleared_dimensions_are_unrestricted_without_scalar_boolean_indexing(self):
        frame = example_records()
        original = frame.copy(deep=True)
        for stages, bands, expected in (
            ([], [], 16),
            (["PDUFA Decision"], [], 12),
            ([], ["0–30 DAYS"], 15),
            (["not a recorded stage"], [], 0),
        ):
            with self.subTest(stages=stages, bands=bands):
                shown = chart_rows(filter_pipeline(frame, stages, bands))
                self.assertEqual(len(shown), expected)
                self.assertIn("Ticker", shown.columns)
        pd.testing.assert_frame_equal(frame, original)

    def test_cleared_filters_keep_custom_indexes_and_literal_query_scope(self):
        frame = example_records()
        frame.index = ["exact-" + str(i) for i in range(len(frame))]
        filtered = filter_pipeline(frame, [], [], query="Company 15")
        self.assertEqual(filtered.index.tolist(), ["exact-15"])
        self.assertEqual(filtered.iloc[0]["nct_id"], "NCT00000001")
        self.assertEqual(len(filter_pipeline(frame, [], [], query="[not a regex]")), 0)

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

    def test_supported_stage_and_date_filters_preserve_exact_counts(self):
        """Retained product contract, executed against supported Next.js code."""
        self.assertGreater(run_frontend_contract('trial-filters.test.cjs'), 0)
        self.assertGreater(run_frontend_contract('pipeline-data.test.cjs'), 0)

    def test_supported_workspace_preserves_trial_pages_and_research_only_wt(self):
        """Retained product contract, executed against supported Next.js code."""
        self.assertGreater(run_frontend_contract('workspace-pages.test.cjs'), 0)
        self.assertGreater(run_frontend_contract('wt-entry-stay-exit.test.cjs'), 0)

    def test_supported_central_restrictions_keep_original_filters_and_presets(self):
        """Retained product contract, executed against supported Next.js code."""
        self.assertGreater(run_frontend_contract('restrictions-central-placement.test.cjs'), 0)



if __name__ == "__main__":
    unittest.main()
