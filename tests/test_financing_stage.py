"""Second-financing stage qualification and table-column integration."""
from datetime import date
import unittest

import pandas as pd

from financing_stage import FINANCING_OPTIONS, add_financing_column, financing_stage
from stages import StageIndex


TODAY = date(2026, 10, 7)


def financing_row(**changes):
    row = {
        "ticker": "TEST", "drug": "Drug A", "indication": "Disease A",
        "event_key": "TEST|DRUG_A", "second_financing_status": "",
        "second_financing_source": "https://www.sec.gov/Archives/edgar/data/123/test",
        "second_financing_audit_status": "VERIFIED_FINANCING_IN_PROGRESS",
        "verified_as_of": "2026-10-06", "second_financing_date": "",
    }
    row.update(changes)
    return row


class FinancingStageTests(unittest.TestCase):
    def test_all_four_phases_require_specific_status_evidence(self):
        self.assertEqual(financing_stage(financing_row(second_financing_status="ANNOUNCED"), TODAY), "ANNOUNCED")
        self.assertEqual(financing_stage(financing_row(second_financing_status="STARTED"), TODAY), "STARTED")
        self.assertEqual(financing_stage(financing_row(second_financing_status="RUNNING"), TODAY), "RUNNING")
        self.assertEqual(financing_stage(financing_row(
            second_financing_status="CLOSED",
            second_financing_audit_status="VERIFIED_SECOND_POST_PHASE3_FINANCING",
            second_financing_date="2026-10-03"), TODAY), "FINISHED")
        self.assertEqual(len(FINANCING_OPTIONS), 5)

    def test_closure_overrides_prior_running_milestones(self):
        row = financing_row(second_financing_status="CLOSED",
                            second_financing_running="YES", second_financing_closed="YES",
                            second_financing_audit_status="VERIFIED_SECOND_POST_PHASE3_FINANCING",
                            second_financing_date="2026-10-03")
        self.assertEqual(financing_stage(row, TODAY), "FINISHED")

    def test_unverified_missing_source_and_stale_active_stay_review(self):
        for row in [
            financing_row(second_financing_status="ANNOUNCED", second_financing_source=""),
            financing_row(second_financing_status="STARTED", verified_as_of="2026-09-01"),
            financing_row(second_financing_status="RUNNING", second_financing_audit_status=""),
            financing_row(second_financing_status="CLOSED",
                          second_financing_audit_status="VERIFIED_SECOND_POST_PHASE3_FINANCING",
                          second_financing_date=""),
            financing_row(second_financing_status=""),
        ]:
            self.assertEqual(financing_stage(row, TODAY), "REVIEW / UNVERIFIED")

    def test_historical_verified_close_remains_finished(self):
        row = financing_row(second_financing_status="CLOSED",
                            second_financing_audit_status="VERIFIED_SECOND_POST_PHASE3_FINANCING",
                            second_financing_date="2025-10-03",
                            verified_as_of="2026-09-01")
        self.assertEqual(financing_stage(row, TODAY), "FINISHED")

    def test_exact_identity_only_and_index_preserved(self):
        known = financing_row(second_financing_status="RUNNING")
        other = financing_row(drug="Drug B", event_key="TEST|DRUG_B",
                              second_financing_status="ANNOUNCED")
        index = StageIndex([known, other], TODAY)
        frame = pd.DataFrame([
            {"Ticker": "TEST", "Drug": "Drug A", "STAGE": "PHASE 3 ONGOING", "DAYS TO PDUFA": pd.NA},
            {"Ticker": "TEST", "Drug": "Drug B", "STAGE": "PHASE 3 ONGOING", "DAYS TO PDUFA": pd.NA},
            {"Ticker": "TEST", "STAGE": "STAGE UNKNOWN — REVIEW", "DAYS TO PDUFA": pd.NA},
        ], index=[42, 8, 109])
        result = add_financing_column(frame, index)
        self.assertEqual(result["FINANCING"].tolist(),
                         ["RUNNING", "ANNOUNCED", "REVIEW / UNVERIFIED"])
        self.assertEqual(result.index.tolist(), [42, 8, 109])
        self.assertEqual(result.columns.tolist()[:4],
                         ["Ticker", "STAGE", "DAYS TO PDUFA", "FINANCING"])


if __name__ == "__main__":
    unittest.main()
