from datetime import date
import unittest

import pandas as pd

from stages import StageIndex, add_stage_column, program_stage

TODAY = date(2026, 10, 7)


def program(**changes):
    return {
        "ticker": "TEST", "drug": "Drug A", "indication": "Disease A", "event_key": "TEST|DRUG_A",
        "pdufa_date": "2026-10-17", "pdufa_confirmation": "VERIFIED", "pdufa_evidence_url": "https://issuer.test/pdufa",
        "last_checked": "2026-10-06T15:00:00Z", "conflict_flag": "NONE", **changes,
    }


class StageTests(unittest.TestCase):
    def test_closed_financing_does_not_mean_currently_in_progress(self):
        row = program(second_financing_status="CLOSED", second_financing_running="YES", second_financing_closed="YES",
                      second_financing_audit_status="VERIFIED_SECOND_POST_PHASE3_FINANCING", second_financing_source="https://sec.test/close",
                      second_financing_date="2026-09-15", verified_as_of="2026-10-05")
        stage = program_stage(row, TODAY)
        self.assertEqual(stage, "2ND FINANCING CLOSED · PDUFA / FDA REVIEW")
        self.assertNotIn("IN PROGRESS", stage)

    def test_active_financing_requires_fresh_verified_evidence(self):
        row = program(second_financing_status="IN_PROGRESS", second_financing_audit_status="VERIFIED_FINANCING_IN_PROGRESS",
                      second_financing_source="https://sec.test/offering", verified_as_of="2026-10-06")
        self.assertIn("FINANCING IN PROGRESS", program_stage(row, TODAY))
        self.assertIn("FINANCING STATUS — REVIEW", program_stage({**row, "verified_as_of": "2026-09-01"}, TODAY))
        self.assertIn("FINANCING STATUS — REVIEW", program_stage({**row, "second_financing_source": ""}, TODAY))

    def test_completed_phase3_is_results_review_without_success_claim(self):
        row = program(pdufa_date="", phases="PHASE3", trial_status="COMPLETED", promotion_status="VERIFIED")
        self.assertEqual(program_stage(row, TODAY), "PHASE 3 COMPLETED — RESULTS REVIEW")

    def test_manual_and_combined_phase2_keep_review_labels(self):
        self.assertEqual(program_stage(program(pdufa_date="", current_stage="PHASE 2 — MANUAL REVIEW"), TODAY), "PHASE 2 — MANUAL REVIEW")
        self.assertEqual(program_stage(program(pdufa_date="", phases="PHASE2|PHASE3"), TODAY), "PHASE 2/3 — REVIEW")

    def test_predictions_and_elapsed_dates_are_not_observed_fda_decisions(self):
        self.assertEqual(program_stage(program(pdufa_date="2026-10-01", fda_prediction="APPROVED"), TODAY), "FDA DECISION PENDING — REVIEW")
        self.assertNotEqual(program_stage(program(decision_date="2026-10-17"), TODAY), "FDA APPROVED")
        self.assertEqual(program_stage(program(pdufa_date="2020-10-01", actual_outcome="CRL"), TODAY), "FDA CRL")

    def test_conflicting_regulatory_evidence_stays_review(self):
        self.assertEqual(program_stage(program(conflict_flag="CONFLICT"), TODAY), "PDUFA / FDA REVIEW — EVIDENCE REVIEW")

    def test_ticker_alone_cannot_choose_between_programs(self):
        index = StageIndex([program(), program(drug="Drug B", event_key="TEST|DRUG_B", pdufa_date="2026-11-01")], TODAY)
        self.assertEqual(index.resolve({"Ticker": "TEST"}), "MULTIPLE PROGRAMS — REVIEW")
        self.assertTrue(pd.isna(index.countdown({"Ticker": "TEST"})))
        self.assertEqual(index.resolve({"Ticker": "TEST", "Drug": "Drug A"}), "PDUFA / FDA REVIEW")
        self.assertEqual(index.countdown({"Ticker": "TEST", "Drug": "Drug A"}), 10)

    def test_adjacent_columns_keep_filtered_indices_and_blank_undated_countdowns(self):
        frame = pd.DataFrame([{"Ticker": "TEST", "Drug": "Drug A", "PDUFA Date": "2026-10-17"},
                              {"Ticker": "OTHER", "Drug": "Drug B", "PDUFA Date": ""}], index=[42, 91])
        result = add_stage_column(frame, StageIndex([program()], TODAY))
        self.assertEqual(list(result.columns)[:3], ["Ticker", "STAGE", "DAYS TO PDUFA"])
        self.assertEqual(list(result.index), [42, 91])
        self.assertEqual(result.loc[42, "DAYS TO PDUFA"], 10)
        self.assertTrue(pd.isna(result.loc[91, "DAYS TO PDUFA"]))

    def test_source_context_does_not_borrow_an_unrelated_pdufa(self):
        source = program(pdufa_date="", phases="PHASE2", promotion_status="AWAITING_PHASE3")
        result = add_stage_column(pd.DataFrame([{"Ticker": "TEST", "Drug": "Drug A"}]), StageIndex([program()], TODAY), source)
        self.assertEqual(result.iloc[0]["STAGE"], "PHASE 2 ONGOING")
        self.assertTrue(pd.isna(result.iloc[0]["DAYS TO PDUFA"]))

    def test_negative_countdown_means_date_passed(self):
        self.assertEqual(StageIndex([], TODAY).countdown({"Ticker": "TEST", "PDUFA Date": "2026-10-05"}), -2)


if __name__ == "__main__":
    unittest.main()
