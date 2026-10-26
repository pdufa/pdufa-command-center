import unittest
from outcome_fda_research_feature_projection import (
    ALLOWED_RESEARCH_FIELDS, build_research_feature_projection,
)

class ResearchFeatureProjectionTests(unittest.TestCase):
    def test_strict_allowlist_never_includes_outcome_labels(self):
        self.assertEqual(ALLOWED_RESEARCH_FIELDS, {
            "sponsor_submission_month_asof",
            "sponsor_exact_submission_day_asof",
            "sponsor_reported_acceptance_day_asof",
        })
        for cutoff in ("2024-05-19", "2025-07-23", "2025-11-03", "2026-10-26"):
            p = build_research_feature_projection(cutoff)
            self.assertEqual(p["selected_open_fda_receipt_denominator"], 3)
            self.assertTrue(p["retrospective_fda_action_labels_excluded"])
            self.assertTrue(p["unverified_fda_receipt_dates_excluded"])
            self.assertEqual(p["model_eligible_records"], 0)
            self.assertIsNone(p["prediction_probability"])
            for row in p["records"]:
                self.assertEqual(set(row["research_observations"]), ALLOWED_RESEARCH_FIELDS)
                self.assertNotIn("final_fda_action_date", row)
                self.assertNotIn("fda_exact_receipt_day", row)
                self.assertFalse(row["historical_feature_asof_certified"])
                self.assertFalse(row["model_eligible"])

    def test_future_exact_sponsor_day_cannot_appear_in_july(self):
        p = build_research_feature_projection("2025-07-23")
        row = next(x for x in p["records"]
                   if x["application_key"] == "BLA:125745"
                   and x["submission_key"].endswith("2026"))
        self.assertIsNone(row["research_observations"]["sponsor_exact_submission_day_asof"])
        self.assertIsNone(row["research_observations"]["sponsor_reported_acceptance_day_asof"])

    def test_november_publication_can_be_observed_but_not_used_as_model_feature(self):
        p = build_research_feature_projection("2025-11-03")
        row = next(x for x in p["records"]
                   if x["application_key"] == "BLA:125745"
                   and x["submission_key"].endswith("2026"))
        self.assertEqual(row["research_observations"]["sponsor_exact_submission_day_asof"],
                         "2025-07-11")
        self.assertFalse(row["model_eligible"])
        self.assertFalse(p["historical_feature_asof_certified"])

    def test_no_future_observations_before_first_submission(self):
        p = build_research_feature_projection("2024-05-19")
        for row in p["records"]:
            self.assertTrue(all(value is None for value in row["research_observations"].values()))
