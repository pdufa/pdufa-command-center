import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("review", Path(__file__).resolve().parents[1] / "scripts/medical/subspecialty_review_gate.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)

class SpecialistReviewGateTests(unittest.TestCase):
    def test_shell_rejected(self):
        dossier = {"nct": "NCT00000001", "registrySourceSha256": "abc",
                   "routingStatus": "PROVISIONAL_SINGLE_SPECIALTY", "specialtyCandidates": ["oncology"],
                   "dimensions": {k: {"status": "EVIDENCE_REQUIRED"} for k in review.DIMENSIONS}}
        self.assertFalse(review.validate(dossier)["accepted"])

    def test_independent_challenge_and_citations_required(self):
        dimension = {"status": "REVIEWED", "clinicalFinding": "Test finding", "limitations": "Test limitation",
                     "sourceCitations": [{"sourceUrl": "https://example.org", "sourceDate": "2026-01-01",
                                          "locator": "page 1", "claim": "Test claim"}],
                     "reviewer": "A", "independentReview": {"reviewer": "A", "critique": "Test critique"}}
        dossier = {"nct": "NCT00000001", "registrySourceSha256": "abc",
                   "routingStatus": "PROVISIONAL_SINGLE_SPECIALTY", "specialtyCandidates": ["oncology"],
                   "dimensions": {k: dict(dimension) for k in review.DIMENSIONS}}
        self.assertFalse(review.validate(dossier)["accepted"])
        for item in dossier["dimensions"].values():
            item["independentReview"] = {"reviewer": "B", "critique": "Test critique"}
        self.assertTrue(review.validate(dossier)["accepted"])
        self.assertFalse(review.validate(dossier)["scientificAccuracyVerified"])

if __name__ == "__main__":
    unittest.main()
