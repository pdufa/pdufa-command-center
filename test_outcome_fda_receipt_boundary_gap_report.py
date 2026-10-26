import json
import unittest
from outcome_fda_receipt_boundary_gap_report import (
    SCHEMA_VERSION, MISSING_RECEIPT_EVIDENCE, build_receipt_boundary_gap_report,
)


class FDAReceiptBoundaryGapReportTests(unittest.TestCase):
    def setUp(self):
        self.report = build_receipt_boundary_gap_report()

    def test_exactly_three_missing_boundaries_derived_from_fixtures(self):
        r = self.report
        self.assertEqual(r["schema_version"], SCHEMA_VERSION)
        self.assertEqual(r["dataset_role"], "research_only_nontraining")
        self.assertEqual(r["selected_action_denominator"], 20)
        self.assertEqual(r["structured_timeline_count"], 17)
        self.assertEqual(r["unlinked_actions_count"], 3)
        self.assertEqual(r["unlinked_application_count"], 2)
        self.assertEqual(len(r["unlinked_actions"]), 3)

    def test_known_fda_action_endpoints_and_application_identities(self):
        got = {(a["application_key"], a["final_fda_action_date"]) for a in
               self.report["unlinked_actions"]}
        self.assertEqual(got, {
            ("BLA:125745", "2025-01-15"),
            ("BLA:125745", "2026-01-09"),
            ("BLA:125840", "2026-02-07"),
        })
        self.assertEqual(got, set(MISSING_RECEIPT_EVIDENCE))

    def test_no_guessed_fda_receipt_day(self):
        for action in self.report["unlinked_actions"]:
            self.assertIsNone(action["exact_submission_received_date"])
            self.assertFalse(action["receipt_date_verified"])
            self.assertFalse(action["review_cycle_independently_certified"])
            self.assertFalse(action["model_eligible"])
            self.assertEqual(action["evidence"]["granularity"], "month_only_sponsor")
            self.assertTrue(action["evidence"]["corroboration_url"].startswith("https://"))
            self.assertEqual(action["source_document_role"], "signed_fda_final_action_letter")

    def test_fail_closed_and_export_serialization(self):
        r = self.report
        self.assertFalse(r["complete_application_denominator_verified"])
        self.assertEqual(r["independently_certified_review_cycles"], 0)
        self.assertEqual(r["model_eligible_records"], 0)
        self.assertIsNone(r["prediction_probability"])
        self.assertEqual(json.loads(json.dumps(r)), r)


if __name__ == "__main__":
    unittest.main()
