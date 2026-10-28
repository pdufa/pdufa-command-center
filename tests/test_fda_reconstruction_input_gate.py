import json
import unittest
from pathlib import Path
from research.fda_reconstruction_input_gate import build_reconstruction_input_gate

ROOT = Path(__file__).resolve().parents[1]

class ReconstructionInputGateTests(unittest.TestCase):
    def test_all_six_reconstructions_excluded_from_training(self):
        reconstruction = json.loads((ROOT/"research/evidence/2025_holdout_predecision_reconstruction.json").read_text())
        report = build_reconstruction_input_gate(reconstruction)
        self.assertEqual(len(report["cases"]), 6)
        self.assertEqual(report["validated_prediction_inputs"], 0)
        self.assertFalse(report["trading_authorized"])
        for row in report["cases"]:
            self.assertFalse(row["eligible_for_training"])
            self.assertFalse(row["eligible_for_validated_prediction"])
            self.assertIn("ORIGINAL_PREDICTION_CUTOFF_NOT_AUTHENTICATED", row["blockers"])

if __name__ == "__main__":
    unittest.main()
