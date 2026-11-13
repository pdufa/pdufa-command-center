"""Integration tests for the existing nightly FOCUS source monitor review extension."""
import datetime as dt
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from focus_nightly_l6_review import (
    build_assessment_readiness, clinical_components, write_step_summary, main,
    REQUIRED_HEADERS,
)


def setup():
    header = [""] * 31
    for i, label in REQUIRED_HEADERS.items():
        header[i] = label
    def row(ticker, nct, scores, fda_date="NDA filing planned 2027"):
        v = [""] * 31
        v[0], v[1], v[2], v[6], v[7] = ticker, nct, ticker+" Inc", "COMPLETED", "YES"
        v[9], v[10] = f"https://clinicaltrials.gov/study/{nct}", "2026-11-12"
        v[15] = scores
        v[22] = "POST-P3 / filing planned" if "planned" in fda_date else "FDA NDA review"
        v[26] = 900000000
        v[28] = fda_date
        v[30] = "https://source.example"
        return v
    src = "CLINICAL_FIVE: post-1-1:75; post-1-2:75; post-1-3:50; post-1-4:50; post-1-5:50"
    missing = "CLINICAL_FIVE: post-1-1:75; post-1-2:MISSING_EVIDENCE; post-1-3:50; post-1-4:50; post-1-5:NOT_REPORTED"
    rows = [
        row("AAA", "NCT12345678", src, "2026-11-20"),
        row("BBB", "NCT87654321", missing),
        row("CCC", "NCT11112222", ""),
    ]
    roster = {"schemaVersion": 1, "records": [
        {"ticker": "AAA", "nct": "NCT12345678"},
        {"ticker": "BBB", "nct": "NCT87654321"},
    ]}
    monitor = {"schemaVersion": 1, "trials": [
        {"ticker": "AAA", "nct": "NCT12345678", "sourceStatus": "OFFICIAL_REGISTRY_RETRIEVED",
         "phase": ["PHASE3"], "delta": "REGISTRY_EVIDENCE_CHANGED",
         "applicationCycles": ["app-a"]},
        {"ticker": "BBB", "nct": "NCT87654321", "sourceStatus": "OFFICIAL_REGISTRY_RETRIEVED",
         "phase": ["PHASE3"], "delta": "NO_REGISTRY_EVIDENCE_CHANGE",
         "applicationCycles": ["app-b"]},
    ]}
    return [header, *rows], roster, monitor


