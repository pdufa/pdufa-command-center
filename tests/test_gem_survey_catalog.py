"""Seven primary GEM surveys; historical and BPW work is optional diagnostics."""
import unittest
from gem_survey_catalog import SURVEYS, RESEARCH_DIAGNOSTICS, survey_rows


class GemSurveyDirectoryTests(unittest.TestCase):
    def test_seven_primary_surveys_with_optional_second_financing(self):
        self.assertEqual(len(SURVEYS), 7)
        self.assertEqual([row[0] for row in SURVEYS], list(range(1, 8)))
        self.assertEqual([row[2] for row in SURVEYS[:2]], [
            "Entry benchmark 1", "Optional financing / dilution evidence"])
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

    def test_daily_seven_surveys_use_saved_pipeline_scoped_gem_rows(self):
        sample = [
            {"Benchmark 1 — Phase 3 released": "PASS — VERIFIED RESULTS RELEASE",
             "Benchmark 2 — Financing #2 closed": "PASS — TWO POST-READOUT CLOSES",
             "Cash runway (months)": 14,
             "Cash runway gate": "PASS — 12 MONTHS",
             "GEM 3 dilution status": "ALERT — FINANCING TERMS NEED REVIEW",
             "Hedge-fund signal": "SOURCE-VERIFIED QUARTERLY 13F HOLDINGS",
             "Insider Form 4 signal": "",
             "Market activity /10": 6,
             "Rating status": "RATED",
             "PDUFA verification": "VERIFIED — SOURCE LINKED"},
            {"Benchmark 1 — Phase 3 released": "PENDING",
             "Benchmark 2 — Financing #2 closed": "PENDING",
             "Hedge-fund signal": "", "Insider Form 4 signal":
             "SOURCE-VERIFIED SEC FORM 4 OBSERVATIONS"},
        ]
        rows = survey_rows({}, scans=sample, feed_current=True)
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0]["Verified coverage"], "1 / 2 program rows")
        self.assertEqual(rows[1]["Verified coverage"], "1 / 2 program rows")
        self.assertEqual(rows[3]["Verified coverage"], "1 / 2 program rows")
        self.assertEqual(rows[4]["Verified coverage"],
                         "13F: 1 / 2 program rows · Form 4: 1 / 2 program rows")
        self.assertEqual(rows[6]["Verified coverage"], "1 / 2 program rows")
        self.assertEqual(rows[4]["Role"], "Advisory / ranking")
        stale = survey_rows({}, scans=sample, feed_current=False)
        self.assertIn("STALE SOURCE FEED", stale[0]["Source status"])
        self.assertEqual(survey_rows({}, scans=[], feed_current=True)[0]
                         ["Source status"], "NOT VERIFIED / NO MATCHED OBSERVATIONS")

    def test_research_diagnostics_have_no_nightly_critical_path(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        main = (root / ".github/workflows/gem-research-quality.yml").read_text()
        optional = (root / ".github/workflows/gem-research-diagnostics.yml").read_text()
        ui = (root / "gem_scans_ui.py").read_text()
        self.assertNotIn("run_gem_bpw_comparable.py", main)
        self.assertNotIn("steps.bpw_comparable.outcome", main)
        self.assertIn("collect_gem_hedge_funds.py", main)
        self.assertIn("collect_gem_insider_form4.py", main)
        self.assertIn("run_gem_bpw_comparable.py", optional)
        self.assertIn("workflow_dispatch:", optional)
        self.assertNotIn("schedule:", optional)
        self.assertIn("GEM SURVEY DIRECTORY — 7 PRIMARY SURVEYS", ui)
        self.assertIn("OWNERSHIP & INSIDER ACTIVITY — ADVISORY", ui)
        self.assertIn("SHOW HISTORICAL GEM BACKTEST / CALIBRATION", ui)
        self.assertIn("SHOW BIOPHARMAWATCH FEATURE-COVERAGE DIAGNOSTIC", ui)
        self.assertIn("survey_rows({}, scans=items,", ui)

    def test_unverified_diagnostic_does_not_assert_current_survey_coverage(self):
        rows = survey_rows({})
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(r["Verified coverage"] == "NOT VERIFIED" for r in rows))
        self.assertTrue(all(r["Source status"] == "NOT VERIFIED" for r in rows))


if __name__ == "__main__":
    unittest.main()
