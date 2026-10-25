"""Published KEYNOTE-024 pilot extraction is dated, source-linked and unscored."""
import unittest

from app.scientific_dossier import DOMAINS
from app.scientific_pilot_keynote024_results import keynote024_published_results


class Keynote024PublishedResultsTests(unittest.TestCase):
    def setUp(self):
        self.report = keynote024_published_results()
        self.snapshots = {
            x["analysis_id"]: x for x in self.report["analysis_snapshots"]
        }

    def test_primary_pfs_exact_original_publication(self):
        initial = self.snapshots["keynote024_initial_2016"]
        self.assertEqual(initial["nct_id"], "NCT02142738")
        self.assertEqual(initial["publication_date"], "2016-10-08")
        self.assertEqual(initial["source_id"], "27718847")
        self.assertEqual(initial["arm_counts_randomized"], {
            "pembrolizumab": 154, "chemotherapy": 151,
        })
        pfs = initial["effects"]["progression_free_survival"]
        self.assertEqual(pfs["analysis_role"], "prespecified_primary")
        self.assertEqual((pfs["pembrolizumab"], pfs["chemotherapy"]), (10.3, 6.0))
        self.assertEqual(pfs["hazard_ratio"], 0.5)
        self.assertEqual(pfs["hazard_ratio_95pct_ci"], [0.37, 0.68])
        self.assertEqual(pfs["p_value"], "<0.001")

    def test_original_safety_uses_treatment_related_not_all_cause(self):
        initial = self.snapshots["keynote024_initial_2016"]
        self.assertEqual(initial["safety"]["treatment_related_adverse_events_grade_3_to_5_percent"],
                         {"pembrolizumab": 26.6, "chemotherapy": 53.3})
        self.assertIn("not all-cause", initial["safety"]["denominator_note"])
        self.assertEqual(initial["effects"]["overall_survival"]["analysis_role"],
                         "secondary_interim")
        self.assertNotIn("median_months", initial["effects"]["overall_survival"])

    def test_long_term_followup_is_separate_and_crossover_flagged(self):
        initial = self.snapshots["keynote024_initial_2016"]
        followup = self.snapshots["keynote024_five_year_2021"]
        self.assertEqual(followup["source_id"], "33872070")
        self.assertEqual(followup["data_cutoff_date"], "2020-06-01")
        self.assertEqual(followup["effective_crossover_percent_from_chemotherapy"], 66.0)
        self.assertEqual(followup["effects"]["overall_survival"]["hazard_ratio"], 0.62)
        self.assertEqual(followup["effects"]["overall_survival"]["five_year_kaplan_meier_survival_percent"],
                         {"pembrolizumab": 31.9, "chemotherapy": 16.3})
        self.assertNotEqual(
            initial["effects"]["overall_survival"]["hazard_ratio"],
            followup["effects"]["overall_survival"]["hazard_ratio"],
        )
        self.assertNotIn("five_year_kaplan_meier_survival_percent",
                         initial["effects"]["overall_survival"])

    def test_exploratory_quality_of_life_keeps_nominal_p_value(self):
        pro = self.snapshots["keynote024_pros_2017"]
        self.assertEqual(pro["source_id"], "29129441")
        outcome = pro["outcomes"]["quality_of_life_week15_change"]
        self.assertEqual(outcome["between_group_difference"], 7.8)
        self.assertEqual(outcome["difference_95pct_ci"], [2.9, 12.8])
        self.assertEqual(outcome["nominal_p_value"], "0.0020")
        self.assertEqual(outcome["analysis_role"], "prespecified_exploratory")

    def test_unverified_analysis_does_not_change_existing_scores(self):
        self.assertEqual(self.report["nct_id"], "NCT02142738")
        self.assertEqual(set(self.report["domain_scores"]), set(DOMAINS))
        self.assertEqual(len(self.report["analysis_snapshots"]), 3)
        self.assertTrue(all(x is None for x in self.report["domain_scores"].values()))
        self.assertIsNone(self.report["overall_score"])
        self.assertIsNone(self.report["fda_approval_probability"])
        self.assertEqual(self.report["scientific_review_status"],
                         "source_reported_requires_independent_appraisal")
        self.assertTrue(self.report["read_only"])
        self.assertFalse(self.report["trading_actions_enabled"])

    def test_sources_have_unique_ids_and_valid_http_links(self):
        source_ids = [r["source_id"] for r in self.report["analysis_snapshots"]]
        self.assertEqual(len(source_ids), len(set(source_ids)))
        for record in self.report["analysis_snapshots"]:
            self.assertEqual(record["nct_id"], "NCT02142738")
            self.assertEqual(record["source_url"],
                             "https://pubmed.ncbi.nlm.nih.gov/" + record["source_id"] + "/")
            self.assertEqual(record["source_evidence_status"],
                             "published_reported_not_independently_reanalyzed")

    def test_publication_results_are_not_regulatory_forecasts(self):
        corroboration = self.report["corroborating_sources"]
        self.assertEqual(len(corroboration), 2)
        self.assertTrue(any(x["source_type"] == "fda_staff_authored_approval_summary"
                            for x in corroboration))
        self.assertTrue(any(x["source_type"] == "national_cancer_institute_scientific_summary"
                            for x in corroboration))

    def test_returned_data_is_independent_copy(self):
        original = keynote024_published_results()
        self.report["analysis_snapshots"][0]["effects"].clear()
        self.report["corroborating_sources"].clear()
        self.assertEqual(keynote024_published_results(), original)


if __name__ == "__main__":
    unittest.main()
