import unittest
import pandas as pd

from pipeline_universe import STAGES, select_records, stage_counts
from strategy_view import prepare_strategy_rows, issue_summary, _trial_html


def sample_pool():
    return pd.DataFrame([
        {
            "record_id": "TRIAL|NCT00000001",
            "record_type": "Registered trial", "ticker": "ABC",
            "company": "Alpha Biotech", "drug": "Alpha-1",
            "indication": "focal epilepsy", "nct_id": "NCT00000001",
            "drug_class": "Kv7 modulator", "registered_phase": "Phase 3",
            "current_stage": "Phase 3", "stage_tags": ("Phase 3",),
            "source_url": "https://clinicaltrials.gov/study/NCT00000001",
        },
        {
            "record_id": "TRIAL|NCT00000002",
            "record_type": "Registered trial", "ticker": "XYZ",
            "company": "Zeta Biotech", "drug": "Zeta-2",
            "indication": "chronic hepatitis B", "nct_id": "NCT00000002",
            "registered_phase": "Phase 1", "current_stage": "Phase 1",
            "stage_tags": ("Phase 1",),
        },
        {
            "record_id": "APPLICATION|XYZ|no-nct",
            "record_type": "Regulatory program / event", "ticker": "XYZ",
            "company": "Zeta Biotech", "drug": "Zeta-3",
            "indication": "", "nct_id": "",
            "current_stage": "PDUFA Decision",
            "stage_tags": ("PDUFA Decision",),
        },
    ])


