import unittest
from outcome_fda_receipt_asof_audit import build_receipt_asof_audit

class ReceiptAsOfAuditTests(unittest.TestCase):
    def test_before_any_sponsor_public_confirmation(self):
        r = build_receipt_asof_audit("2024-05-19")
        self.assertEqual(r["selected_open_fda_receipt_denominator"], 3)
        self.assertEqual(r["sponsor_submission_confirmation_public_count"], 0)
        self.assertEqual(r["sponsor_exact_day_public_count"], 0)
        self.assertEqual(r["sponsor_acceptance_disclosure_public_count"], 0)

    def test_july_2025_does_not_backdate_pierre_fabre_november_disclosure(self):
        r = build_receipt_asof_audit("2025-07-23")
        self.assertEqual(r["sponsor_submission_confirmation_public_count"], 3)
        self.assertEqual(r["sponsor_exact_day_public_count"], 0)
        atara = next(x for x in r["records"]
                     if x["final_fda_action_date"] == "2026-01-09")
        self.assertIsNone(atara["sponsor_exact_submission_day_asof"])
        self.assertIsNone(atara["sponsor_reported_acceptance_day_asof"])
        self.assertFalse(atara["sponsor_acceptance_disclosure_public"])

    def test_november_2025_sponsor_day_available_but_not_fda_receipt(self):
        r = build_receipt_asof_audit("2025-11-03")
        self.assertEqual(r["sponsor_exact_day_public_count"], 1)
        atara = next(x for x in r["records"]
                     if x["final_fda_action_date"] == "2026-01-09")
        self.assertEqual(atara["sponsor_exact_submission_day_asof"], "2025-07-11")
        self.assertEqual(atara["sponsor_reported_acceptance_day_asof"], "2025-07-23")
        self.assertIsNone(atara["fda_exact_receipt_day"])
        self.assertFalse(atara["fda_receipt_independently_verified"])

    def test_asof_cutoff_after_all_actions_still_not_model_clearance(self):
        r = build_receipt_asof_audit("2026-10-26")
        self.assertEqual(r["sponsor_exact_day_public_count"], 1)
        self.assertEqual(r["fda_exact_receipts_independently_verified"], 0)
        self.assertEqual(r["model_eligible_records"], 0)
        self.assertIsNone(r["prediction_probability"])
        self.assertFalse(r["complete_application_denominator_verified"])
        self.assertFalse(r["historical_feature_asof_certified"])
        self.assertTrue(all(not x["model_eligible"] for x in r["records"]))

    def test_reject_invalid_cutoff(self):
        with self.assertRaises(ValueError):
            build_receipt_asof_audit("2025-99-99")
