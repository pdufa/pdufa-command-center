import unittest
from datetime import date
from dataclasses import replace
from outcome_fda_review_timeline_evidence import (
    FDA_ABEONA_APPROVAL, FDA_ABEONA_CRL,
    FDA_MESOBLAST_SBRA, FDA_MESOBLAST_2023_CRL, FDA_MESOBLAST_APPROVAL,
    MESOBLAST_SBRA_IDENTIFIER_CONFLICT, MESOBLAST_SOURCE_SUPPORTED_TIMELINES,
    ROCKET_SOURCE_SUPPORTED_TIMELINES, FDA_ROCKET_CRL, FDA_ROCKET_APPROVAL,
    ULTRAGENYX_SOURCE_SUPPORTED_TIMELINES, ULTRAGENYX_PDUFA_GOAL_SOURCE_CONFLICT,
    FDA_ULTRAGENYX_CRL, FDA_ULTRAGENYX_APPROVAL,
    REPLIMUNE_SOURCE_SUPPORTED_TIMELINES,
    REPLIMUNE_FINAL_ACTION_VS_REVIEW_RECOMMENDATION,
    FDA_REPLIMUNE_FIRST_CRL, FDA_REPLIMUNE_SECOND_CRL, FDA_REPLIMUNE_APPROVAL,
    REVIEW_TIMELINES, SourceSupportedCycle, review_timeline_summary,
    validate_review_timelines,
)
from outcome_fda_research_action_fixtures import RESEARCH_ACTIONS

