import unittest
from datetime import date
from dataclasses import replace
from outcome_fda_review_timeline_evidence import (
    FDA_ABEONA_APPROVAL, FDA_ABEONA_CRL,
    FDA_MESOBLAST_SBRA, FDA_MESOBLAST_2023_CRL, FDA_MESOBLAST_APPROVAL,
    MESOBLAST_SBRA_IDENTIFIER_CONFLICT, MESOBLAST_SOURCE_SUPPORTED_TIMELINES,
    REVIEW_TIMELINES, SourceSupportedCycle, review_timeline_summary,
    validate_review_timelines,
)
from outcome_fda_research_action_fixtures import RESEARCH_ACTIONS

class ReviewTimelineEvidenceTests(unittest.TestCase):
    def test_four_timelines_are_two_applications(self):
        summary = review_timeline_summary()
        self.assertEqual(summary["applications_with_source_supported_timelines"], 2)
        self.assertEqual(summary["source_supported_review_timelines"], 4)
        self.assertEqual({c.application_key for c in REVIEW_TIMELINES}, {"BLA:125807", "BLA:125706"})

    def test_action_endpoints_match_source_fixtures(self):
        validate_review_timelines()
        self.assertEqual(
            [(c.received_date.isoformat(), c.action_date.isoformat(), c.action_type)
             for c in REVIEW_TIMELINES],
            [("2023-09-25", "2024-04-16", "complete_response"),
             ("2024-10-28", "2025-04-28", "approval"),
             ("2023-01-31", "2023-08-01", "complete_response"),
             ("2024-07-08", "2024-12-18", "approval")],
        )

    def test_second_cycle_uses_fda_pdufa_goal_not_action(self):
        self.assertEqual(REVIEW_TIMELINES[1].pdufa_goal_date, date(2025, 4, 29))
        self.assertEqual(REVIEW_TIMELINES[1].action_date, date(2025, 4, 28))
        self.assertEqual(REVIEW_TIMELINES[0].final_action_source_url, FDA_ABEONA_CRL)
        self.assertEqual(REVIEW_TIMELINES[1].final_action_source_url, FDA_ABEONA_APPROVAL)

    def test_no_certificate_model_or_probability(self):
        summary = review_timeline_summary()
        self.assertTrue(summary["research_only"])
        self.assertFalse(summary["complete_application_denominator_verified"])
        self.assertFalse(summary["source_publication_asof_verified"])
        self.assertEqual(summary["independently_certified_review_cycles"], 0)
        self.assertEqual(summary["model_eligible_records"], 0)
        self.assertIsNone(summary["prediction_probability"])
        self.assertTrue(all(not c.independently_certified
                            and not c.model_eligible
                            and not c.source_publication_asof_verified
                            for c in REVIEW_TIMELINES))

    def test_action_before_submission_rejected(self):
        with self.assertRaises(ValueError):
            replace(REVIEW_TIMELINES[0], action_date=date(2023, 9, 24))

    def test_invalid_nonfinal_action_rejected(self):
        with self.assertRaises(ValueError):
            replace(REVIEW_TIMELINES[0], action_type="review_recommendation")

    def test_duplicate_cycle_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_review_timelines((REVIEW_TIMELINES[0], REVIEW_TIMELINES[0]))

    def test_overlapping_cycles_rejected(self):
        bad = replace(REVIEW_TIMELINES[1], received_date=date(2024, 4, 16))
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            validate_review_timelines((REVIEW_TIMELINES[0], bad))

    def test_missing_final_action_fixture_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing matching"):
            validate_review_timelines(REVIEW_TIMELINES, tuple())

    def test_mismatched_fda_source_rejected(self):
        with self.assertRaisesRegex(ValueError, "source mismatch"):
            validate_review_timelines((replace(REVIEW_TIMELINES[0], final_action_source_url=FDA_ABEONA_APPROVAL),))

    def test_mesoblast_2023_and_2024_source_boundaries(self):
        cycles = MESOBLAST_SOURCE_SUPPORTED_TIMELINES
        self.assertEqual(len(cycles), 2)
        self.assertEqual(
            [(c.received_date.isoformat(), c.action_date.isoformat(), c.action_type)
             for c in cycles],
            [("2023-01-31", "2023-08-01", "complete_response"),
             ("2024-07-08", "2024-12-18", "approval")],
        )
        self.assertEqual(cycles[0].final_action_source_url, FDA_MESOBLAST_2023_CRL)
        self.assertEqual(cycles[1].final_action_source_url, FDA_MESOBLAST_APPROVAL)
        self.assertEqual(cycles[1].regulatory_history_source_url, FDA_MESOBLAST_SBRA)
        self.assertEqual(cycles[1].pdufa_goal_date, date(2025, 1, 7))

    def test_mesoblast_conflicting_original_fda_pdf_identifiers_retained(self):
        conflict = MESOBLAST_SBRA_IDENTIFIER_CONFLICT
        self.assertEqual(conflict["cover_page_1"], "127506/0")
        self.assertEqual(conflict["regulatory_history_page_7"], "125706/0")
        self.assertEqual(conflict["signed_fda_approval_letter"], "125706/0")
        self.assertTrue(all(c.application_key == "BLA:125706"
                            for c in MESOBLAST_SOURCE_SUPPORTED_TIMELINES))
        self.assertNotIn("BLA:127506", {c.application_key for c in REVIEW_TIMELINES})

    def test_mesoblast_original_2020_cycle_not_assumed_certified(self):
        self.assertTrue(all(c.received_date != date(2020, 1, 31)
                            for c in MESOBLAST_SOURCE_SUPPORTED_TIMELINES))
        self.assertEqual(review_timeline_summary()["independently_certified_review_cycles"], 0)

if __name__ == "__main__":
    unittest.main()
