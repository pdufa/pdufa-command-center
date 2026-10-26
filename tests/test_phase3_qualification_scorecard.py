"""Exact denominator tests for research-only MAIN nine-gate Phase 3 scorecard."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from phase3_qualification_scorecard import build_scorecard, render_markdown
from phase3_rights_review_submissions import build_review_coverage
from phase3_rights_review_worklist import build_worklist
import test_phase3_rights_review_worklist as original_fixture


class MainQualificationScorecardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fx = original_fixture.Phase3RightsWorklistTests()
        fx.setUp()
        worklist = build_worklist(fx.registry, fx.ledger, fx.casebook,
                                  fx.leads, fx.join)
        review = build_review_coverage(worklist, [])
        fx.program["trials_with_provisional_drug_or_biologic_mentions"] = sum(
            bool(r["provisional_drug_or_biologic_names"]) for r in fx.program["items"])
        fx.leads["issuer_metadata_fetched"] = 130
        fx.leads["issuer_metadata_unavailable_or_invalid"] = 0
        cls.fixture = (fx.ledger, fx.program, fx.leads, fx.pilot, worklist, review)

    def setUp(self):
        self.sources = copy.deepcopy(self.fixture)

    def build(self):
        return build_scorecard(*self.sources)

    def test_expected_gate_denominators_and_rights_completions(self):
        r = self.build()
        self.assertEqual(r["gate_checks_denominator"], 6669)
        self.assertEqual(r["gate_checks_pass"], 741)
        self.assertEqual(r["gate_checks_review"], 5928)
        self.assertEqual(r["gate_checks_fail"], 0)
        self.assertEqual(len(r["per_gate"]), 9)
        self.assertEqual(r["trials_by_unresolved_gate_count"]["8"], 741)
        self.assertEqual(r["rights_review_checklist_slots"], 4446)
        self.assertEqual(r["rights_slots_with_submissions"], 0)
        self.assertEqual(r["rights_slots_without_submissions"], 4446)
        self.assertEqual(r["trials_with_any_submissions"], 0)
        self.assertEqual(r["independently_verified_current_rights_trials"], 0)
        self.assertIsNone(r["qualified_trial_count"])

    def test_research_progress_not_pipeline_qualification(self):
        r = self.build()
        self.assertEqual(r["historical_trial_count"], 741)
        self.assertEqual(r["issuer_research_pointer_count"], 130)
        self.assertEqual(r["trials_with_provisional_registered_drug"], 494)
        self.assertEqual(r["trials_without_provisional_registered_drug"], 247)
        self.assertEqual(r["sec_issuer_indexes_fetched"], 130)
        self.assertEqual(r["sec_primary_documents_selected"], 4)
        self.assertEqual(r["sec_primary_documents_attempted"], 4)
        self.assertEqual(r["sec_primary_documents_fetched"], 4)
        self.assertEqual(r["trial_issuer_text_available"], 12)
        self.assertIsNone(r["qualifying_pipeline_count"])

    def test_collapsible_secondary_gates_and_progress_table(self):
        md = render_markdown(self.build())
        self.assertIn("741/741", md)
        self.assertIn("741/6669", md)
        self.assertIn("5928/6669", md)
        self.assertIn("0/4446", md)
        self.assertIn("**UNKNOWN** (not zero)", md)
        self.assertIn("<details><summary>All nine mandatory gates", md)
        self.assertIn("<details><summary>Secondary rights source/reviewer coverage", md)
        self.assertIn("current_commercial_rights", md)

    def test_missing_trial_in_ledger_fails_closed(self):
        self.sources[0]["records"].pop()
        with self.assertRaises(ValueError):
            self.build()

    def test_duplicate_nct_in_review_evidence_fails_closed(self):
        self.sources[5]["items"][0]["nct_id"] = "NCT00000002"
        with self.assertRaises(ValueError):
            self.build()

    def test_cross_ticker_or_cik_mismatch_fails_closed(self):
        for idx, field, value in ((1, "ticker", "WRONG"),
                                   (2, "saved_sec_cik", "0000000909")):
            with self.subTest(field=field):
                sources = copy.deepcopy(self.sources)
                if idx == 1:
                    sources[1]["items"][0][field] = value
                else:
                    sources[2]["trials"][0][field] = value
                with self.assertRaises(ValueError):
                    build_scorecard(*sources)

    def test_manually_asserted_qualifying_trial_rejected(self):
        self.sources[0]["records"][0]["qualified_pipeline"] = True
        with self.assertRaises(ValueError):
            self.build()

    def test_forced_independent_commercial_rights_rejected(self):
        self.sources[5]["items"][0]["commercial_rights_verified"] = True
        with self.assertRaises(ValueError):
            self.build()

    def test_fabricated_review_gate_pass_rejected(self):
        self.sources[0]["records"][0]["gates"]["current_commercial_rights"] = "PASS"
        with self.assertRaises(ValueError):
            self.build()

    def test_issuer_metadata_fetched_denominator_rejected(self):
        self.sources[2]["issuer_metadata_fetched"] = 131
        with self.assertRaises(ValueError):
            self.build()

    def test_primary_document_attempts_must_reconcile(self):
        self.sources[3]["documents_attempted"] = 12
        with self.assertRaises(ValueError):
            self.build()

    def test_submissions_must_add_to_4446(self):
        self.sources[5]["distinct_review_slots_with_submissions"] = 1
        with self.assertRaises(ValueError):
            self.build()

    def test_review_slots_cannot_count_more_reviewer_reports_than_submissions(self):
        self.sources[5]["review_slots_with_reviewer_reported_findings"] = 1
        with self.assertRaises(ValueError):
            self.build()

    def test_registry_named_drug_count_must_match_741_rows(self):
        self.sources[1]["trials_with_provisional_drug_or_biologic_mentions"] = 741
        with self.assertRaises(ValueError):
            self.build()

    def test_worklist_rights_status_cannot_be_promoted(self):
        self.sources[4]["items"][0]["qualified_pipeline"] = False
        with self.assertRaises(ValueError):
            self.build()

    def test_status_issues_are_explicit_not_a_fictitious_success_probability(self):
        r = self.build()
        self.assertNotIn("approval_probability", r)
        self.assertIsNone(r["qualified_trial_count"])
        self.assertTrue(r["blockers"])
        self.assertEqual(sum(r["source_review_priority_counts"].values()), 741)


if __name__ == "__main__":
    unittest.main()
