"""Pre-release trial-scoring gates: no outcome leakage or fabricated PoS."""
import unittest
from datetime import date
import pandas as pd

from pre_readout_score import (
    candidate_queue, assess, evidence_template, EVIDENCE_COLUMNS, WEIGHTS,
)


def trial(**overrides):
    row = {
        "nct_id": "NCT12345678", "ticker": "TEST", "company": "Test Bio",
        "drug": "Candidate A", "indication": "Indication A",
        "phases": "PHASE3", "trial_status": "RECRUITING",
        "results_first_posted": "", "source_url": "https://clinicaltrials.gov/study/NCT12345678",
        "primary_completion": "2027-03-01", "primary_completion_type": "ESTIMATED",
        "program_identity_status": "VERIFIED", "phase2_nct_ids": "NCT87654321",
    }
    row.update(overrides)
    return row


def market():
    return pd.DataFrame([{
        "ticker": "TEST", "market_cap": "1200000000",
        "market_cap_status": "VERIFIED",
        "market_cap_checked_at": "2026-10-09T09:00:00Z",
    }])


def evidence(**overrides):
    row = {
        "nct_id": "NCT12345678", "assessment_cutoff_date": "2026-10-10",
        "issuer_readout_status": "VERIFIED_UNRELEASED",
        "issuer_readout_checked_at": "2026-10-10",
        "issuer_readout_source": "https://example.com/company/investors",
        "actual_topline_release_date": "",
    }
    for key, weight in WEIGHTS.items():
        row[f"{key}_points"] = str(weight)
        row[f"{key}_source"] = "https://example.com/evidence/" + key
        row[f"{key}_source_date"] = "2026-10-09"
    row.update(overrides)
    return row


class PreReadoutTests(unittest.TestCase):
    def setUp(self):
        self.as_of = date(2026, 10, 10)
        self.queue = candidate_queue(pd.DataFrame([trial()]), pd.DataFrame(),
                                     market(), self.as_of)

    def test_future_pre_readout_candidate_is_unscored_and_probability_blank(self):
        self.assertEqual(len(self.queue), 1)
        self.assertEqual(self.queue.iloc[0]["Assessment Status"],
                         "NOT SCORED — BEFORE-READOUT EVIDENCE INCOMPLETE")
        self.assertTrue(pd.isna(self.queue.iloc[0]["Phase 3 Success Probability %"]))
        self.assertTrue(pd.isna(self.queue.iloc[0]["Pre-Readout Evidence Points"]))

    def test_no_posted_phase3_results_in_queue(self):
        a = pd.DataFrame([trial(results_first_posted="2026-10-09")])
        self.assertTrue(candidate_queue(a, pd.DataFrame(), market(), self.as_of).empty)
        registry = pd.DataFrame([{
            "nct_id": "NCT12345678", "phase3_results_posted_at": "2026-10-08",
        }])
        self.assertTrue(candidate_queue(pd.DataFrame([trial()]), registry,
                                        market(), self.as_of).empty)

    def test_excludes_finished_or_out_of_range_and_unverified_cap(self):
        self.assertTrue(candidate_queue(pd.DataFrame([trial(trial_status="TERMINATED")]),
                                        pd.DataFrame(), market(), self.as_of).empty)
        low = market()
        low.loc[0, "market_cap"] = "299999999"
        self.assertTrue(candidate_queue(pd.DataFrame([trial()]), pd.DataFrame(),
                                        low, self.as_of).empty)
        high = market()
        high.loc[0, "market_cap"] = "10000000001"
        self.assertTrue(candidate_queue(pd.DataFrame([trial()]), pd.DataFrame(),
                                        high, self.as_of).empty)
        unverified = market()
        unverified.loc[0, "market_cap_status"] = "REVIEW"
        self.assertTrue(candidate_queue(pd.DataFrame([trial()]), pd.DataFrame(),
                                        unverified, self.as_of).empty)

    def test_older_cutoff_rejects_future_market_data(self):
        self.assertTrue(candidate_queue(pd.DataFrame([trial()]), pd.DataFrame(),
                                        market(), "2026-10-01").empty)

    def test_research_points_are_distinct_from_calibrated_success_probability(self):
        rated = assess(self.queue, pd.DataFrame([evidence()]), self.as_of)
        self.assertEqual(float(rated.iloc[0]["Pre-Readout Evidence Points"]), 100.0)
        self.assertTrue(pd.isna(rated.iloc[0]["Phase 3 Success Probability %"]))
        self.assertEqual(rated.iloc[0]["Assessment Status"],
                         "100-POINT RESEARCH SCORE — UNCALIBRATED")

    def test_result_date_or_late_source_blocks_score(self):
        after = assess(self.queue, pd.DataFrame([evidence(
            actual_topline_release_date="2026-10-09")]), self.as_of)
        self.assertTrue(pd.isna(after.iloc[0]["Pre-Readout Evidence Points"]))
        late = assess(self.queue, pd.DataFrame([evidence(
            phase2_efficacy_source_date="2026-10-11")]), self.as_of)
        self.assertTrue(pd.isna(late.iloc[0]["Pre-Readout Evidence Points"]))
        self.assertIn("phase2_efficacy", late.iloc[0]["Missing Evidence"])

    def test_readout_source_and_cutoff_are_mandatory(self):
        unknown = assess(self.queue, pd.DataFrame([evidence(
            issuer_readout_status="UNVERIFIED")]), self.as_of)
        self.assertTrue(pd.isna(unknown.iloc[0]["Pre-Readout Evidence Points"]))
        moved = assess(self.queue, pd.DataFrame([evidence(
            assessment_cutoff_date="2026-10-09")]), self.as_of)
        self.assertTrue(pd.isna(moved.iloc[0]["Pre-Readout Evidence Points"]))

    def test_score_requires_all_evidence_and_valid_weight_ranges(self):
        partial = assess(self.queue, pd.DataFrame([evidence(
            regulatory_alignment_points="")]), self.as_of)
        self.assertTrue(pd.isna(partial.iloc[0]["Pre-Readout Evidence Points"]))
        out_of_bounds = assess(self.queue, pd.DataFrame([evidence(
            phase3_design_points="31")]), self.as_of)
        self.assertTrue(pd.isna(out_of_bounds.iloc[0]["Pre-Readout Evidence Points"]))
        self.assertEqual(sum(WEIGHTS.values()), 100)

    def test_blank_export_template_never_invents_scores(self):
        frame = evidence_template(self.queue)
        self.assertEqual(len(frame), 1)
        self.assertEqual(list(frame.columns), EVIDENCE_COLUMNS)
        self.assertEqual(frame.iloc[0]["nct_id"], "NCT12345678")
        self.assertEqual(frame.iloc[0]["phase2_efficacy_points"], "")
        self.assertEqual(frame.iloc[0]["issuer_readout_status"], "")


if __name__ == "__main__":
    unittest.main()
