"""Run chart-indicator research sheet's original invariants in the standard CI unittest suite.

Original test_chart_indicator_sheet.py uses pytest-style functions; the existing
CI runner uses unittest discovery, which otherwise silently skips those tests.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path


def _cases():
    source = Path(__file__).with_name("test_chart_indicator_sheet.py")
    spec = importlib.util.spec_from_file_location("chart_indicator_sheet_cases", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ChartIndicatorSheetTests(unittest.TestCase):
    def test_exact_program_identity_stage_lineage_and_trade_safety(self):
        with tempfile.TemporaryDirectory() as directory:
            _cases().test_program_identity_and_wt_tags_are_not_trade_authorization(
                Path(directory)
            )

    def test_inactive_stage_and_unverified_market_cap_cannot_promote(self):
        with tempfile.TemporaryDirectory() as directory:
            _cases().test_unverified_market_cap_and_inactive_stage_do_not_promote(
                Path(directory)
            )

    def test_timestamp_from_streamlit_day_does_not_crash_catalyst_delta(self):
        import pandas as pd
        from chart_indicator_sheet import build_chart_indicator_rows
        _csv = _cases()._csv
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _csv(root / "pdufa_candidates.csv", [
                {"event_key": "XYZ|DRUG", "ticker": "XYZ",
                 "drug": "therapy", "pdufa_date": "2026-12-01"},
            ])
            rows = build_chart_indicator_rows(root, pd.Timestamp("2026-10-16"))
            self.assertEqual(len(rows), 1)
            self.assertIn("+46 days", rows[0]["Priority 8 — PDUFA / catalyst"])

    def test_all_indicators_have_adjoining_reference_targets(self):
        _cases().test_every_indicated_metric_has_an_adjacent_target()


if __name__ == "__main__":
    unittest.main()
