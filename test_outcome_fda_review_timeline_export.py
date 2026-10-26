import json
import unittest

from outcome_fda_review_timeline_export import (
    SCHEMA_VERSION, DATA_QUALITY_FINDINGS, build_timeline_export,
)


class FDAReviewTimelineExportTests(unittest.TestCase):
    def setUp(self):
        self.export = build_timeline_export()

    def test_counts_are_derived_from_selected_actions(self):
        e = self.export
        self.assertEqual(e["schema_version"], SCHEMA_VERSION)
        self.assertEqual(e["dataset_role"], "research_only_nontraining")
        self.assertEqual(e["sampled_fda_actions"], 20)
        self.assertEqual(e["sampled_application_identifiers"], 10)
        self.assertEqual(e["source_supported_timelines"], 17)
        self.assertEqual(e["sampled_actions_without_structured_timeline"], 3)
        self.assertEqual(e["sampled_applications_without_structured_timeline"], 2)
        self.assertEqual(len(e["timelines"]), 17)
        self.assertEqual(len({r["application_key"] for r in e["timelines"]}), 8)

    def test_model_gates_fail_closed(self):
        e = self.export
        self.assertFalse(e["complete_application_denominator_verified"])
        self.assertEqual(e["independently_certified_review_cycles"], 0)
        self.assertEqual(e["model_eligible_records"], 0)
        self.assertIsNone(e["prediction_probability"])
        for r in e["timelines"]:
            self.assertFalse(r["review_cycle_independently_certified"])
            self.assertFalse(r["source_publication_asof_verified"])
            self.assertFalse(r["model_eligible"])
            self.assertIsNone(r["source_publication_date"])

    def test_lantidra_fda_summary_evidence_not_a_signed_letter(self):
        original = next(r for r in self.export["timelines"]
                        if r["submission_key"] == "BLA:125734:ORIGINAL")
        self.assertEqual(original["final_fda_action_date"], "2021-08-18")
        self.assertEqual(original["action_evidence_role"], "fda_regulatory_history_summary")
        self.assertEqual(original["data_quality_finding"]["code"],
                         "SIGNED_ORIGINAL_CRL_NOT_DIRECTLY_VERIFIED")
        self.assertFalse(original["data_quality_finding"]["detail"]
                         ["original_signed_action_letter_verified"])

    def test_mesoblast_2020_review_is_retrospective_not_signed_crl(self):
        original = next(r for r in self.export["timelines"]
                        if r["submission_key"] == "BLA:125706:ORIGINAL")
        self.assertEqual(original["submission_received_date"], "2020-01-31")
        self.assertEqual(original["final_fda_action_date"], "2020-09-30")
        self.assertEqual(original["action_evidence_role"], "fda_regulatory_history_summary")
        self.assertEqual(original["final_action_evidence_url"],
                         "https://www.fda.gov/media/184952/download")
        self.assertEqual(original["data_quality_finding"]["code"],
                         "SIGNED_ORIGINAL_2020_CRL_NOT_DIRECTLY_VERIFIED")
        self.assertFalse(original["data_quality_finding"]["detail"]
                         ["original_signed_action_letter_verified"])
        self.assertFalse(original["source_publication_asof_verified"])
        self.assertFalse(original["model_eligible"])

    def test_open_fda_conflicts_retained(self):
        for key in (
            "BLA:125743:RESUBMISSION-1",
            "BLA:125845:RESUBMISSION-1",
            "BLA:125706:RESUBMISSION-1",
            "BLA:125706:RESUBMISSION-2",
            "BLA:125827:RESUBMISSION-2",
        ):
            row = next(r for r in self.export["timelines"]
                       if r["submission_key"] == key)
            self.assertEqual(row["data_quality_finding"],
                             DATA_QUALITY_FINDINGS[key])
        alyglo = next(r for r in self.export["timelines"]
                      if r["submission_key"] == "BLA:125743:RESUBMISSION-1")
        self.assertEqual(alyglo["data_quality_finding"]["detail"]["clinical_review"]["goal_date"],
                         "2024-01-12")
        self.assertEqual(alyglo["data_quality_finding"]["detail"]["sbra"]["goal_date"],
                         "2024-01-13")

    def test_review_cycles_have_distinct_ids_and_fda_https_sources(self):
        e = self.export
        self.assertEqual(len({r["submission_key"] for r in e["timelines"]}),
                         len(e["timelines"]))
        for r in e["timelines"]:
            self.assertTrue(r["final_action_evidence_url"].startswith("https://"))
            self.assertTrue(r["receipt_evidence_url"].startswith("https://"))
            self.assertTrue(r["regulatory_history_source_url"].startswith("https://"))

    def test_roundtrip_json_preserves_provenance(self):
        self.assertEqual(self.export, json.loads(json.dumps(self.export)))


if __name__ == "__main__":
    unittest.main()
