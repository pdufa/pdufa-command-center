"""Fail-closed tests for full-population RAAS coverage and lossless census reconciliation."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/raas_population_coverage_audit.py"
spec = importlib.util.spec_from_file_location("raas_population_coverage_audit", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class RaasPopulationCoverageAuditTests(unittest.TestCase):
    def test_original_is_pinned_and_evolving_is_preserved(self):
        pinned = mod.parse_census(mod.PINNED)
        evolving = mod.parse_census(mod.EVOLVING)
        self.assertEqual(len(pinned), 741)
        self.assertTrue(len(evolving) >= 1)
        self.assertIn("new-platform/frontend/public/phase3-census-2026-10-26.csv",
                      str(mod.PINNED))
        self.assertNotEqual(mod.PINNED, mod.EVOLVING)
        self.assertTrue(all(r["source_url"].endswith(nct)
                            for nct,r in pinned.items()))
        self.assertTrue(all(r["source_url"].endswith(nct)
                            for nct,r in evolving.items()))
        check = (ROOT / "scripts/check_phase3_original_registry_pilot.py").read_text()
        self.assertIn("new-platform/frontend/public/phase3-census-2026-10-26.csv", check)
        self.assertIn('len(rows) != 741', check)

    def test_all_741_are_assessed_with_missingness_not_invented_ratings(self):
        pinned=mod.parse_census(mod.PINNED)
        evolving=mod.parse_census(mod.EVOLVING)
        stages=mod.source_readouts(mod.READOUT, pinned)
        self.assertEqual(len(stages), 10)
        self.assertEqual(sum(x == "TOP" for x in stages.values()), 2)
        self.assertEqual(sum(x == "BOTTOM" for x in stages.values()), 8)
        grades=mod.source_grades(mod.HISTORY, stages)
        result=mod.coverage_snapshot(pinned, evolving, stages, grades)
        historical=result["historicalCensus"]
        research=result["evolvingResearch"]
        self.assertEqual(historical["trials"],741)
        self.assertEqual(len(historical["records"]),741)
        self.assertEqual(historical["approvedOverallScored"],0)
        self.assertEqual(historical["top"],2)
        self.assertEqual(historical["bottom"],8)
        self.assertEqual(historical["unverified"],731)
        self.assertEqual(sum(x["approvedOverallScore"] is not None for x in historical["records"]),0)
        self.assertTrue(all(x["pdufaQualified"] is None for x in historical["records"]))
        self.assertEqual(research["trials"],len(evolving))
        self.assertEqual(result["reconciliation"]["preservedOriginalNctCount"],741)
        self.assertEqual(result["reconciliation"]["evolvingNctCount"],len(evolving))
        self.assertEqual(result["reconciliation"]["addedToEvolving"],
          sorted(set(evolving)-set(pinned)))
        self.assertEqual(result["reconciliation"]["missingFromEvolving"],
          sorted(set(pinned)-set(evolving)))
        self.assertTrue(all(x["metricGradesMissing"] is None
              for x in historical["records"] if x["readoutStage"]=="UNVERIFIED"))

    def test_source_grade_requires_real_as_saved_metric_event(self):
        stages=mod.source_readouts(mod.READOUT,mod.parse_census(mod.PINNED))
        event={
            "eventId":"abcd", "kind":"METRIC_SCORE_UPDATED",
            "nctId":"NCT07363577","stage":"pre",
            "scoreKind":"UNSCORED","score":None,
            "recordedAt":"2026-11-04T13:00:00.000Z",
            "metricGrades":[{"metricId":"pre-4-1", "score":50,
                "ruleId":"timing-specificity-exploratory-v1",
                "sourceDate":"2026-07-22",
                "sourceUrl":"https://ir.example.com/issuer"}]
        }
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"history.json"
            path.write_text(json.dumps({
                "schemaVersion":1,"scope":"RAAS_TRIAL_SCORE_HISTORY",
                "records":[event]}))
            grades=mod.source_grades(path,stages)
            self.assertEqual(grades[("NCT07363577","pre-4-1")]["score"],50)
            self.assertEqual(grades[("NCT07363577","pre-4-1")]["scoreType"],
                             "EXPERIMENTAL_NOT_VALIDATED")
            event["scoreKind"]="VALIDATED"
            path.write_text(json.dumps({"schemaVersion":1,
                  "scope":"RAAS_TRIAL_SCORE_HISTORY","records":[event]}))
            with self.assertRaisesRegex(ValueError, "Cross-trial or composite"):
                mod.source_grades(path,stages)
            # An archived TOP metric must not be applied to the same trial's
            # current BOTTOM scoring while its history survives.
            event["scoreKind"]="UNSCORED"
            path.write_text(json.dumps({"schemaVersion":1,
                  "scope":"RAAS_TRIAL_SCORE_HISTORY","records":[event]}))
            changed={**stages,"NCT07363577":"BOTTOM"}
            self.assertEqual(mod.source_grades(path,changed),{})

    def test_corrupted_or_duplicate_inventory_fails_closed(self):
        rows=list(mod.parse_census(mod.PINNED).values())
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"invalid.csv"
            def write(r):
                with p.open("w",newline="") as out:
                    writer=csv.DictWriter(out,fieldnames=mod.HEADER)
                    writer.writeheader();writer.writerows(r)
            write(rows+[rows[0]])
            with self.assertRaisesRegex(ValueError,"Invalid or duplicate"):
                mod.parse_census(p)
            write([{**rows[0],"source_url":"https://example.org/fake"}])
            with self.assertRaisesRegex(ValueError,"Invalid or duplicate"):
                mod.parse_census(p)
            write([{**rows[0],"status":"APPROVED"}])
            with self.assertRaisesRegex(ValueError,"Invalid or duplicate"):
                mod.parse_census(p)


if __name__ == "__main__":
    unittest.main()
