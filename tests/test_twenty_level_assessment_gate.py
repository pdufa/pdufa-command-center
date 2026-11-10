"""Ensure readiness never passes as a completed scientific assessment."""
import importlib.util
import unittest
from pathlib import Path
root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gate", root/"scripts/medical/twenty_level_assessment_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class AssessmentGateTests(unittest.TestCase):
    def test_empty_and_readiness_only_rejected(self):
        self.assertFalse(gate.validate({})["accepted"])
        self.assertFalse(gate.validate({"assessmentLevel": 20, "nct": "NCT00000001"})["accepted"])

    def test_source_and_independent_challenge_required(self):
        package = {"nct": "NCT00000001", "applicationId": "app1", "reviewCycle": "2026",
                   "assessmentLevel": 20, "evidence": [{"sourceUrl": "https://example.org",
                   "sourceDate": "2026-01-01", "claim": "documented", "locator": "p.1"}],
                   "limitations": "unknown CMC", "reviewer": "analyst1",
                   "independentChallenge": {"reviewer": "analyst1"},
                   "outcomeJudgment": "ABSTAIN", "timingJudgment": "UNKNOWN",
                   "frozenAt": "2026-11-10T00:00:00Z", "predictionHistoryAppendOnly": True}
        self.assertIn("CHALLENGER_NOT_INDEPENDENT", gate.validate(package)["errors"])
        package["independentChallenge"]["reviewer"] = "analyst2"
        self.assertTrue(gate.validate(package)["accepted"])
        self.assertFalse(gate.validate(package)["scientificAccuracyVerified"])

    def test_uncalibrated_probability_rejected(self):
        package = {"outcomeProbability": 0.9}
        self.assertIn("UNCALIBRATED_PROBABILITY", gate.validate(package)["errors"])

if __name__ == "__main__":
    unittest.main()
