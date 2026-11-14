"""Review-worklist integration: no unverified clinical signoff or live writes."""
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
SCRIPT = ROOT / "scripts/medical/level16_change_review_worklist.py"
spec = importlib.util.spec_from_file_location("level16_change_review_worklist", SCRIPT)
worklist = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worklist)
RESEARCH = ROOT / "reports/scientific-levels1-6/focus-source-research-20261114.json"


def fixture():
    return json.loads(RESEARCH.read_text(encoding="utf-8"))


def change_candidate(candidate, nct="NCT04576949", phase=None):
    """Synthetic metadata-only change, not proof of actual registry alteration."""
    row = next(row for row in candidate["trials"] if row["nct"] == nct)
    source = row["registrySource"]
    digest = "a" * 64 if source["documentSha256"] != "a" * 64 else "b" * 64
    source["documentSha256"] = digest
    source["capturedRegistry"]["sha256"] = digest
    old_time = datetime.fromisoformat(source["retrievedAt"].replace("Z", "+00:00"))
    source["retrievedAt"] = (old_time + timedelta(microseconds=1)).isoformat()
    for level in row["levels"]:
        for finding in level.get("preliminaryFindings", []):
            if finding.get("sourceUrl") == source["sourceUrl"]:
                finding["documentSha256"] = digest
    if phase is not None:
        source["phasesUnreviewed"] = phase
        source["capturedRegistry"]["fields"]["phase"]["value"] = phase
    return row


