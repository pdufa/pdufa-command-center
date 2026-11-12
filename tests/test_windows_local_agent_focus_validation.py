"""The four-hour FOCUS queue status never overstates completed science."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
QUEUE = ROOT / "scripts" / "level2_focus_evidence_queue.py"
SPEC = importlib.util.spec_from_file_location("level2_focus_queue_for_job_tests", QUEUE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
from windows_local_agent_focus_validation import verify_queue_report


class ScheduledFocusValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "new-platform/frontend/data/p3PostDataActive.json").read_bytes()
        cls.report = MODULE.build_review_queue(json.loads(cls.raw))
        import hashlib
        cls.report["snapshot_sha256"] = hashlib.sha256(cls.raw).hexdigest()

    def test_exact_snapshot_generated_queue_passes(self):
        self.assertEqual(self.report["trial_count"], len(json.loads(self.raw)["records"]))
        self.assertTrue(verify_queue_report(self.report, self.raw))

    def test_modified_snapshot_is_not_reported_successful(self):
        altered = self.raw.replace(b"Abivax S.A.", b"Abivax Inc.", 1)
        self.assertNotEqual(self.raw, altered)
        self.assertFalse(verify_queue_report(self.report, altered))

    def test_completed_science_or_prediction_claim_is_rejected(self):
        for field, value in (
            ("level2_assessments_completed", 1),
            ("outcome_predictions_generated", 1),
            ("current_live_focus_membership_confirmed", True),
        ):
            with self.subTest(field=field):
                report = copy.deepcopy(self.report)
                report[field] = value
                self.assertFalse(verify_queue_report(report, self.raw))
        tampered = copy.deepcopy(self.report)
        tampered["records"][0]["hypothesis_review"]["scientifically_verified"] = True
        self.assertFalse(verify_queue_report(tampered, self.raw))

    def test_missing_trial_or_promoted_source_lead_is_rejected(self):
        shortened = copy.deepcopy(self.report)
        shortened["records"].pop()
        self.assertFalse(verify_queue_report(shortened, self.raw))
        promoted = copy.deepcopy(self.report)
        promoted["records"][0]["source_leads"][0]["status"] = "VERIFIED"
        self.assertFalse(verify_queue_report(promoted, self.raw))

    def test_tampered_snapshot_checksum_is_rejected(self):
        tampered = copy.deepcopy(self.report)
        tampered["snapshot_sha256"] = "0" * 64
        self.assertFalse(verify_queue_report(tampered, self.raw))


if __name__ == "__main__":
    unittest.main()
