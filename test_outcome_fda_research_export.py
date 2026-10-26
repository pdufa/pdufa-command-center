import json
import unittest
from outcome_fda_research_export import build_research_export, SCHEMA_VERSION


class ResearchExportTests(unittest.TestCase):
    def setUp(self):
        self.data = build_research_export()

    def test_schema_and_role(self):
        self.assertEqual(self.data["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.data["dataset_role"], "research_only_nontraining")

    def test_counts_and_nonduplicate_records(self):
        self.assertEqual(self.data["applications_with_sampled_actions"], 8)
        self.assertEqual(self.data["sampled_action_endpoints"], 17)
        self.assertEqual(len(self.data["records"]), 17)
        self.assertEqual(len({r["application_key"] for r in self.data["records"]}), 8)

    def test_fail_closed_fields(self):
        self.assertFalse(self.data["complete_application_denominator_verified"])
        self.assertEqual(self.data["independently_certified_review_cycles"], 0)
        self.assertEqual(self.data["model_eligible_records"], 0)
        self.assertIsNone(self.data["prediction_probability"])
        for record in self.data["records"]:
            self.assertFalse(record["model_eligible"])
            self.assertFalse(record["feature_asof_verified"])
            self.assertFalse(record["review_cycle_certified"])
            self.assertIsNone(record["source_publication_date"])

    def test_individual_fda_primary_source_url(self):
        for record in self.data["records"]:
            self.assertTrue(record["primary_fda_source_url"].startswith("https://"))
            self.assertTrue(record["final_agency_action"])
            self.assertIn(record["action_type"], ("complete_response", "approval", "accelerated_approval"))

    def test_roundtrip_json(self):
        self.assertEqual(json.loads(json.dumps(self.data)), self.data)

if __name__ == "__main__":
    unittest.main()
