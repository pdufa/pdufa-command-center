"""Guardrails for additive 20-level Deep Medical Intelligence expansion."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "new-platform/frontend/data/deepMedicalTwentyLevelExpansion.json"

class TwentyLevelExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FILE.read_text())

    def test_exact_levels_and_unique_sequence(self):
        levels = self.data["levels"]
        self.assertEqual(len(levels), 20)
        self.assertEqual([x["level"] for x in levels], list(range(1, 21)))

    def test_no_fabricated_scientific_completion(self):
        self.assertEqual(self.data["scientificReviewsCompletedByThisPlan"], 0)
        self.assertTrue(self.data["preserveExistingTwelveLevelArchitecture"])
        for level in self.data["levels"]:
            self.assertIsNone(level["outcomeProbability"])
            self.assertEqual(level["assessmentStatus"], "NOT_SCIENTIFICALLY_ADJUDICATED")

    def test_phase_four_source_extraction_not_equated_to_review(self):
        self.assertEqual(self.data["levels"][3]["implementationStatus"],
                         "SOURCE_EXTRACTION_INSTALLED_NOT_ADJUDICATED")

if __name__ == "__main__":
    unittest.main()
