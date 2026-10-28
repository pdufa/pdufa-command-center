"""Unit tests for candidate cohort audit."""
import unittest
from research.fda_candidate_audit import audit_candidates


class CandidateAuditTests(unittest.TestCase):
    def test_empty_cohort_never_reports_approval_rate(self):
        result = audit_candidates([])
        self.assertEqual(result["total_candidates"], 0)
        self.assertIsNone(result["approval_rate"])
        self.assertFalse(result["validated_training_cohort"])

    def test_candidate_union_abstains_even_with_approval_action(self):
        record = {
            "action_type": "approval",
            "official_fda_action_source": "FDA action letter",
            "application_id": "NDA-TEST",
            "review_cycle_id": "cycle-1",
            "action_date": "2025-06-01",
            "evidence_cutoff_date": "2025-05-31",
            "source_cohort": "candidate_union",
            "original_filing_denominator_verified": False,
            "program_family_disjoint_verified": True,
        }
        result = audit_candidates([record, record])
        self.assertEqual(result["total_candidates"], 2)
        self.assertEqual(result["abstained"], 2)
        self.assertEqual(result["eligible_for_further_review"], 0)
        self.assertIn("candidate_union_not_representative", result["abstention_reasons"])
        self.assertIsNone(result["approval_rate"])

    def test_duplicate_review_cycle_abstains(self):
        record = {
            "action_type": "approval",
            "official_fda_action_source": "https://www.fda.gov/example",
            "application_id": "NDA-TEST",
            "review_cycle_id": "cycle-1",
            "action_date": "2025-06-01",
            "evidence_cutoff_date": "2025-05-31",
            "source_cohort": "complete_original_filing_population",
            "original_filing_denominator_verified": True,
            "program_family_disjoint_verified": True,
        }
        result = audit_candidates([record, dict(record)])
        self.assertEqual(result["eligible_for_further_review"], 0)
        self.assertEqual(result["abstained"], 2)
        self.assertEqual(result["abstention_reasons"]["duplicate_review_cycle"], 1)
        self.assertEqual(result["abstention_reasons"]["duplicate_review_cycle_previous_occurrence"], 1)
        self.assertEqual(result["conflicted_review_cycles"], 1)
        self.assertEqual(result["eligible_action_counts"], {})
        self.assertIsNone(result["approval_rate"])

    def test_conflicting_duplicate_actions_are_both_excluded(self):
        base = {
            "action_type": "approval",
            "official_fda_action_source": "https://www.fda.gov/example",
            "application_id": "BLA-TEST",
            "review_cycle_id": "original-1",
            "action_date": "2025-07-01",
            "evidence_cutoff_date": "2025-06-30",
            "source_cohort": "complete_original_filing_population",
            "original_filing_denominator_verified": True,
            "program_family_disjoint_verified": True,
        }
        conflicting = dict(base, action_type="complete_response_letter")
        report = audit_candidates([base, conflicting])
        self.assertEqual(report["eligible_for_further_review"], 0)
        self.assertEqual(report["abstained"], 2)
        self.assertEqual(report["eligible_action_counts"].get("approval", 0), 0)
        self.assertEqual(report["eligible_action_counts"].get("crl", 0), 0)

    def test_unknown_action_abstains(self):
        result = audit_candidates([{"action_type": "pending"}])
        self.assertEqual(result["abstained"], 1)
        self.assertFalse(result["trading_authorized"])


if __name__ == "__main__":
    unittest.main()
