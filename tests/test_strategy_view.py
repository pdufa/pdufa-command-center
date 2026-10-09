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
        self.assertEqual(rows.iloc[0]["issue"], "Neurology")
        self.assertEqual(rows.iloc[0]["approach"], "Kv7 modulator")
        self.assertEqual(rows.iloc[1]["issue"], "chronic hepatitis B")
        self.assertEqual(rows.iloc[2]["issue"],
                         "Indication / disease not yet classified")

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
            "Indication / disease not yet classified"
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


if __name__ == "__main__":
    unittest.main()
