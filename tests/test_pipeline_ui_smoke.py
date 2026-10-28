"""Exercise the supported Next.js Pipeline, distinct GEM stages and WT.

The old Streamlit widget/session-state protocol is retired. Current empty-filter
semantics, bounded pages, saved labels and evidence gates are tested against the
actual frontend modules, rather than reconstructing the removed application.
"""
import csv
from pathlib import Path
import unittest
from supported_dashboard_checks import run_frontend_contract, run_backend_contract

ROOT = Path(__file__).resolve().parents[1]


class PipelinePageSmokeTests(unittest.TestCase):
    def test_retired_plan_navigation_keeps_saved_plan_data(self):
        self.assertGreater(run_frontend_contract("retired-navigation-migration.test.cjs"), 0)
        with (ROOT / "data/swiftlook_plan.csv").open(newline="") as stream:
            reader = csv.DictReader(stream)
            self.assertIn("task", reader.fieldnames)
            self.assertTrue(list(reader))

    def test_pipeline_pages_are_bounded_and_support_full_universe_search(self):
        self.assertGreater(run_frontend_contract("workspace-pages.test.cjs"), 0)

    def test_pipeline_stage_date_cap_and_search_filters_reconcile(self):
        self.assertGreater(run_frontend_contract("pipeline-data.test.cjs"), 0)
        self.assertGreater(run_frontend_contract("trial-filters.test.cjs"), 0)

    def test_watch_trade_navigation_preserves_permanent_program_selections(self):
        self.assertGreater(run_frontend_contract("retired-navigation-migration.test.cjs"), 0)
        self.assertGreater(run_backend_contract("test_permanent_program_ids.py"), 0)

    def test_retired_phase3_bookmarks_do_not_recreate_the_old_dashboard(self):
        self.assertGreater(run_frontend_contract("retired-navigation-migration.test.cjs"), 0)

    def test_gem_jr_and_gem_remain_distinct_qualification_contracts(self):
        self.assertGreater(run_frontend_contract("gem-original-checkbox-groups.test.cjs"), 0)
        self.assertGreater(run_frontend_contract("gem-research-defaults.test.cjs"), 0)

    def test_retired_combined_gem_layout_cannot_merge_stage_associations(self):
        self.assertGreater(run_frontend_contract("retired-navigation-migration.test.cjs"), 0)
        self.assertGreater(run_frontend_contract("restrictions-central-placement.test.cjs"), 0)

    def test_missing_science_never_becomes_a_success_probability(self):
        self.assertGreater(run_frontend_contract("decision-assessment-adapter.test.cjs"), 0)
        self.assertGreater(run_frontend_contract("numeric-forecast-metrics.test.cjs"), 0)

    def test_trial_specific_clinical_scores_retain_missing_and_dated_sources(self):
        self.assertGreater(run_frontend_contract("candidate-assessments.test.cjs"), 0)
        self.assertGreater(run_backend_contract("test_trial_qualification.py"), 0)

    def test_old_prephase3_links_fall_back_without_inventing_a_legacy_screen(self):
        self.assertGreater(run_frontend_contract("retired-navigation-migration.test.cjs"), 0)


if __name__ == "__main__":
    unittest.main()
