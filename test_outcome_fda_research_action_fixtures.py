import unittest
from outcome_fda_action_events import check_asof, unique_final_actions
from outcome_fda_research_action_fixtures import RESEARCH_ACTIONS, research_summary

class ResearchFixturesTests(unittest.TestCase):
    def test_distinct_applications_and_actions(self):
        result = research_summary()
        self.assertEqual(result["applications_with_sampled_actions"], 10)
        self.assertEqual(result["sampled_action_endpoints"], 19)

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

    def test_celltrans_approval_cycle_is_unverified(self):
        matched = [e for e in RESEARCH_ACTIONS if e.application_key == "BLA:125734"]
        self.assertEqual(len(matched), 1)
        self.assertIn("CYCLE-UNVERIFIED", matched[0].submission_key)
        self.assertEqual(matched[0].event_date.isoformat(), "2023-06-28")

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
            self.assertIn("CYCLE-UNVERIFIED", actions[0].submission_key)
            self.assertIsNone(actions[0].source_publication_date)

if __name__ == "__main__":
    unittest.main()