class LiveReadinessTests(unittest.TestCase):
    def test_live_sheet_3_repo_2_mismatch_does_not_skip_trial(self):
        sheet, roster, monitor = setup()
        report = build_assessment_readiness(sheet, roster, monitor, dt.date(2026, 11, 12))
        s = report["summary"]
        self.assertEqual(s["liveFocusNcts"], 3)
        self.assertEqual(s["savedGithubRosterNcts"], 2)
        self.assertEqual(s["fiveClinicalFactors"], 1)
        self.assertEqual(s["partialClinicalFactors"], 1)
        self.assertEqual(s["noClinicalFactors"], 1)
        self.assertEqual(s["liveSheetOnlyNcts"], 1)
        self.assertEqual(s["notVerifiedInCurrentRegistryScan"], 1)
        self.assertEqual(s["registryPhase3UnverifiedNcts"], 1)
        self.assertEqual(report["rosterMismatchReview"]["newInLiveSheet"], ["NCT11112222"])
        self.assertEqual([r["review_order"] for r in report["assessments"]], [1, 2, 3])
        self.assertEqual({r["nct"] for r in report["assessments"]},
                         {"NCT12345678", "NCT87654321", "NCT11112222"})
        self.assertEqual(s["nearFdaDateUnverifiedCount"], 1)

    def test_missing_components_are_never_imputed_or_l6_certified(self):
        sheet, roster, monitor = setup()
        report = build_assessment_readiness(sheet, roster, monitor, dt.date(2026, 11, 12))
        by_nct = {r["nct"]: r for r in report["assessments"]}
        self.assertEqual(by_nct["NCT12345678"]["fully_observed_clinical_five_100"], 60)
        partial = by_nct["NCT87654321"]
        self.assertEqual(partial["component_coverage"], "3/5")
        self.assertIsNone(partial["fully_observed_clinical_five_100"])
        self.assertIsNone(partial["scientific_score_100"])
        self.assertIsNone(partial["fda_probability"])
        zero = by_nct["NCT11112222"]
        self.assertIsNone(zero["observed_only_mean_100"])
        self.assertEqual(zero["missing_component_indices"], [1, 2, 3, 4, 5])
        self.assertEqual(report["validatedLevel6OverallScores"], 0)
        self.assertEqual(report["blindProspectivePredictionsProduced"], 0)

    def test_changed_evidence_is_classified_for_review_not_prediction(self):
        sheet, roster, monitor = setup()
        out = build_assessment_readiness(sheet, roster, monitor, dt.date(2026, 11, 12))
        self.assertEqual(out["summary"]["evidenceChangedNcts"], 1)
        self.assertTrue(all(r["requires_review"] for r in out["assessments"]))
        self.assertTrue(all(r["genuine_blind_prediction"] is False for r in out["assessments"]))
        self.assertEqual(out["summary"]["independentScientificSignoffs"], 0)
        self.assertEqual(out["summary"]["automatedAssessmentDecisions"], 0)

    def test_bad_source_identity_fails_closed(self):
        sheet, roster, monitor = setup()
        sheet[1][9] = "https://clinicaltrials.gov/study/NCT00000000"
        with self.assertRaisesRegex(ValueError, "EXACT_NCT"):
            build_assessment_readiness(sheet, roster, monitor, dt.date(2026, 11, 12))

    def test_changed_header_fails_closed(self):
        sheet, roster, monitor = setup()
        sheet[0][15] = "All FDA predictions"
        with self.assertRaisesRegex(ValueError, "HEADER_SCHEMA"):
            build_assessment_readiness(sheet, roster, monitor, dt.date(2026, 11, 12))

    def test_ticker_mismatch_fails_closed(self):
        sheet, roster, monitor = setup()
        monitor["trials"][1]["ticker"] = "WRONG"
        with self.assertRaisesRegex(ValueError, "TICKER_MISMATCH"):
            build_assessment_readiness(sheet, roster, monitor, dt.date(2026, 11, 12))

    def test_all_unknown_factors_blank_not_zero(self):
        self.assertEqual(clinical_components(""), [None] * 5)

    def test_duplicate_factor_rejected(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CLINICAL"):
            clinical_components("CLINICAL_FIVE: post-1-1:50; post-1-1:75; post-1-2:50; post-1-3:50; post-1-4:50; post-1-5:50")

    def test_unapproved_factor_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNRECOGNIZED_COMPONENT"):
            clinical_components("CLINICAL_FIVE: post-1-1:87; post-1-2:50; post-1-3:50; post-1-4:50; post-1-5:50")

    def test_public_ci_summary_contains_counts_not_individual_grades(self):
        sheet, roster, monitor = setup()
        report = build_assessment_readiness(sheet, roster, monitor, dt.date(2026, 11, 12))
        with tempfile.TemporaryDirectory() as t:
            output = Path(t) / "summary.md"
            with patch.dict("os.environ", {"GITHUB_STEP_SUMMARY": str(output)}):
                write_step_summary(report)
            body = output.read_text()
        self.assertIn("liveFocusNcts: 3", body)
        self.assertNotIn("NCT12345678", body)
        self.assertNotIn("source_components", body)
        self.assertNotIn("75", body)

    def test_source_explicitly_labels_future_regulatory_reviews_not_expected(self):
        sheet, roster, monitor = setup()
        r = build_assessment_readiness(sheet, roster, monitor, dt.date(2026, 11, 12))
        by_nct = {e["nct"]: e for e in r["assessments"]}
        self.assertEqual(by_nct["NCT87654321"]["missing_regulatory_conclusion_class"],
                         "FUTURE_FDA_REVIEW_FINDINGS_NOT_YET_EXPECTED")


if __name__ == "__main__":
    unittest.main()