class StrategyViewTests(unittest.TestCase):
    def test_all_selected_pipeline_records_remain_in_strategy(self):
        pool = sample_pool()
        issue_catalog = pd.DataFrame([
            {"nct_id": "NCT00000001", "issue": "Neurology",
             "trial_name": "ALPHA", "ticker": "UNRELATED"},
            {"nct_id": "NCT99999999", "issue": "Unrelated"},
        ])
        rows = prepare_strategy_rows(pool, issue_catalog)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows["record_id"].nunique(), 3)
        self.assertEqual(rows.iloc[0]["issue"], "Epilepsy")
        self.assertEqual(rows.iloc[0]["approach"], "Kv7 modulator")
        self.assertEqual(rows.iloc[1]["issue"], "Hepatitis B")
        self.assertEqual(rows.iloc[2]["issue"],
                         "Indication not recorded")

    def test_no_false_matching_by_ticker(self):
        pool = sample_pool()
        catalog = pd.DataFrame([{"nct_id": "NCT99999999", "ticker": "XYZ",
                                 "issue": "Wrong issue"}])
        rows = prepare_strategy_rows(pool, catalog)
        self.assertFalse(rows["issue"].eq("Wrong issue").any())

    def test_unrecorded_nct_is_not_counted_as_trial(self):
        rows = prepare_strategy_rows(sample_pool(), pd.DataFrame())
        summary = issue_summary(rows)
        blank = summary.loc[summary["Disease / issue"].eq(
            "Indication not recorded"
        )].iloc[0]
        self.assertEqual(int(blank["Unique NCT IDs"]), 0)
        self.assertIn("No NCT ID", _trial_html(rows.iloc[2].to_dict()))

    def test_stage_filter_preserves_individual_stage_counts(self):
        universe = sample_pool()
        self.assertEqual(len(STAGES), 14)
        counts = stage_counts(universe).set_index("Stage")["Count"]
        self.assertEqual(int(counts.loc["Phase 3"]), 1)
        self.assertEqual(int(counts.loc["Phase 1"]), 1)
        self.assertEqual(int(counts.loc["PDUFA Decision"]), 1)
        self.assertEqual(len(select_records(universe, list(STAGES))), 3)
        self.assertEqual(len(select_records(universe, ["Phase 3"])), 1)

    def test_html_escaping_and_link_scheme(self):
        pool = sample_pool()
        pool.loc[0, "drug"] = "<malicious>"
        pool.loc[0, "source_url"] = "javascript:alert(1)"
        rows = prepare_strategy_rows(pool, pd.DataFrame())
        rendered = _trial_html(rows.iloc[0].to_dict())
        self.assertNotIn("javascript:alert", rendered)
        self.assertNotIn("<malicious>", rendered)

    def test_disease_synonyms_are_combined_without_mixing_trial_ids(self):
        from disease_taxonomy import group_indication
        self.assertEqual(group_indication("Diabetes | Diabetes Mellitus, Type 2"), "Type 2 diabetes")
        self.assertEqual(group_indication("Type 2 Diabetes Mellitus"), "Type 2 diabetes")
        self.assertEqual(group_indication("Pulmonary Arterial Hypertension"), "Pulmonary arterial hypertension")
        self.assertEqual(group_indication("Non-small Cell Lung Cancer"), "Non-small cell lung cancer")
        self.assertEqual(group_indication("Prader-Willi Syndrome | Hyperphagia"), "Prader-Willi syndrome")
        self.assertEqual(group_indication("Healthy Volunteers"), "Healthy volunteers / no disease")
        self.assertEqual(group_indication("Diabetes Insipidus"), "Diabetes insipidus")

    def test_multi_condition_trial_is_visible_under_each_disease_without_new_source_rows(self):
        from strategy_view import expand_strategy_rows
        from disease_taxonomy import group_indications
        sample = sample_pool()
        sample.loc[1, "indication"] = "Diabetes | Diabetes Mellitus, Type 2 | Obesity"
        original = prepare_strategy_rows(sample, pd.DataFrame())
        self.assertEqual(len(original), 3)
        self.assertEqual(len(group_indications(sample.loc[1, "indication"])), 2)
        associations = expand_strategy_rows(original)
        self.assertEqual(associations["record_id"].nunique(), 3)
        self.assertEqual(len(associations), 4)
        self.assertEqual(set(associations.loc[
            associations["record_id"].eq("TRIAL|NCT00000002"), "issue"
        ]), {"Type 2 diabetes", "Obesity"})
        groups = issue_summary(original)
        self.assertIn("Type 2 diabetes", set(groups["Disease / issue"]))
        self.assertIn("Obesity", set(groups["Disease / issue"]))

    def test_neither_overweight_nor_diabetes_insipidus_inherits_wrong_patient_count(self):
        from disease_taxonomy import group_indication, burden_for
        self.assertEqual(group_indication("Overweight"), "Overweight")
        self.assertEqual(group_indication("Diabetes Insipidus"), "Diabetes insipidus")
        self.assertFalse(burden_for("Type 2 diabetes"))
        self.assertFalse(burden_for("Overweight"))

    def test_named_drug_mechanism_and_evidence_link(self):
        from drug_mechanisms import classify_named_interventions
        cls, evidence = classify_named_interventions("placebo | semaglutide")
        self.assertIn("GLP-1", cls)
        self.assertTrue(evidence.startswith("https://"))
        self.assertEqual(classify_named_interventions("AR-101 (unclassified)"), ("", ""))
        pool = sample_pool()
        pool.loc[1, "drug"] = "semaglutide | placebo"
        rows = prepare_strategy_rows(pool, pd.DataFrame())
        self.assertIn("GLP-1", rows.loc[1, "approach"])
        self.assertIn("Named ingredient class source", _trial_html(rows.loc[1].to_dict()))

    def test_non_small_cell_and_small_cell_are_not_mixed(self):
        from disease_taxonomy import group_indications
        non_small = group_indications("Non-Small Cell Lung Cancer")
        small = group_indications("Small Cell Lung Cancer")
        self.assertEqual(non_small, ("Non-small cell lung cancer",))
        self.assertEqual(small, ("Small cell lung cancer",))

    def test_population_sort_and_source_definitions(self):
        from disease_taxonomy import burden_for
        frame = pd.DataFrame([
            {"record_id": "1", "issue": "Diabetes", "nct_id": "NCT00000001", "ticker": "AA"},
            {"record_id": "2", "issue": "Hypertension", "nct_id": "NCT00000002", "ticker": "BB"},
            {"record_id": "3", "issue": "Osteoarthritis", "nct_id": "NCT00000003", "ticker": "CC"},
            {"record_id": "4", "issue": "Rare Unknown", "nct_id": "NCT00000004", "ticker": "DD"},
        ])
        summary = issue_summary(frame)
        self.assertEqual(summary.iloc[0]["Disease / issue"], "Hypertension")
        self.assertEqual(summary.iloc[1]["Disease / issue"], "Diabetes")
        self.assertEqual(summary.iloc[2]["Disease / issue"], "Osteoarthritis")
        self.assertEqual(summary.iloc[3]["Worldwide affected"], "Not verified")
        self.assertEqual(burden_for("Diabetes")["us_people"], 40100000)
        self.assertTrue(summary.iloc[0]["Burden source"].startswith("https://"))
        us = issue_summary(frame, sort_by="Patient population (US)")
        self.assertEqual(us.iloc[0]["Disease / issue"], "Hypertension")
        active = issue_summary(frame, sort_by="Most Pipeline trials / programs")
        self.assertEqual(len(active), 4)


    def test_activity_filter_retains_stages_and_distinguishes_terminated(self):
        from strategy_view import select_trial_activity
        source = sample_pool()
        source.loc[0, "status"] = "RECRUITING"
        source.loc[1, "status"] = "COMPLETED"
        source.loc[2, "status"] = "TERMINATED"
        strategy = prepare_strategy_rows(source, pd.DataFrame())
        self.assertEqual(len(select_trial_activity(
            strategy, "All clinical / regulatory records"
        )), 3)
        self.assertEqual(len(select_trial_activity(
            strategy, "Active / recruiting trials"
        )), 1)
        self.assertEqual(len(select_trial_activity(
            strategy, "Completed trials"
        )), 1)
        stopped = select_trial_activity(strategy, "Stopped / withdrawn studies")
        self.assertEqual(len(stopped), 1)
        self.assertEqual(stopped.iloc[0]["ticker"], "XYZ")
        # Filtering STRATEGY never modifies the source Pipeline pool.
        self.assertEqual(len(source), 3)


if __name__ == "__main__":
    unittest.main()
