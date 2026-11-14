"""Regression: unknown registry status cannot certify phase-first intake."""
import importlib.util
from datetime import date
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "app" / "phase_first_intake.py"
spec = importlib.util.spec_from_file_location("phase_first_intake_test_module", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PhaseStatusVerificationTests(unittest.TestCase):
    def test_unknown_status_blocks_phase_verification(self):
        registry = {
            "nct_id": "NCT12345678",
            "phases": ["PHASE3"],
            "status": "UNKNOWN_STATUS",
            "last_update_posted": {"date": "2026-01-01"},
            "study_design": {"designInfo": {"allocation": "RANDOMIZED"}},
            "primary_outcomes": [{"measure": "Response", "timeFrame": "12 weeks"}],
        }
        result = module.phase_first_intake(
            registry, cutoff=date(2026, 2, 1),
            registry_checked="2026-01-02",
        )
        self.assertEqual(result["executionStatus"], "BLOCKED_UNVERIFIED_PHASE")
        self.assertIsNone(result["phase"])
        self.assertIsNone(result["trialStatus"])
        self.assertEqual(result["fdaPrediction"], "ABSTAIN")
        self.assertEqual(result["scientificValidation"], "NOT_VERIFIED")

    def test_known_status_can_be_intake_only_not_validated(self):
        registry = {
            "nct_id": "NCT12345678",
            "phases": ["PHASE3"],
            "status": "RECRUITING",
            "last_update_posted": {"date": "2026-01-01"},
        }
        result = module.phase_first_intake(
            registry, cutoff=date(2026, 2, 1),
            registry_checked="2026-01-02",
        )
        self.assertEqual(result["executionStatus"], "INTAKE_ONLY")
        self.assertEqual(result["phase"], "PHASE3")
        self.assertEqual(result["fdaPrediction"], "ABSTAIN")
        self.assertEqual(result["endpointQuality"]["scientificScoreStatus"], "NOT_VALIDATED")


    def test_post_cutoff_registry_update_blocks_phase_and_review(self):
        registry = {
            "nct_id": "NCT12345678",
            "phases": ["PHASE3"],
            "status": "COMPLETED",
            "last_update_posted": {"date": "2026-03-01"},
            "primary_outcomes": [{"measure": "Response", "timeFrame": "12 weeks"}],
        }
        result = module.phase_first_intake(
            registry, cutoff=date(2026, 2, 1),
            registry_checked="2026-03-02",
        )
        self.assertEqual(result["executionStatus"], "BLOCKED_UNVERIFIED_PHASE")
        self.assertEqual(result["evidenceInventory"]["primary endpoint definition"], "UNVERIFIED")
        self.assertEqual(result["fdaPrediction"], "ABSTAIN")

    def test_phase_two_does_not_require_completed_phase_three_results(self):
        registry = {
            "nct_id": "NCT12345678",
            "phases": ["PHASE2"],
            "status": "RECRUITING",
            "last_update_posted": {"date": "2026-01-01"},
        }
        result = module.phase_first_intake(
            registry, cutoff=date(2026, 2, 1),
            registry_checked="2026-01-02",
        )
        self.assertEqual(result["executionStatus"], "INTAKE_ONLY")
        self.assertIn("completed Phase 3 results", result["notYetExpected"])
        self.assertNotIn("completed Phase 3 results", result["missingEvidence"])
        self.assertEqual(
            result["evidenceInventory"]["phase-appropriate efficacy and safety evidence"],
            "NOT_ASSESSED",
        )
        self.assertEqual(result["fdaPrediction"], "ABSTAIN")


if __name__ == "__main__":
    unittest.main()
