import unittest
from outcome_fda_action_events import check_asof, unique_final_actions
from outcome_fda_research_action_fixtures import RESEARCH_ACTIONS, research_summary

class ResearchFixturesTests(unittest.TestCase):
    def test_distinct_applications_and_actions(self):
        result = research_summary()
        self.assertEqual(result["applications_with_sampled_actions"], 5)
        self.assertEqual(result["sampled_action_endpoints"], 12)

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

if __name__ == "__main__":
    unittest.main()
