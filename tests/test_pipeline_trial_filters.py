import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from pipeline_trial_filters import (
    DEFAULTS, add_public_filter_columns, filter_public_trials,
    selection_signature, has_active_filter,
)


AS_OF = date(2026, 10, 18)


def sample():
    return pd.DataFrame([
        dict(record_id="APPLICATION|AAA|DRUG_A_20270101", ticker="AAA",
             stage_tags=("Phase 3 Results", "PDUFA Decision"),
             registered_phase="", status="", drug_modality="",
             indication="Melanoma", primary_completion="",
             study_completion="", results_posted="",
             fda_acceptance_date="2026-10-20", pdufa_date="2027-01-01"),
        dict(record_id="TRIAL|NCT12345678", ticker="AAA",
             stage_tags=("Phase 3 Results",), registered_phase="Phase 3",
             status="COMPLETED", drug_modality="Biologic / biological (registry)",
             indication="Melanoma", primary_completion="2026-10-29",
             study_completion="2026-11-30", results_posted="2026-10-01",
             fda_acceptance_date="", pdufa_date=""),
        dict(record_id="TRIAL|NCT87654321", ticker="BBB",
             stage_tags=("Phase 3",), registered_phase="Phase 3",
             status="RECRUITING", drug_modality="Drug (registry)",
             indication="Lung cancer", primary_completion="",
             study_completion="", results_posted="",
             fda_acceptance_date="", pdufa_date=""),
    ])


def settings(**changes):
    return dict(DEFAULTS, **changes)


class PublicPipelineFiltersTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        pd.DataFrame([
            {"ticker": "AAA", "market_cap": "750000000",
             "market_cap_status": "VERIFIED"},
            {"ticker": "BBB", "market_cap": "990000000",
             "market_cap_status": "NOT_VERIFIED"},
        ]).to_csv(self.root / "phase_pipeline_market_caps.csv", index=False)
        pd.DataFrame([
            {"ticker": "AAA", "market_status": "MARKET_UPDATED",
             "last_session": "2026-10-16", "last_close_usd": "12.5"},
            {"ticker": "BBB", "market_status": "MARKET_UPDATED",
             "last_session": "2026-08-01", "last_close_usd": "3.2"},
        ]).to_csv(self.root / "step7_market_status.csv", index=False)
        pd.DataFrame([
            {"event_key": "AAA|DRUG_A_20270101",
             "shares_float": "25000000", "cash": "80000000"}
        ]).to_csv(self.root / "pdufa_candidates.csv", index=False)
        pd.DataFrame([
            {"event_key": "AAA|DRUG_A_20270101",
             "second_financing_closed": "YES",
             "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
             "second_financing_source": "https://www.sec.gov/Archives/a"},
            {"event_key": "BBB|DRUG_B",
             "second_financing_closed": "YES",
             "second_financing_audit_status": "REVIEW",
             "second_financing_source": "https://www.sec.gov/Archives/b"},
        ]).to_csv(self.root / "second_financing_status.csv", index=False)
        self.frame = add_public_filter_columns(sample(), self.root, AS_OF)

    def test_no_trial_filter_changes_universe(self):
        self.assertFalse(has_active_filter(DEFAULTS))
        self.assertEqual(len(filter_public_trials(self.frame, DEFAULTS, AS_OF)), 3)
        self.assertEqual(len(self.frame), 3)

    def test_financing_requires_exact_application(self):
        found = filter_public_trials(
            self.frame,
            settings(pipeline_trial_financing_v1="Verified second financing closed"),
            AS_OF,
        )
        self.assertEqual(found["record_id"].tolist(),
                         ["APPLICATION|AAA|DRUG_A_20270101"])
        self.assertFalse(
            bool(self.frame.loc[self.frame["record_id"].eq("TRIAL|NCT12345678"),
                                "filter_second_financing_verified"].iloc[0])
        )

    def test_sourced_results_and_financing_and(self):
        found = filter_public_trials(self.frame, settings(
            pipeline_trial_results_v1="Sourced Phase 3 results",
            pipeline_trial_financing_v1="Verified second financing closed",
        ), AS_OF)
        self.assertEqual(found["record_id"].tolist(),
                         ["APPLICATION|AAA|DRUG_A_20270101"])

    def test_market_caps_reject_unverified_and_stale_price(self):
        cap = filter_public_trials(
            self.frame, settings(pipeline_trial_market_cap_v1="$300M–$10B"), AS_OF)
        self.assertEqual(len(cap), 2)  # AAA app and AAA registered trial
        self.assertEqual(self.frame["filter_price_usd"].notna().sum(), 2)
        price = filter_public_trials(
            self.frame, settings(pipeline_trial_price_v1="$5–$20"), AS_OF)
        self.assertEqual(len(price), 2)

    def test_float_and_cash_are_exact_application_values(self):
        found = filter_public_trials(
            self.frame, settings(pipeline_trial_float_v1="20M–100M",
                                 pipeline_trial_cash_v1="$50M–$200M"), AS_OF)
        self.assertEqual(found["record_id"].tolist(),
                         ["APPLICATION|AAA|DRUG_A_20270101"])

    def test_clinical_and_date_windows(self):
        found = filter_public_trials(self.frame, settings(
            pipeline_trial_phases_v1=["Phase 3"],
            pipeline_trial_statuses_v1=["COMPLETED"],
            pipeline_trial_indication_v1="melanoma",
            pipeline_trial_modalities_v1=["Biologic"],
            pipeline_trial_milestone_v1="Primary completion",
            pipeline_trial_window_v1="Next 30 days",
        ), AS_OF)
        self.assertEqual(found["record_id"].tolist(), ["TRIAL|NCT12345678"])

    def test_missing_unavailable_metrics_fail_closed(self):
        found = filter_public_trials(
            self.frame, settings(pipeline_trial_insider_v1="20%+"), AS_OF)
        self.assertTrue(found.empty)
        self.assertTrue(self.frame["filter_runway_months"].isna().all())

    def test_signature_changes_and_reset_defaults(self):
        a = selection_signature({})
        b = selection_signature(settings(pipeline_trial_indication_v1="melanoma"))
        self.assertNotEqual(a, b)
        self.assertEqual(a, selection_signature(DEFAULTS))

    def test_missing_files_leave_data_unverified(self):
        with tempfile.TemporaryDirectory() as folder:
            clean = add_public_filter_columns(sample(), folder, AS_OF)
            self.assertTrue(clean["filter_market_cap_usd"].isna().all())
            self.assertFalse(clean["filter_second_financing_verified"].any())
            self.assertEqual(len(clean), 3)


if __name__ == "__main__":
    unittest.main()
