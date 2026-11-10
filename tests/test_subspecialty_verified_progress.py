import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("progress", Path(__file__).resolve().parents[1] / "scripts/medical/subspecialty_verified_progress.py")
progress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(progress)

class VerifiedProgressTests(unittest.TestCase):
    def queue(self):
        return {"status": "RESEARCH_QUEUE_NOT_CLINICAL_ASSESSMENTS",
                "items": [{"nct": f"NCT{i:08d}", "dimension": d}
                          for i in range(29) for d in progress._gate.DIMENSIONS]}

    def test_no_reviews_means_no_completion(self):
        result = progress.summarize(self.queue(), {"dossiers": []})
        self.assertEqual(result["structurallyValidatedDimensions"], 0)
        self.assertEqual(result["dimensionsRemaining"], 232)
        self.assertFalse(result["scientificAccuracyVerified"])

    def test_invalid_review_not_counted(self):
        result = progress.summarize(self.queue(), {"dossiers": [{"nct": "NCT00000000"}]})
        self.assertEqual(result["structurallyValidatedDossiers"], 0)
        self.assertIn("NCT00000000", result["rejectedReviewPackages"])

    def test_unknown_trial_rejected(self):
        with self.assertRaises(ValueError):
            progress.summarize(self.queue(), {"dossiers": [{"nct": "NCT99999999"}]})

if __name__ == "__main__":
    unittest.main()
