"""Scientific assessment backend package smoke tests."""
import unittest
from app.scientific_assessment_adapter import scientific_trial_payload

class ScientificAssessmentAdapterTests(unittest.TestCase):
    def test_missing_identity_rejected(self):
        with self.assertRaises(ValueError):
            scientific_trial_payload("")

    def test_missing_evidence_never_scores(self):
        result = scientific_trial_payload("TRIAL|NCT12345678")
        self.assertEqual(result["exactId"], "TRIAL|NCT12345678")
        self.assertIsNone(result["assessment"]["overall_score"])
        self.assertEqual(result["sourceStatus"], "not_loaded")
        self.assertTrue(result["independentOfQualificationPresets"])

if __name__ == "__main__":
    unittest.main()
