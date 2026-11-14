"""End-to-end read-only FOCUS preview from actual collected original registry receipts.

All tests run without network or live reviewer credentials.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/medical/level16_offline_research_preview.py"
spec = importlib.util.spec_from_file_location("level16_offline_research_preview", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    return tuple(json.loads(path.read_text(encoding="utf-8")) for path in (
        module.RESEARCH, module.COVERAGE, module.ROSTER,
        module.APPLICATIONS, module.DEFINITIONS, module.ORCA2,
    ))


class OriginalRegistryOfflinePreviewTests(unittest.TestCase):
    def setUp(self):
        self.research, self.coverage, self.roster, self.apps, self.defs, self.orca = fixture()

    def build(self):
        return module.build(self.research, self.coverage, self.roster,
                            self.apps, self.defs, self.orca)

    def test_actual_collected_registry_provides_phase_instead_of_empty_checkpoint(self):
        html, receipt = self.build()
        self.assertEqual(receipt["focusTrialCount"], 32)
        self.assertEqual(receipt["originalRegistryFieldsCapturedUnreviewed"], 32)
        self.assertEqual(receipt["independentSourceAuthentications"], 0)
        self.assertEqual(receipt["scientificallyAdjudicatedLevels"], 0)
        self.assertEqual(receipt["fdaForecasts"], 0)
        self.assertFalse(receipt["stagingActivated"])
        self.assertEqual(html.count("Owner-only assessment handoff — OWNER NOT REVIEWED"), 192)
        self.assertIn("Registry phase/status (captured, NOT verified)", html)
        self.assertIn("PHASE3", html)
        self.assertIn("Hochberg", html)
        self.assertIn("PRELIMINARY RESEARCH — NOT INDEPENDENTLY REVIEWED", html)
        self.assertIn("32</strong><small>FOCUS exact NCT trials", html)
        self.assertIn("NOT MEDICAL ASSESSMENTS OR FDA FORECASTS", html)

    def test_original_receipt_source_digest_swap_fails_closed(self):
        self.research["trials"][0]["registrySource"]["documentSha256"] = "b" * 64
        with self.assertRaises(ValueError):
            self.build()

    def test_rejects_cross_trial_coverage_and_phase_tampering(self):
        self.coverage["trials"][0]["phaseUnreviewed"] = ["PHASE1"]
        with self.assertRaises(ValueError):
            self.build()
        self.coverage, self.research = fixture()[1], fixture()[0]
        self.coverage["trials"][0]["ticker"] = "WRONG"
        with self.assertRaises(ValueError):
            self.build()

    def test_missing_registry_record_cannot_be_reported_as_full_capture(self):
        self.research["trials"][0]["registrySource"] = None
        with self.assertRaises((ValueError, KeyError, TypeError)):
            self.build()

    def test_rejects_substituted_scientific_signoff_or_prospective_predictions(self):
        for key, value in (
            ("actualAuthenticatedSources", 1),
            ("actualIndependentAssessments", 1),
            ("historicalPredictionInputPermitted", True),
            ("prospectiveBlindAssessment", True),
        ):
            research = copy.deepcopy(self.research)
            research[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.build(research, self.coverage, self.roster, self.apps,
                             self.defs, self.orca)

    def test_rejects_mismatched_cutoff_or_missing_original_provisional_crosswalk(self):
        self.coverage["evidenceCutoffDate"] = "2026-11-13"
        with self.assertRaises(ValueError):
            self.build()
        self.coverage, self.apps = fixture()[1], fixture()[3]
        self.apps["records"].pop()
        with self.assertRaises(ValueError):
            self.build()

    def test_cli_writes_single_local_output_without_overwriting_or_network(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preview.html"
            command = [sys.executable, str(SCRIPT), "--output", str(output)]
            run = subprocess.run(command, capture_output=True, text=True,
                                 cwd=ROOT, timeout=40, check=True)
            details = json.loads(run.stdout)
            self.assertEqual(details["focusTrialCount"], 32)
            self.assertEqual(details["scientificallyAdjudicatedLevels"], 0)
            self.assertTrue(output.exists())
            self.assertIn("PHASE3", output.read_text(encoding="utf-8"))
            repeated = subprocess.run(command, capture_output=True, text=True,
                                      cwd=ROOT, timeout=40)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("FileExistsError", repeated.stderr)


if __name__ == "__main__":
    unittest.main()
