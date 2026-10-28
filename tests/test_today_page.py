"""TODAY tab: date/source evidence and performance regressions."""
from supported_dashboard_checks import run_frontend_contract
import unittest
from pathlib import Path

import pandas as pd

from today_page import assemble


class TodayTabTests(unittest.TestCase):
    def test_assemble_keeps_source_linked_yesterday_record(self):
        live = pd.DataFrame([{
            "ticker": "TEST", "company": "Test Bio",
            "drug": "Example", "indication": "Condition A",
            "event_key": "TEST|EXAMPLE",
        }])
        posted = pd.DataFrame([{
            "ticker": "XYZ", "company": "Sample Therapeutics",
            "drug": "Candidate", "indication": "Condition B",
            "phase3_results_posted_at": "2026-10-09",
            "phase3_results_source": "https://clinicaltrials.gov/study/NCT12345678",
            "phase3_status": "RESULTS_REVIEW",
            "phase3_result": "Registry results posted; efficacy not adjudicated",
            "nct_id": "NCT12345678",
        }])
        result = assemble(live, posted, pd.DataFrame())
        self.assertEqual(set(result["Ticker"]), {"TEST", "XYZ"})
        row = result.loc[result["Ticker"].eq("XYZ")].iloc[0]
        self.assertEqual(row["Result Posted"].isoformat(), "2026-10-09")
        self.assertEqual(row["Research Status"], "SOURCE LINKED")
        self.assertEqual(row["FINANCING"], "REVIEW / UNVERIFIED")
        self.assertEqual(row["Source List"], "PHASE 3 PIPELINE")

    def test_duplicate_rows_do_not_duplicate_trial_records(self):
        row = {
            "ticker": "XYZ", "drug": "Candidate", "indication": "Condition B",
            "nct_id": "NCT12345678",
            "phase3_results_posted_at": "2026-10-09",
            "phase3_results_source": "https://clinicaltrials.gov/study/NCT12345678",
        }
        result = assemble(pd.DataFrame(), pd.DataFrame([row, row]), pd.DataFrame())
        self.assertEqual(len(result), 1)

    def test_today_has_only_one_ticker_picker_not_per_row_widgets(self):
        source = (Path(__file__).resolve().parents[1] /
                  "today_page.py").read_text(encoding="utf-8")
        self.assertNotIn("st.toggle(", source)
        self.assertNotIn("for row_num, (_, item) in enumerate(frame.iterrows())", source)
        self.assertIn('key="today_watchlist_ticker_v2"', source)
        self.assertIn('key="today_watch_add_v2"', source)
        self.assertIn('key="today_watch_remove_v2"', source)
        self.assertIn('bottom = bottom.sort_values("Result Posted"', source)

    def test_result_sources_are_not_labeled_as_positive_outcomes(self):
        source = (Path(__file__).resolve().parents[1] /
                  "today_page.py").read_text(encoding="utf-8")
        self.assertIn("a source link is not proof of a positive primary endpoint", source)

    def test_supported_published_results_keep_exact_trial_sources_and_no_inferred_outcome(self):
        """Retained product contract, executed against supported Next.js code."""
        self.assertGreater(run_frontend_contract('scans-new-results.test.cjs'), 0)
        self.assertGreater(run_frontend_contract('candidate-assessments.test.cjs'), 0)

    def test_phase3_collector_and_data_preserved_but_old_schedule_removed(self):
        root = Path(__file__).resolve().parents[1]
        # Scanner code and historical evidence survive, but the workflow
        # schedule was removed by explicit request and must not be restarted.
        self.assertFalse((root / ".github/workflows/phase3-results-intake.yml").exists())
        self.assertTrue((root / "scripts/phase3_results_intake.py").exists())
        self.assertTrue((root / "scripts/phase3_drug_identity.py").exists())
        self.assertTrue((root / "data/phase3_announcements.csv").exists())
        self.assertTrue((root / "data/second_financing_status.csv").exists())


if __name__ == "__main__":
    unittest.main()

