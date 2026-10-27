"""Current candidate score and separate GEM qualification contracts.

The retired Streamlit dataframe column order is not a Next.js API. Actual React
rendering now verifies seven categories for each P/J/G model, actual zero versus
missing values, exact identities, dated citations and complete-score-only order.
"""
import unittest
from supported_dashboard_checks import run_frontend_contract, run_backend_contract


class FourPdufaScoreTabTests(unittest.TestCase):
    def test_all_current_ranking_models_expose_sources_and_missingness(self):
        self.assertGreater(run_frontend_contract("candidate-assessments.test.cjs"), 0)
        self.assertGreater(run_frontend_contract("numeric-forecast-metrics.test.cjs"), 0)

    def test_gem_jr_and_gem_keep_separate_qualification_and_source_contracts(self):
        self.assertGreater(run_frontend_contract("gem-original-checkbox-groups.test.cjs"), 0)
        self.assertGreater(run_frontend_contract("gem-research-defaults.test.cjs"), 0)
        self.assertGreater(run_backend_contract("test_trial_qualification.py"), 0)


if __name__ == "__main__":
    unittest.main()
