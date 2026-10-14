"""GEM retains 11 surveys and two mandatory eligibility benchmarks."""
import unittest
from gem_survey_catalog import SURVEYS, survey_rows


class GemSurveyDirectoryTests(unittest.TestCase):
    def test_numbered_directory_no_longer_contains_approval_probability(self):
        self.assertEqual(len(SURVEYS), 11)
        self.assertEqual([row[0] for row in SURVEYS], list(range(1, 12)))
        self.assertEqual([row[2] for row in SURVEYS[:2]], [
            "Entry benchmark 1", "Entry benchmark 2"])
        self.assertEqual(SURVEYS[-1][1], "BiopharmaWatch Comparison")
        self.assertTrue(all("Approval Probability" not in row[1] for row in SURVEYS))

    def test_coverage_is_observation_not_signal_and_preserves_unknown(self):
        data={"schema_version": 1,
              "same_input_score_comparison_performed": False,
              "capability_matrix": [
                  {"key": "clinical", "state": "PARTIAL",
                   "observed_gem_rows": 1, "total_gem_rows": 368},
                  {"key": "financing", "state": "CUSTOM",
                   "observed_gem_rows": 0, "total_gem_rows": 368},
                  {"key": "market_cap", "state": "PARTIAL",
                   "observed_gem_rows": 358, "total_gem_rows": 368},
              ]}
        rows=survey_rows(data)
        self.assertEqual(rows[0]["Verified coverage"], "1 / 368 program rows")
        self.assertEqual(rows[1]["Verified coverage"], "0 / 368 program rows")
        self.assertEqual(rows[8]["Verified coverage"], "358 / 368 program rows")
        self.assertEqual(rows[9]["Verified coverage"], "NOT VERIFIED")
        self.assertEqual(rows[-1]["Source status"], "AVAILABLE — COVERAGE AUDIT")
        self.assertEqual(len(rows), 11)

    def test_unverified_audit_never_claims_source_coverage(self):
        rows=survey_rows({})
        self.assertTrue(all(r["Verified coverage"] == "NOT VERIFIED"
                            for r in rows[:-1]))
        self.assertEqual(rows[-1]["Source status"], "PENDING — NO CURRENT AUDIT")


if __name__ == "__main__":
    unittest.main()
