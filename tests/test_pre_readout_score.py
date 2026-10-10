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
        "checked_at": "2026-10-10T08:00:00Z", "source_updated": "2026-10-09",
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
        "nct_id": "NCT12345678", "ticker": "TEST", "drug": "Candidate A",
        "indication": "Indication A", "assessment_cutoff_date": "2026-10-10",
        "issuer_readout_status": "VERIFIED_UNRELEASED",
        "issuer_readout_checked_at": "2026-10-10",
        "issuer_readout_source": "https://example.com/company/investors",
        "actual_topline_release_date": "",
        "phase2_nct_id": "NCT87654321",
        "phase2_primary_pvalue": "0.012",
        "phase2_primary_endpoint_met": "YES",
        "phase2_pvalue_source": "https://clinicaltrials.gov/study/NCT87654321",
        "phase2_pvalue_source_date": "2026-09-15",
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

    def test_phase2_p_is_mandatory_and_exact_trial_matched(self):
        for override in (
            {"phase2_primary_pvalue": ""},
            {"phase2_primary_pvalue": "1.5"},
            {"phase2_primary_endpoint_met": "NO"},
            {"phase2_nct_id": "NCT99999999"},
            {"phase2_pvalue_source_date": "2026-10-10"},
            {"phase2_pvalue_source_date": "2026-10-11"},
            {"phase2_pvalue_source": "not a source"},
        ):
            rated = assess(self.queue, pd.DataFrame([evidence(**override)]), self.as_of)
            self.assertTrue(pd.isna(rated.iloc[0]["Pre-Readout Evidence Points"]), override)
            self.assertTrue(pd.isna(rated.iloc[0]["Phase 3 Success Probability %"]))

    def test_result_date_or_late_source_blocks_score(self):
        after = assess(self.queue, pd.DataFrame([evidence(
            actual_topline_release_date="2026-10-09")]), self.as_of)
        self.assertTrue(pd.isna(after.iloc[0]["Pre-Readout Evidence Points"]))
        late = assess(self.queue, pd.DataFrame([evidence(
            phase2_efficacy_source_date="2026-10-11")]), self.as_of)
        self.assertTrue(pd.isna(late.iloc[0]["Pre-Readout Evidence Points"]))
        self.assertIn("phase2_efficacy", late.iloc[0]["Missing Evidence"])

    def test_date_only_same_day_efficacy_source_cannot_enter_pre_readout_score(self):
        rated = assess(self.queue, pd.DataFrame([evidence(
            phase2_efficacy_source_date="2026-10-10")]), self.as_of)
        self.assertTrue(pd.isna(rated.iloc[0]["Pre-Readout Evidence Points"]))
        self.assertTrue(pd.isna(rated.iloc[0]["Phase 3 Success Probability %"]))
        self.assertIn("same-day sources excluded", rated.iloc[0]["Missing Evidence"])

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

    def test_wrong_trial_identity_blocks_manual_research_score(self):
        for bad in ({"ticker": "OTHER"}, {"drug": "Other Drug"},
                    {"indication": "Other indication"}):
            result = assess(self.queue, pd.DataFrame([evidence(**bad)]), self.as_of)
            self.assertTrue(pd.isna(result.iloc[0]["Pre-Readout Evidence Points"]))
            self.assertIn("matching trial", result.iloc[0]["Missing Evidence"])

    def test_blank_export_template_never_invents_scores(self):
        frame = evidence_template(self.queue)
        self.assertEqual(len(frame), 1)
        self.assertEqual(list(frame.columns), EVIDENCE_COLUMNS)
        self.assertEqual(frame.iloc[0]["nct_id"], "NCT12345678")
        self.assertEqual(frame.iloc[0]["phase2_efficacy_points"], "")
        self.assertEqual(frame.iloc[0]["issuer_readout_status"], "")


    def test_future_trial_snapshot_cannot_be_backcast(self):
        old_caps = market()
        old_caps.loc[0, "market_cap_checked_at"] = "2026-10-01T10:00:00Z"
        current_snapshot = pd.DataFrame([trial(
            checked_at="2026-10-10", source_updated="2026-10-09",
        )])
        historical = candidate_queue(current_snapshot, pd.DataFrame(), old_caps,
                                     date(2026, 10, 8))
        self.assertTrue(historical.empty)
        historical_with_future_revision = candidate_queue(pd.DataFrame([trial(
            checked_at="2026-10-07", source_updated="2026-10-09",
        )]), pd.DataFrame(), old_caps, date(2026, 10, 8))
        self.assertTrue(historical_with_future_revision.empty)

    def test_issuer_check_must_be_current_to_score(self):
        rated = assess(self.queue, pd.DataFrame([evidence(
            issuer_readout_checked_at="2026-10-08",
        )]), self.as_of)
        self.assertTrue(pd.isna(rated.iloc[0]["Pre-Readout Evidence Points"]))
        self.assertIn("issuer check performed", rated.iloc[0]["Missing Evidence"])



    def test_protocol_revision_and_status_are_required_for_pre_readout_queue(self):
        base = pd.DataFrame([trial()])
        url = "https://clinicaltrials.gov/study/NCT12345678"
        valid = {
            "nct_id": "NCT12345678", "source_url": url,
            "checked_at": "2026-10-10T08:00:00Z",
            "source_updated": "2026-10-09",
            "registry_overall_status": "RECRUITING",
            "registry_results_first_posted": "",
        }
        for changes in (
            {"registry_overall_status": ""},
            {"registry_overall_status": "COMPLETED"},
            {"registry_overall_status": "TERMINATED"},
            {"registry_results_first_posted": "2026-10-09"},
            {"source_updated": "2026-10-11"},
            {"checked_at": "2026-10-11"},
            {"source_url": "https://example.com/unverified"},
        ):
            p = pd.DataFrame([{**valid, **changes}])
            q = candidate_queue(base, pd.DataFrame(), market(), self.as_of,
                                protocols=p)
            self.assertTrue(q.empty, f"Unsafe pre-readout protocol admitted: {changes}")
        admitted = candidate_queue(base, pd.DataFrame(), market(), self.as_of,
                                   protocols=pd.DataFrame([valid]))
        self.assertEqual(len(admitted), 1)
        self.assertTrue(pd.isna(admitted.iloc[0]["Phase 3 Success Probability %"]))

    def test_missing_exact_protocol_is_not_treated_as_verified_unreleased(self):
        foreign = pd.DataFrame([{
            "nct_id": "NCT87654321", "source_url": "https://clinicaltrials.gov/study/NCT87654321",
            "checked_at": "2026-10-10", "source_updated": "2026-10-09",
            "registry_overall_status": "RECRUITING", "registry_results_first_posted": "",
        }])
        self.assertTrue(candidate_queue(pd.DataFrame([trial()]), pd.DataFrame(),
                                        market(), self.as_of, protocols=foreign).empty)


    def test_explicitly_missing_protocol_ledger_fails_closed(self):
        q = candidate_queue(pd.DataFrame([trial()]), pd.DataFrame(),
                            market(), self.as_of, protocols=pd.DataFrame())
        self.assertTrue(q.empty)
        self.assertIn("Phase 3 Success Probability %", q.columns)

    def test_production_fails_closed_without_recent_matching_protocol(self):
        base = pd.DataFrame([trial()])
        protocol = {
            "nct_id": "NCT12345678",
            "source_url": "https://clinicaltrials.gov/study/NCT12345678",
            "checked_at": "2026-10-10T08:00:00Z",
            "source_updated": "2026-10-09",
            "registry_overall_status": "RECRUITING",
            "registry_results_first_posted": "",
        }
        self.assertTrue(candidate_queue(base, pd.DataFrame(), market(),
                         self.as_of, require_protocol=True).empty)
        self.assertTrue(candidate_queue(base, pd.DataFrame(), market(),
                         self.as_of, protocols=pd.DataFrame(),
                         require_protocol=True).empty)
        accepted = candidate_queue(base, pd.DataFrame(), market(),
                                   self.as_of, protocols=pd.DataFrame([protocol]),
                                   require_protocol=True)
        self.assertEqual(len(accepted), 1)
        self.assertTrue(pd.isna(accepted.iloc[0]["Phase 3 Success Probability %"]))
        for change in (
            {"checked_at": "2026-10-06"},
            {"registry_overall_status": "COMPLETED"},
            {"registry_results_first_posted": "2026-10-09"},
            {"source_url": "https://example.org/wrong"},
            {"nct_id": "NCT87654321"},
        ):
            unsafe = candidate_queue(base, pd.DataFrame(), market(),
                                     self.as_of,
                                     protocols=pd.DataFrame([{**protocol, **change}]),
                                     require_protocol=True)
            self.assertTrue(unsafe.empty, f"Unsafe protocol admitted: {change}")

    def test_pipeline_uses_fresh_protocol_gate(self):
        from pathlib import Path
        app = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        section = app.split("with pre_tab:", 1)[1].split("with intake_tab:", 1)[0]
        self.assertIn("protocols=_p3_protocols, require_protocol=True", section)
        self.assertLess(section.index('"data/pre_readout_protocols.csv"'),
                        section.index("phase3_pre_readout_queue("))


    def test_no_future_readout_date_in_historical_score(self):
        future = evidence(actual_topline_release_date="2026-10-11")
        scored = assess(self.queue, pd.DataFrame([future]), self.as_of)
        self.assertTrue(pd.isna(scored.iloc[0]["Pre-Readout Evidence Points"]))
        self.assertIn("outcome-era knowledge", scored.iloc[0]["Missing Evidence"])
        unknown = evidence(actual_topline_release_date="not-yet-confirmed")
        scored2 = assess(self.queue, pd.DataFrame([unknown]), self.as_of)
        self.assertTrue(pd.isna(scored2.iloc[0]["Pre-Readout Evidence Points"]))

    def test_pipeline_allows_only_in_session_strict_source_scoring(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        part = source.split("with pre_tab:", 1)[1].split("with intake_tab:", 1)[0]
        self.assertIn("pre_readout_evidence_upload_v1", part)
        self.assertIn("require_protocol=True", part)
        self.assertIn("_expected.issubset(_p3_import.columns)", part)
        self.assertIn("_p3_import[\"nct_id\"].astype(str).duplicated().any()", part)
        self.assertIn("Session-only evidence loaded.", part)



if __name__ == "__main__":
    unittest.main()
