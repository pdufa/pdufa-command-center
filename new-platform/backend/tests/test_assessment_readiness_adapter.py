import unittest
from app.assessment_readiness_adapter import assessment_readiness_inputs


class AssessmentReadinessAdapterTests(unittest.TestCase):
    def test_exact_identity_and_complete_model(self):
        record = {"programId": "PDUFA-000001", "exactKey": "A",
                  "models": {"GEM_JR": {"score": 78, "coverage": 100}}}
        result = assessment_readiness_inputs(record, program_id="PDUFA-000001", exact_key="A")
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["assessment_score"], 78)

    def test_mismatched_trial_is_not_reused(self):
        record = {"programId": "PDUFA-000001", "exactKey": "A",
                  "models": {"GEM": {"score": 95, "coverage": 100}}}
        result = assessment_readiness_inputs(record, program_id="PDUFA-000002", exact_key="B", stage="GEM")
        self.assertEqual(result["status"], "IDENTITY_MISMATCH")
        self.assertIsNone(result["assessment_score"])

    def test_partial_model_withheld(self):
        record = {"programId": "PDUFA-000001", "exactKey": "A",
                  "models": {"GEM": {"score": 80, "coverage": 90}}}
        result = assessment_readiness_inputs(record, program_id="PDUFA-000001", exact_key="A", stage="GEM")
        self.assertEqual(result["status"], "ASSESSMENT_INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
