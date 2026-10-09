import sys
import types
import unittest
from unittest.mock import patch

import pandas as pd

from strategy_discovery import (
    RESEARCH_LENSES, research_questions, scoped_records,
    mechanism_evidence, target_summary, render_optional_discovery,
)


class OptionalDiscoveryTests(unittest.TestCase):
    def sample(self):
        return pd.DataFrame([
            {
                "record_id": "TRIAL|NCT00000001", "issue": "Type 2 diabetes",
                "ticker": "AA", "company": "Alpha", "drug": "Asset A",
                "nct_id": "NCT00000001", "drug_class": "",
                "mechanism_target": "GLP-1 receptor agonism",
                "classification_source_url": "https://example.org/verified",
                "named_mechanism": "",
            },
            {
                "record_id": "TRIAL|NCT00000001", "issue": "Obesity",
                "ticker": "AA", "company": "Alpha", "drug": "Asset A",
                "nct_id": "NCT00000001", "drug_class": "",
                "mechanism_target": "GLP-1 receptor agonism",
                "classification_source_url": "https://example.org/verified",
                "named_mechanism": "",
            },
            {
                "record_id": "TRIAL|NCT00000002", "issue": "Type 2 diabetes",
                "ticker": "BB", "company": "Bravo", "drug": "Asset B",
                "nct_id": "NCT00000002", "drug_class": "GLP-1 analog",
                "mechanism_target": "", "classification_source_url": "https://example.org/class",
                "named_mechanism": "",
            },
            {
                "record_id": "TRIAL|NCT00000003", "issue": "Type 2 diabetes",
                "ticker": "CC", "company": "Charlie", "drug": "Asset C",
                "nct_id": "NCT00000003", "drug_class": "",
                "mechanism_target": "", "named_mechanism": "",
            },
        ])

    def test_six_optional_lenses_are_questions_not_verdicts(self):
        self.assertEqual(len(RESEARCH_LENSES), 6)
        for lens in RESEARCH_LENSES:
            text = research_questions("Type 2 diabetes", lens)
            self.assertTrue(text)
            self.assertTrue(all(question.endswith("?") for question in text))
        with self.assertRaises(ValueError):
            research_questions("Type 2 diabetes", "FDA approval probability")

    def test_same_trial_can_be_seen_in_two_diseases_without_source_duplication(self):
        pool = self.sample()
        before = pool.copy(deep=True)
        diabetic = scoped_records(pool, "Type 2 diabetes")
        obesity = scoped_records(pool, "Obesity")
        self.assertEqual(len(diabetic), 3)
        self.assertEqual(len(obesity), 1)
        self.assertEqual(diabetic["record_id"].nunique(), 3)
        pd.testing.assert_frame_equal(pool, before)

    def test_target_and_drug_class_not_merged_or_guessed(self):
        diabetic = scoped_records(self.sample(), "Type 2 diabetes")
        categories = [mechanism_evidence(r)[0] for r in diabetic.to_dict("records")]
        self.assertIn("Annotated biological target / mechanism", categories)
        self.assertIn("Annotated drug class (target not established)", categories)
        self.assertIn("Unclassified — source research needed", categories)
        evidence = target_summary(diabetic)
        self.assertEqual(evidence["Pipeline records"].sum(), 3)
        self.assertEqual(evidence["Unique NCT IDs"].sum(), 3)
        self.assertEqual(evidence["Companies"].sum(), 3)
        self.assertIn("Unclassified — source research needed", set(evidence["Evidence type"]))
        self.assertTrue(
            evidence.loc[evidence["Evidence type"].eq(
                "Annotated biological target / mechanism"
            ), "Source"].iloc[0].startswith("https://")
        )

    def test_toggle_off_by_default_and_does_not_touch_data(self):
        pool = self.sample()
        original = pool.copy(deep=True)
        rendered = []
        fake = types.SimpleNamespace(
            markdown=lambda msg, **_: rendered.append(("heading", msg)),
            checkbox=lambda label, **kwargs:
                (rendered.append(("checkbox", kwargs)), False)[1],
            caption=lambda msg: rendered.append(("caption", msg)),
        )
        with patch.dict(sys.modules, {"streamlit": fake}):
            render_optional_discovery(pool)
        self.assertEqual(len([x for x in rendered if x[0] == "checkbox"]), 1)
        self.assertIs(rendered[1][1]["value"], False)
        self.assertEqual(rendered[1][1]["key"], "strategy_enable_discovery")
        pd.testing.assert_frame_equal(pool, original)


if __name__ == "__main__":
    unittest.main()
