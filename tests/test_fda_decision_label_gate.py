"""Regression tests for conservative FDA action-label gate."""
import unittest
from research.fda_decision_label_gate import assess_label_eligibility

BASE = {
    "action_type": "approval",
    "official_fda_action_source": "https://www.fda.gov/example",
    "application_id": "NDA-TEST",
    "review_cycle_id": "cycle-1",
    "action_date": "2025-06-01",
    "evidence_cutoff_date": "2025-05-31",
    "source_cohort": "representative_verified",
    "original_filing_denominator_verified": True,
    "program_family_disjoint_verified": True,
}

class LabelGateTests(unittest.TestCase):
    def test_approval_requires_review(self):
        result = assess_label_eligibility(BASE)
        self.assertEqual(result["status"], "ELIGIBLE_FOR_FURTHER_REVIEW")
        self.assertEqual(result["label"], 1)
        self.assertFalse(result["trading_authorized"])

    def test_crl_is_not_approval(self):
        record = {**BASE, "action_type": "complete_response_letter"}
        self.assertEqual(assess_label_eligibility(record)["label"], 0)

    def test_candidate_union_abstains(self):
        record = {**BASE, "source_cohort": "candidate_union"}
        result = assess_label_eligibility(record)
        self.assertEqual(result["status"], "ABSTAIN")
        self.assertIsNone(result["label"])

    def test_approval_only_abstains(self):
        record = {**BASE, "source_cohort": "selected_approvals_only"}
        self.assertEqual(assess_label_eligibility(record)["status"], "ABSTAIN")

    def test_same_day_or_future_evidence_abstains(self):
        for cutoff in ("2025-06-01", "2025-06-02"):
            with self.subTest(cutoff=cutoff):
                record = {**BASE, "evidence_cutoff_date": cutoff}
                self.assertIn("hindsight_or_same_day_evidence", assess_label_eligibility(record)["reasons"])

    def test_missing_dates_abstains(self):
        record = {**BASE, "action_date": "not-a-date"}
        self.assertEqual(assess_label_eligibility(record)["status"], "ABSTAIN")

    def test_related_program_leakage_abstains(self):
        record = {**BASE, "program_family_disjoint_verified": False}
        self.assertEqual(assess_label_eligibility(record)["status"], "ABSTAIN")

    def test_non_fda_or_non_https_source_abstains(self):
        for source in ("https://notfda.gov/action", "http://www.fda.gov/action", "FDA press release"):
            with self.subTest(source=source):
                result = assess_label_eligibility({**BASE, "official_fda_action_source": source})
                self.assertEqual(result["status"], "ABSTAIN")
                self.assertIn("unverified_fda_source_domain", result["reasons"])

    def test_unknown_outcome_abstains(self):
        record = {**BASE, "action_type": "pending"}
        self.assertEqual(assess_label_eligibility(record)["status"], "ABSTAIN")

if __name__ == "__main__":
    unittest.main()
