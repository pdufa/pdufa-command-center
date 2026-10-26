import json
import unittest
from outcome_fda_receipt_boundary_gap_report import (
    SCHEMA_VERSION, MISSING_RECEIPT_EVIDENCE, SPONSOR_SUBMISSION_EVIDENCE,
    _validated_sponsor_evidence, build_receipt_boundary_gap_report,
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


    def test_pierre_fabre_precise_sponsor_date_not_fda_date(self):
        row = next(x for x in self.report["unlinked_actions"]
                   if x["application_key"] == "BLA:125745"
                   and x["final_fda_action_date"] == "2026-01-09")
        sponsor = row["sponsor_submission_provenance"]
        self.assertEqual(sponsor["sponsor_reported_submission_month"], "2025-07")
        self.assertEqual(sponsor["sponsor_reported_exact_submission_date"], "2025-07-11")
        self.assertEqual(sponsor["sponsor_submission_publicly_confirmed_by"], "2025-07-14")
        self.assertEqual(sponsor["sponsor_reported_fda_acceptance_date"], "2025-07-23")
        self.assertIn("20251103_PR_Final_BLA_Transfer_Announcement_0.pdf",
                      sponsor["sponsor_exact_day_source_url"])
        self.assertIsNone(sponsor["exact_fda_received_date"])
        self.assertFalse(sponsor["exact_fda_received_date_independently_verified"])
        self.assertFalse(row["receipt_date_verified"])
        self.assertIsNone(row["exact_submission_received_date"])

    def test_original_atara_and_regenxbio_are_month_only_sponsor_filings(self):
        expected = {
            ("BLA:125745", "2025-01-15"): (
                "2024-05", "2024-05-01", "2024-05-20", "2024-07-17"
            ),
            ("BLA:125840", "2026-02-07"): (
                "2025-03", "2025-03-01", "2025-03-13", "2025-05-13"
            ),
        }
        for row in self.report["unlinked_actions"]:
            key = (row["application_key"], row["final_fda_action_date"])
            if key not in expected:
                continue
            evidence = row["sponsor_submission_provenance"]
            month, month_start, confirmed_by, accepted_announced = expected[key]
            self.assertEqual(evidence["sponsor_reported_submission_month"], month)
            self.assertEqual(
                evidence["sponsor_submission_month_earliest_calendar_day"], month_start
            )
            self.assertEqual(evidence["sponsor_submission_publicly_confirmed_by"],
                             confirmed_by)
            self.assertEqual(evidence["fda_acceptance_announced_on"],
                             accepted_announced)
            self.assertIsNone(evidence["sponsor_reported_exact_submission_date"])
            self.assertIsNone(evidence["exact_fda_received_date"])
            self.assertFalse(evidence["fda_acceptance_effective_date_independently_verified"])

    def test_sponsor_precision_rollup_preserves_three_fda_gaps(self):
        self.assertEqual(self.report["sponsor_exact_submission_days_documented"], 1)
        self.assertEqual(self.report["sponsor_exact_submission_days_not_documented"], 2)
        self.assertEqual(self.report["fda_exact_receipt_days_independently_verified"], 0)
        self.assertEqual(self.report["unlinked_actions_count"], 3)
        self.assertEqual(self.report["structured_timeline_count"], 17)
        self.assertEqual(len(SPONSOR_SUBMISSION_EVIDENCE), 3)

    def test_invalid_sponsor_day_or_claimed_fda_verification_rejected(self):
        base = SPONSOR_SUBMISSION_EVIDENCE[("BLA:125745", "2026-01-09")]
        invalid = [
            {"sponsor_reported_exact_submission_date": "2025-07-25"},
            {"sponsor_reported_exact_submission_date": "2025-06-11"},
            {"sponsor_reported_fda_acceptance_date": "2025-07-10"},
            {"sponsor_exact_day_source_url": None},
            {"fda_acceptance_effective_date_independently_verified": True},
            {"sponsor_submission_publicly_confirmed_by": "2025-06-30"},
        ]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                _validated_sponsor_evidence({**base, **change})

if __name__ == "__main__":
    unittest.main()
