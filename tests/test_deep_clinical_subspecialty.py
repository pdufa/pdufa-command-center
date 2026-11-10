import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "subspecialty", Path(__file__).resolve().parents[1] / "scripts/medical/deep_clinical_subspecialty.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SubspecialtyTests(unittest.TestCase):
    def test_oncology_routes_without_prediction(self):
        result = module.route("Advanced melanoma", "NCT00000001")
        self.assertEqual(result["specialtyCandidates"], ["oncology"])
        self.assertEqual(result["reviewStatus"], "NOT_ADJUDICATED")
        self.assertIsNone(result["fdaOutcomePrediction"])
        self.assertEqual(len(result["reviewDimensions"]), 8)

    def test_ambiguous_requires_review(self):
        result = module.route("Diabetes with chronic kidney disease")
        self.assertEqual(result["routingStatus"], "REQUIRES_SPECIALIST_REVIEW")
        self.assertEqual(len(result["specialtyCandidates"]), 2)

    def test_unknown_is_not_assumed(self):
        result = module.route("Rare unspecified disorder")
        self.assertEqual(result["specialtyCandidates"], [])
        self.assertEqual(result["routingStatus"], "REQUIRES_SPECIALIST_REVIEW")

    def test_word_boundaries(self):
        self.assertEqual(module.route("Cancerous")["specialtyCandidates"], [])

if __name__ == "__main__":
    unittest.main()
