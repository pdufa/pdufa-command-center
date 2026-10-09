"""Integration checks against real committed PIPELINE source records."""
import unittest
from datetime import date
from pathlib import Path

from pipeline_universe import STAGES, load_universe, select_records, stage_counts
from strategy_discovery import scoped_records, target_summary
from strategy_view import (
    prepare_strategy_rows, expand_strategy_rows, issue_summary,
)

ROOT = Path(__file__).resolve().parent.parent / "data"


class StrategyRealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.universe = load_universe(ROOT, today=date(2026, 10, 9))
        cls.selected = select_records(cls.universe, list(STAGES))
        cls.strategy = prepare_strategy_rows(cls.selected)
        cls.associations = expand_strategy_rows(cls.strategy)

    def test_full_pipeline_source_is_available_not_20_curated_entries(self):
        self.assertGreaterEqual(len(self.selected), 9_000)
        self.assertEqual(len(self.strategy), len(self.selected))
        self.assertEqual(self.strategy["record_id"].nunique(), len(self.selected))
        self.assertEqual(self.associations["record_id"].nunique(), len(self.selected))

    def test_every_stage_kept_and_real_disease_groups_exist(self):
        counts = stage_counts(self.universe)
        self.assertEqual(list(counts["Stage"]), list(STAGES))
        self.assertGreater(int(counts["Count"].sum()), 9_000)
        summary = issue_summary(self.associations, sort_by="Most Pipeline trials / programs")
        names = set(summary["Disease / issue"])
        self.assertTrue(
            {"Type 2 diabetes", "Obesity", "Asthma", "Hypertension"}.issubset(names),
            "Core disease groups must be populated from the full PIPELINE source",
        )
        self.assertGreater(summary["Unique NCT IDs"].sum(), 9_000)

    def test_multi_disease_entries_do_not_mutate_original_source_counts(self):
        self.assertGreater(len(self.associations), len(self.selected))
        self.assertEqual(len(self.strategy), len(self.selected))
        self.assertTrue(self.associations["record_id"].notna().all())

    def test_optional_discovery_processes_real_large_disease_groups(self):
        """The opt-in feature must work on committed Pipeline rows, not just toy samples."""
        for disease in ("Type 2 diabetes", "Obesity", "Asthma"):
            with self.subTest(disease=disease):
                chosen = scoped_records(self.associations, disease)
                self.assertGreater(len(chosen), 20)
                summary = target_summary(chosen)
                self.assertFalse(summary.empty)
                self.assertEqual(int(summary["Pipeline records"].sum()), len(chosen))
                self.assertEqual(
                    int(summary["Unique NCT IDs"].sum()),
                    chosen["nct_id"].loc[chosen["nct_id"].ne("")].nunique(),
                )
                self.assertEqual(
                    chosen["record_id"].nunique(), len(chosen)
                )

    def test_real_data_keeps_unclassified_mechanisms_explicit(self):
        self.assertGreater(self.strategy["drug"].ne("").sum(), 1_000)
        self.assertTrue(self.strategy["approach"].ne("").all())
        self.assertFalse(self.strategy["issue"].isna().any())


if __name__ == "__main__":
    unittest.main()
