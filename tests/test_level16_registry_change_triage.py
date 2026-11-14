"""Exact-FOCUS, source-cutoff and anti-signoff tests for registry-change triage."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/medical/level16_registry_change_triage.py"
spec = importlib.util.spec_from_file_location("level16_registry_change_triage", SCRIPT)
triage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(triage)
RESEARCH = ROOT / "reports/scientific-levels1-6/focus-source-research-20261114.json"


def fixtures():
    return tuple(json.loads(path.read_text(encoding="utf-8")) for path in (
        RESEARCH, triage.ROSTER, triage.APPLICATIONS,
    ))


class RegistryChangeTriageTests(unittest.TestCase):
    def setUp(self):
        self.before, self.roster, self.apps = fixtures()
        self.after = copy.deepcopy(self.before)
        self.nct = "NCT04576949"

    def compare(self):
        return triage.compare(self.before, self.after, self.roster, self.apps)

    def change(self, nct=None, status=None, phase=None, posted_date=None):
        """Create synthetic new-receipt metadata, not real authenticated evidence."""
        nct = nct or self.nct
        row = next(x for x in self.after["trials"] if x["nct"] == nct)
        receipt = row["registrySource"]
        new_digest = "a" * 64 if receipt["documentSha256"] != "a" * 64 else "b" * 64
        receipt["documentSha256"] = new_digest
        receipt["capturedRegistry"]["sha256"] = new_digest
        old_retrieval = datetime.fromisoformat(receipt["retrievedAt"].replace("Z", "+00:00"))
        receipt["retrievedAt"] = (old_retrieval + timedelta(microseconds=1)).isoformat()
        for level in row["levels"]:
            for finding in level.get("preliminaryFindings", []):
                if finding.get("sourceUrl") == receipt["sourceUrl"]:
                    finding["documentSha256"] = new_digest
        if status is not None:
            receipt["studyStatusUnreviewed"] = status
            receipt["capturedRegistry"]["fields"]["studyOverallStatus"]["value"] = status
        if phase is not None:
            receipt["phasesUnreviewed"] = phase
            receipt["capturedRegistry"]["fields"]["phase"]["value"] = phase
        if posted_date is not None:
            receipt["registryPostedVersionDateUnreviewed"] = posted_date
        return row

    def test_unchanged_32_trial_baseline_is_no_new_source_not_complete_assessment(self):
        report = self.compare()
        self.assertEqual(report["focusTrialCount"], 32)
        self.assertEqual(report["changedTrialCount"], 0)
        self.assertEqual(report["unchangedTrialCount"], 32)
        self.assertEqual(report["independentlyAuthenticatedSources"], 0)
        self.assertEqual(report["independentlyAdjudicatedLevels"], 0)
        self.assertEqual(report["publishedFdaForecasts"], 0)
        self.assertFalse(report["historicalBlindPredictionPermitted"])
        self.assertTrue(report["doesNotModifyLiveReviewState"])
        self.assertTrue(all(not x["reassessmentTrigger"]
                            and not x["mayCarryOverPriorScientificSignoffAutomatically"]
                            for x in report["trials"]))

    def test_changed_original_bytes_trigger_all_six_levels_even_if_fields_same(self):
        self.change()
        report = self.compare()
        self.assertEqual(report["changedTrialCount"], 1)
        changed = next(x for x in report["trials"] if x["nct"] == self.nct)
        self.assertTrue(changed["reassessmentTrigger"])
        self.assertEqual(changed["affectedLevels"], list(range(1, 7)))
        self.assertIn("SOURCE_ORIGINAL_BYTES_DIFFER_RECEIPT_REVIEW_REQUIRED",
                      changed["triggerReasons"])
        self.assertEqual(changed["scientificReassessmentStatus"],
                         "BLOCKED_PENDING_INDEPENDENT_SOURCE_AND_DOMAIN_REVIEW")
        self.assertIsNone(changed["approvalProbability"])
        self.assertIsNone(changed["fdaOutcomeJudgment"])

    def test_phase_change_triggers_explicit_phase_specific_reassessment(self):
        self.change(phase=["PHASE2"])
        report = self.compare()
        changed = next(x for x in report["trials"] if x["nct"] == self.nct)
        self.assertIn("phasesUnreviewed", changed["fieldCategoriesChanged"])
        self.assertEqual(changed["affectedLevels"], list(range(1, 7)))
        self.assertNotIn("approvalProbability", changed["triggerReasons"])
        self.assertEqual(report["independentlyAdjudicatedLevels"], 0)

    def test_current_study_status_change_is_not_an_fda_decision(self):
        self.change(status="SUSPENDED")
        report = self.compare()
        changed = next(x for x in report["trials"] if x["nct"] == self.nct)
        self.assertIn("studyStatusUnreviewed", changed["fieldCategoriesChanged"])
        self.assertTrue(changed["reassessmentTrigger"])
        self.assertIsNone(changed["fdaOutcomeJudgment"])

    def test_different_extracted_fields_with_same_digest_are_rejected(self):
        trial = next(x for x in self.after["trials"] if x["nct"] == self.nct)
        trial["registrySource"]["studyStatusUnreviewed"] = "SUSPENDED"
        with self.assertRaises(ValueError):
            self.compare()
        self.after = copy.deepcopy(self.before)
        trial = next(x for x in self.after["trials"] if x["nct"] == self.nct)
        trial["registrySource"]["capturedRegistry"]["fields"]["studyOverallStatus"]["value"] = "SUSPENDED"
        with self.assertRaises(ValueError):
            self.compare()

    def test_older_posted_registry_version_triggers_specific_rollback_investigation(self):
        old = next(x for x in self.before["trials"] if x["nct"] == self.nct)
        previous_date = old["registrySource"]["registryPostedVersionDateUnreviewed"]
        if previous_date is None:
            self.skipTest("No original registry posted version date in current snapshot")
        earlier = (datetime.fromisoformat(previous_date) - timedelta(days=1)).date().isoformat()
        self.change(posted_date=earlier)
        report = self.compare()
        row = next(x for x in report["trials"] if x["nct"] == self.nct)
        self.assertIn("REGISTRY_POSTED_VERSION_ROLLBACK_REQUIRES_RECONCILIATION",
                      row["triggerReasons"])

    def test_candidate_earlier_retrieval_or_cutoff_is_rejected(self):
        row = next(x for x in self.after["trials"] if x["nct"] == self.nct)
        original = datetime.fromisoformat(row["registrySource"]["retrievedAt"].replace(
            "Z", "+00:00"))
        row["registrySource"]["retrievedAt"] = (original - timedelta(days=2)).isoformat()
        with self.assertRaises(ValueError):
            self.compare()
        self.after = copy.deepcopy(self.before)
        self.after["evidenceCutoffDate"] = "2026-11-13"
        with self.assertRaises(ValueError):
            self.compare()

    def test_cross_trial_identity_and_provisional_mapping_cannot_change(self):
        row = next(x for x in self.after["trials"] if x["nct"] == self.nct)
        row["ticker"] = "WRONG"
        with self.assertRaises(ValueError):
            self.compare()
        self.after = copy.deepcopy(self.before)
        row = next(x for x in self.after["trials"] if x["nct"] == self.nct)
        row["candidateApplicationCycleIdsUnverified"] = ["invented-cycle"]
        with self.assertRaises(ValueError):
            self.compare()

    def test_rejects_self_declared_authenticated_source_or_clinical_review(self):
        for key, value in (
            ("actualAuthenticatedSources", 1),
            ("actualIndependentAssessments", 1),
            ("prospectiveBlindAssessment", True),
            ("historicalPredictionInputPermitted", True),
        ):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.after)
                changed[key] = value
                with self.assertRaises(ValueError):
                    triage.compare(self.before, changed, self.roster, self.apps)

    def test_cli_compare_current_snapshot_with_itself_never_fetches_or_writes(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--baseline", str(RESEARCH),
             "--candidate", str(RESEARCH)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=30)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["changedTrialCount"], 0)
        self.assertEqual(payload["focusTrialCount"], 32)
        self.assertEqual(payload["independentlyAdjudicatedLevels"], 0)


if __name__ == "__main__":
    unittest.main()
