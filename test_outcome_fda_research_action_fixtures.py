import unittest
from outcome_fda_action_events import check_asof, unique_final_actions
from outcome_fda_research_action_fixtures import RESEARCH_ACTIONS, research_summary

class ResearchFixturesTests(unittest.TestCase):
    def test_distinct_applications_and_actions(self):
        result = research_summary()
        self.assertEqual(result["applications_with_sampled_actions"], 10)
        self.assertEqual(result["sampled_action_endpoints"], 20)

    def test_never_model_eligible(self):
        result = research_summary()
        self.assertEqual(result["independently_certified_review_cycles"], 0)
        self.assertEqual(result["model_eligible_records"], 0)
        self.assertIsNone(result["prediction_probability"])
        self.assertFalse(result["complete_application_denominator_verified"])

    def test_sources_are_not_assumed_published_on_action_day(self):
        from datetime import date
        self.assertTrue(all(not check_asof(event, date(2026, 10, 26)) for event in RESEARCH_ACTIONS))

    def test_action_keys_are_unique(self):
        self.assertEqual(len(unique_final_actions(list(RESEARCH_ACTIONS))), len(RESEARCH_ACTIONS))

    def test_two_green_cross_actions_one_application(self):
        gc = [e for e in RESEARCH_ACTIONS if e.application_key == "BLA:125743"]
        self.assertEqual(len(gc), 2)
        self.assertEqual({e.event_type for e in gc}, {"complete_response", "approval"})
        self.assertEqual({e.event_date.isoformat() for e in gc}, {"2022-02-25", "2023-12-15"})

    def test_two_atara_pierre_fabre_letters_one_application(self):
        linked = [e for e in RESEARCH_ACTIONS if e.application_key == "BLA:125745"]
        self.assertEqual(len(linked), 2)
        self.assertTrue(all(e.event_type == "complete_response" for e in linked))
        self.assertEqual({e.event_date.isoformat() for e in linked}, {"2025-01-15", "2026-01-09"})

    def test_celltrans_two_fda_actions_keep_source_roles(self):
        matched = [e for e in RESEARCH_ACTIONS if e.application_key == "BLA:125734"]
        self.assertEqual(len(matched), 2)
        first, second = sorted(matched, key=lambda e: e.event_date)
        self.assertEqual((first.submission_key, first.event_type, first.event_date.isoformat()),
                         ("BLA:125734:ORIGINAL", "complete_response", "2021-08-18"))
        self.assertEqual(first.source_document_role, "fda_regulatory_history_summary")
        self.assertEqual((second.submission_key, second.event_type, second.event_date.isoformat()),
                         ("BLA:125734:RESUBMISSION-1", "approval", "2023-06-28"))
        self.assertEqual(second.source_document_role, "signed_fda_final_action_letter")

    def test_no_stemcyte_conflicting_approval_date_silently_included(self):
        self.assertNotIn("BLA:125764", {e.application_key for e in RESEARCH_ACTIONS})

    def test_capricor_and_regenxbio_only_confirm_crl(self):
        expectations = {
            "BLA:125842": "2025-07-09",
            "BLA:125840": "2026-02-07",
        }
        for key, date in expectations.items():
            actions = [e for e in RESEARCH_ACTIONS if e.application_key == key]
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0].event_type, "complete_response")
            self.assertEqual(actions[0].event_date.isoformat(), date)
            if key == "BLA:125840":
                self.assertIn("CYCLE-UNVERIFIED", actions[0].submission_key)
            else:
                self.assertEqual(actions[0].submission_key, "BLA:125842:ORIGINAL")
            self.assertIsNone(actions[0].source_publication_date)

    def test_alyglo_original_and_resubmission_identified_by_fda(self):
        gc = sorted((e for e in RESEARCH_ACTIONS if e.application_key == "BLA:125743"),
                    key=lambda e: e.event_date)
        self.assertEqual([e.submission_key for e in gc],
                         ["BLA:125743:ORIGINAL", "BLA:125743:RESUBMISSION-1"])
        self.assertTrue(all(e.source_document_role == "signed_fda_final_action_letter"
                            for e in gc))

    def test_2020_mesoblast_and_2021_lantidra_use_fda_reviews_not_signed_letters(self):
        indirect = [e for e in RESEARCH_ACTIONS
                    if e.source_document_role == "fda_regulatory_history_summary"]
        self.assertEqual(len(indirect), 2)
        self.assertEqual(
            {(e.application_key, e.event_date.isoformat()) for e in indirect},
            {("BLA:125706", "2020-09-30"), ("BLA:125734", "2021-08-18")},
        )
        source = next(e for e in indirect if e.application_key == "BLA:125706")
        self.assertEqual(source.source_url, "https://www.fda.gov/media/184952/download")
        self.assertIsNone(source.source_publication_date)

if __name__ == "__main__":
    unittest.main()
