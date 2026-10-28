import json
import unittest
from pathlib import Path
from research.fda_reconstruction_leakage_audit import audit_reconstruction_leakage

ROOT = Path(__file__).resolve().parents[1]

class ReconstructionLeakageAuditTests(unittest.TestCase):
    def test_six_reconstructed_cases_remain_unverified(self):
        reconstruction = json.loads((ROOT/"research/evidence/2025_holdout_predecision_reconstruction.json").read_text())
        report = audit_reconstruction_leakage(reconstruction)
        self.assertEqual(len(report["cases"]), 6)
        self.assertEqual(report["verified_prediction_inputs"], 0)
        self.assertFalse(report["trading_authorized"])
        self.assertTrue(all(row["validated_prediction_inputs"] == 0 for row in report["cases"]))
        self.assertTrue(all(row["original_prediction_cutoff"] is None for row in report["cases"]))

    def test_future_and_outcome_sources_excluded(self):
        data = {"cases": [{"event_key": "TEST|2025-01-10", "reconstruction_cutoff": "2025-01-09",
                           "action_date": "2025-01-10", "original_prediction_cutoff": None,
                           "observations": [
                               {"id": "after", "available_on": "2025-01-11",
                                "source_role": "PREDECISION_RESEARCH"},
                               {"id": "outcome", "available_on": "2025-01-08",
                                "source_role": "OUTCOME_ONLY"},
                           ]}]}
        report = audit_reconstruction_leakage(data)
        self.assertEqual(len(report["cases"][0]["excluded_observations"]), 2)
        reasons = {x["observation_id"]: x["reasons"] for x in report["cases"][0]["excluded_observations"]}
        self.assertIn("AVAILABLE_AFTER_RECONSTRUCTION_CUTOFF", reasons["after"])
        self.assertIn("NOT_PREDECISION_SOURCE", reasons["outcome"])

    def test_duplicate_observation_rejected(self):
        obs = {"id": "duplicate", "available_on": "2025-01-08", "source_role": "PREDECISION_RESEARCH"}
        data = {"cases": [{"event_key": "TEST", "reconstruction_cutoff": "2025-01-09",
                           "action_date": "2025-01-10", "observations": [obs, obs]}]}
        with self.assertRaises(ValueError):
            audit_reconstruction_leakage(data)

if __name__ == "__main__":
    unittest.main()
