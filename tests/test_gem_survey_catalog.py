"""Seven primary GEM surveys; historical and BPW work is optional diagnostics."""
import unittest
from gem_survey_catalog import SURVEYS, RESEARCH_DIAGNOSTICS, survey_rows


class GemSurveyDirectoryTests(unittest.TestCase):
    def test_seven_primary_surveys_only_two_benchmarks(self):
        self.assertEqual(len(SURVEYS), 7)
        self.assertEqual([row[0] for row in SURVEYS], list(range(1, 8)))
        self.assertEqual([row[2] for row in SURVEYS[:2]], [
            "Entry benchmark 1", "Entry benchmark 2"])
        names = [row[1] for row in SURVEYS]
        self.assertEqual(names[4], "Ownership & Insider Activity")
        self.assertTrue(all(x not in names for x in (
            "Company Valuation", "Historical Price Performance",
            "BiopharmaWatch Comparison", "Insider Trading",
            "FDA Approval Probability",
        )))
        self.assertEqual(len(RESEARCH_DIAGNOSTICS), 2)

    def test_combined_ownership_coverage_keeps_13f_and_form4_separate(self):
        data = {
            "schema_version": 1, "same_input_score_comparison_performed": False,
            "capability_matrix": [
                {"key": "clinical", "state": "PARTIAL",
                 "observed_gem_rows": 1, "total_gem_rows": 368},
                {"key": "financing", "state": "CUSTOM",
                 "observed_gem_rows": 0, "total_gem_rows": 368},
                {"key": "hedge", "state": "PARTIAL",
                 "observed_gem_rows": 70, "total_gem_rows": 368},
                {"key": "insider", "state": "PARTIAL",
                 "observed_gem_rows": 55, "total_gem_rows": 368},
            ],
        }
        rows = survey_rows(data)
        self.assertEqual(rows[0]["Verified coverage"], "1 / 368 program rows")
        self.assertEqual(rows[1]["Verified coverage"], "0 / 368 program rows")
        self.assertEqual(rows[4]["Verified coverage"],
                         "13F: 70 / 368 program rows · Form 4: 55 / 368 program rows")
        self.assertIn("13F: PARTIAL", rows[4]["Source status"])
        self.assertIn("Form 4: PARTIAL", rows[4]["Source status"])
        self.assertEqual(rows[5]["Verified coverage"], "NOT VERIFIED")
        self.assertEqual(len(rows), 7)

    def test_missing_insider_never_infers_unique_ownership_coverage(self):
        data = {"schema_version": 1,
                "same_input_score_comparison_performed": False,
                "capability_matrix": [{"key": "hedge", "state": "PARTIAL",
                                      "observed_gem_rows": 3, "total_gem_rows": 8}]}
        record = survey_rows(data)[4]
        self.assertEqual(record["Verified coverage"],
                         "13F: 3 / 8 program rows · Form 4: NOT VERIFIED")

    def test_unverified_diagnostic_does_not_assert_current_survey_coverage(self):
        rows = survey_rows({})
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(r["Verified coverage"] == "NOT VERIFIED" for r in rows))
        self.assertTrue(all(r["Source status"] == "NOT VERIFIED" for r in rows))


if __name__ == "__main__":
    unittest.main()