class OfflineReviewWorklistTests(unittest.TestCase):
    def setUp(self):
        self.candidate = fixture()

    def test_identical_snapshot_has_32_trials_192_unadjudicated_levels(self):
        report = worklist.build(self.candidate)
        self.assertEqual(report["focusTrialCount"], 32)
        self.assertEqual(report["reviewLevelsPerTrial"], 6)
        self.assertEqual(len(report["trials"]), 32)
        self.assertEqual(sum(len(row["levels"]) for row in report["trials"]), 192)
        self.assertEqual(report["changedTrialsRequiringReview"], 0)
        self.assertEqual(report["changedLevelsRequiringReview"], 0)
        self.assertEqual(report["independentSourceAuthentications"], 0)
        self.assertEqual(report["independentlyAdjudicatedLevels"], 0)
        self.assertEqual(report["authorizedReviewerCount"], 0)
        self.assertEqual(report["fdaPredictionsProduced"], 0)
        self.assertFalse(report["protectedReviewEventsWritten"])
        self.assertFalse(report["liveReassessmentScheduled"])
        self.assertFalse(report["stagingActivated"])
        for row in report["trials"]:
            self.assertFalse(row["requiresManualCurrentEvidenceReview"])
            self.assertEqual(row["worklistStatus"],
                             "NO_NEW_CHANGE_DETECTED_EXISTING_REVIEWS_NOT_VERIFIED")
            for level in row["levels"]:
                self.assertFalse(level["registryEvidenceChangeDetected"])
                self.assertIsNone(level["approvalProbability"])
                self.assertIsNone(level["score"])
                self.assertEqual(level["scientificReviewStatus"], "NOT_ADJUDICATED")

    def test_new_document_bytes_require_six_manual_reviews_and_orca2_priority(self):
        change_candidate(self.candidate)
        report = worklist.build(self.candidate)
        self.assertEqual(report["changedTrialsRequiringReview"], 1)
        self.assertEqual(report["changedLevelsRequiringReview"], 6)
        first = report["trials"][0]
        self.assertEqual(first["nct"], "NCT04576949")
        self.assertEqual(first["affectedLevels"], list(range(1, 7)))
        self.assertTrue(first["requiresManualCurrentEvidenceReview"])
        self.assertEqual(first["worklistStatus"],
                         "NEW_UNREVIEWED_EVIDENCE_BLOCKED_PENDING_AUTHORIZATION")
        for level in first["levels"]:
            self.assertTrue(level["registryEvidenceChangeDetected"])
            self.assertTrue(level["originalEvidenceReverificationNeeded"])
            self.assertFalse(level["reviewerIdentityApproved"])
            self.assertEqual(level["scientificReviewStatus"], "NOT_ADJUDICATED")
            self.assertEqual(level["independentChallengeStatus"], "NOT_COMPLETED")
            self.assertEqual(level["adjudicationStatus"], "NOT_COMPLETED")
        self.assertEqual(report["independentlyAdjudicatedLevels"], 0)

    def test_changed_phase_never_inherits_old_adjudication_or_prediction(self):
        change_candidate(self.candidate, phase=["PHASE2"])
        report = worklist.build(self.candidate)
        first = report["trials"][0]
        self.assertIn("CAPTURED_PHASESUNREVIEWED_DIFF", first["triggerReasons"])
        for level in first["levels"]:
            self.assertFalse(level["reviewerIdentityApproved"])
            self.assertEqual(level["sourceReviewStatus"], "NOT_INDEPENDENTLY_AUTHENTICATED")
            self.assertIsNone(level["fdaOutcomeJudgment"])
        self.assertFalse(report["liveReassessmentScheduled"])

    def test_changed_unmapped_nct_remains_unmapped(self):
        change_candidate(self.candidate, nct="NCT05031780")
        report = worklist.build(self.candidate)
        trial = next(x for x in report["trials"] if x["nct"] == "NCT05031780")
        self.assertEqual(trial["applicationMappingStatus"], "NOT_MAPPED_APPLICATION_CYCLE")
        self.assertEqual(trial["affectedLevels"], list(range(1, 7)))
        self.assertEqual(report["changedTrialsRequiringReview"], 1)

    def test_denies_forged_independent_source_and_reviewer_metadata(self):
        for key, val in (
            ("actualAuthenticatedSources", 1),
            ("actualIndependentAssessments", 1),
            ("prospectiveBlindAssessment", True),
            ("historicalPredictionInputPermitted", True),
        ):
            altered = copy.deepcopy(self.candidate)
            altered[key] = val
            with self.subTest(key=key), self.assertRaises(ValueError):
                worklist.build(altered)

    def test_cross_nct_and_unapproved_application_cycle_rejected(self):
        altered = copy.deepcopy(self.candidate)
        altered["trials"][0]["nct"] = "NCT99999999"
        with self.assertRaises(ValueError):
            worklist.build(altered)
        altered = copy.deepcopy(self.candidate)
        altered["trials"][0]["candidateApplicationCycleIdsUnverified"] = [
            "invented-application-cycle"]
        with self.assertRaises(ValueError):
            worklist.build(altered)

    def test_regression_blocks_backdated_retrieval_and_modified_fields_same_digest(self):
        altered = copy.deepcopy(self.candidate)
        item = next(x for x in altered["trials"] if x["nct"] == "NCT04576949")
        t = datetime.fromisoformat(item["registrySource"]["retrievedAt"].replace(
            "Z", "+00:00"))
        item["registrySource"]["retrievedAt"] = (t - timedelta(days=2)).isoformat()
        with self.assertRaises(ValueError):
            worklist.build(altered)
        altered = copy.deepcopy(self.candidate)
        item = next(x for x in altered["trials"] if x["nct"] == "NCT04576949")
        item["registrySource"]["studyStatusUnreviewed"] = "SUSPENDED"
        with self.assertRaises(ValueError):
            worklist.build(altered)

    def test_caller_cannot_substitute_frozen_baseline(self):
        altered_baseline = copy.deepcopy(fixture())
        altered_baseline["evidenceCutoffDate"] = "2026-11-15"
        with self.assertRaises(ValueError):
            worklist.build(self.candidate, baseline=altered_baseline)

    def test_cli_is_read_only_and_produces_json_without_network(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--candidate", str(RESEARCH)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=45)
        report = json.loads(result.stdout)
        self.assertEqual(report["focusTrialCount"], 32)
        self.assertEqual(report["changedTrialsRequiringReview"], 0)
        self.assertFalse(report["protectedReviewEventsWritten"])
        self.assertFalse(report["stagingActivated"])


if __name__ == "__main__":
    unittest.main()