class ReviewTimelineEvidenceTests(unittest.TestCase):
    def test_eleven_timelines_are_five_applications(self):
        summary = review_timeline_summary()
        self.assertEqual(summary["applications_with_source_supported_timelines"], 5)
        self.assertEqual(summary["source_supported_review_timelines"], 11)
        self.assertEqual({c.application_key for c in REVIEW_TIMELINES}, {"BLA:125807", "BLA:125706", "BLA:125806", "BLA:125845", "BLA:125827"})

    def test_dynamic_selected_sample_denominators(self):
        summary = review_timeline_summary()
        self.assertEqual(summary["selected_research_action_endpoints"], 19)
        self.assertEqual(summary["selected_research_application_identifiers"], 10)
        self.assertEqual(summary["source_supported_review_timelines"], 11)
        self.assertEqual(summary["applications_with_source_supported_timelines"], 5)
        self.assertEqual(summary["selected_actions_without_structured_timeline"], 8)
        self.assertEqual(summary["selected_applications_without_structured_timeline"], 5)
        self.assertFalse(summary["complete_application_denominator_verified"])
        self.assertEqual(summary["model_eligible_records"], 0)

    def test_action_endpoints_match_source_fixtures(self):
        validate_review_timelines()
        self.assertEqual(
            [(c.received_date.isoformat(), c.action_date.isoformat(), c.action_type)
             for c in REVIEW_TIMELINES],
            [("2023-09-25", "2024-04-16", "complete_response"),
             ("2024-10-28", "2025-04-28", "approval"),
             ("2023-01-31", "2023-08-01", "complete_response"),
             ("2024-07-08", "2024-12-18", "approval"),
             ("2023-08-01", "2024-06-14", "complete_response"),
             ("2025-09-26", "2026-03-26", "accelerated_approval"),
             ("2024-12-18", "2025-07-07", "complete_response"),
             ("2026-03-20", "2026-09-17", "approval"),
             ("2024-11-21", "2025-07-21", "complete_response"),
             ("2025-10-09", "2026-04-10", "complete_response"),
             ("2026-06-02", "2026-08-06", "accelerated_approval")],
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

    def test_rocket_original_and_resubmission_are_one_application(self):
        cycles = ROCKET_SOURCE_SUPPORTED_TIMELINES
        self.assertEqual(len(cycles), 2)
        self.assertEqual({c.application_key for c in cycles}, {"BLA:125806"})
        self.assertEqual(
            [(c.received_date.isoformat(), c.action_date.isoformat(), c.action_type) for c in cycles],
            [("2023-08-01", "2024-06-14", "complete_response"),
             ("2025-09-26", "2026-03-26", "accelerated_approval")],
        )
        self.assertEqual(cycles[0].final_action_source_url, FDA_ROCKET_CRL)
        self.assertEqual(cycles[1].final_action_source_url, FDA_ROCKET_APPROVAL)
        self.assertEqual(cycles[1].pdufa_goal_date, date(2026, 3, 28))

    def test_ultragenyx_two_actions_are_one_application(self):
        cycles = ULTRAGENYX_SOURCE_SUPPORTED_TIMELINES
        self.assertEqual(len(cycles), 2)
        self.assertEqual({c.application_key for c in cycles}, {"BLA:125845"})
        self.assertEqual(
            [(c.received_date.isoformat(), c.action_date.isoformat(), c.action_type) for c in cycles],
            [("2024-12-18", "2025-07-07", "complete_response"),
             ("2026-03-20", "2026-09-17", "approval")],
        )
        self.assertEqual(cycles[0].final_action_source_url, FDA_ULTRAGENYX_CRL)
        self.assertEqual(cycles[1].final_action_source_url, FDA_ULTRAGENYX_APPROVAL)

    def test_ultragenyx_pdufa_source_disagreement_kept_open(self):
        conflict = ULTRAGENYX_PDUFA_GOAL_SOURCE_CONFLICT
        self.assertEqual(conflict["sbra"]["goal_date"], "2026-09-19")
        self.assertEqual(conflict["clinical_review"]["goal_date"], "2026-09-18")
        self.assertNotEqual(conflict["sbra"]["source_url"],
                            conflict["clinical_review"]["source_url"])
        self.assertEqual(conflict["resolution_status"], "unresolved_preserve_both")
        self.assertEqual(ULTRAGENYX_SOURCE_SUPPORTED_TIMELINES[1].pdufa_goal_date,
                         date(2026, 9, 19))

    def test_replimune_three_actions_are_one_application(self):
        cycles = REPLIMUNE_SOURCE_SUPPORTED_TIMELINES
        self.assertEqual(len(cycles), 3)
        self.assertEqual({c.application_key for c in cycles}, {"BLA:125827"})
        self.assertEqual(
            [(c.received_date.isoformat(), c.action_date.isoformat(), c.action_type) for c in cycles],
            [("2024-11-21", "2025-07-21", "complete_response"),
             ("2025-10-09", "2026-04-10", "complete_response"),
             ("2026-06-02", "2026-08-06", "accelerated_approval")],
        )
        self.assertEqual(cycles[0].final_action_source_url, FDA_REPLIMUNE_FIRST_CRL)
        self.assertEqual(cycles[1].final_action_source_url, FDA_REPLIMUNE_SECOND_CRL)
        self.assertEqual(cycles[2].final_action_source_url, FDA_REPLIMUNE_APPROVAL)

    def test_replimune_reviewer_recommendation_not_final_action(self):
        anomaly = REPLIMUNE_FINAL_ACTION_VS_REVIEW_RECOMMENDATION
        self.assertEqual(anomaly["reviewer_recommendation"], "complete_response")
        self.assertEqual(anomaly["final_agency_action"], "accelerated_approval")
        self.assertEqual(anomaly["review_pdufa_goal_date"], "2026-08-02")
        self.assertEqual(anomaly["final_action_date"], "2026-08-06")
        self.assertEqual(anomaly["pdufa_clock_explanation"], "unverified")
        self.assertEqual(REPLIMUNE_SOURCE_SUPPORTED_TIMELINES[2].pdufa_goal_date, date(2026, 8, 2))

    def test_all_seven_new_timelines_remain_research_only(self):
        new_cycles = (ROCKET_SOURCE_SUPPORTED_TIMELINES
                      + ULTRAGENYX_SOURCE_SUPPORTED_TIMELINES
                      + REPLIMUNE_SOURCE_SUPPORTED_TIMELINES)
        self.assertEqual(len(new_cycles), 7)
        self.assertTrue(all(not c.independently_certified
                            and not c.model_eligible
                            and not c.source_publication_asof_verified
                            for c in new_cycles))
        self.assertEqual(review_timeline_summary()["model_eligible_records"], 0)

if __name__ == "__main__":
    unittest.main()
