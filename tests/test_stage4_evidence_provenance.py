import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "stage4_evidence_provenance.py"
spec = importlib.util.spec_from_file_location("stage4_evidence_provenance", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample():
    return {"nct": "NCT05507203", "source_type": "trial_registry",
            "url": "https://clinicaltrials.gov/study/NCT05507203",
            "document_date": "2026-10-01", "accessed_date": "2026-11-10",
            "evidence_excerpt": "Source passage to review", "reviewer": "reviewer-id",
            "phase": "Phase 3"}


class ProvenanceTests(unittest.TestCase):
    def test_complete_provenance_is_still_unverified(self):
        self.assertFalse(module.validate_evidence(sample())["scientifically_verified"])

    def test_missing_excerpt_fails(self):
        item = sample()
        item["evidence_excerpt"] = ""
        with self.assertRaises(ValueError):
            module.validate_evidence(item)

    def test_bad_date_fails(self):
        item = sample()
        item["document_date"] = "2026-02-30"
        with self.assertRaises(ValueError):
            module.validate_evidence(item)

    def test_prediction_is_rejected(self):
        item = sample()
        item["prediction"] = {"approval": 1}
        with self.assertRaises(ValueError):
            module.validate_evidence(item)

    def test_unverified_cannot_claim_verified(self):
        item = sample()
        item["verification_status"] = "verified"
        with self.assertRaises(ValueError):
            module.validate_evidence(item)

    def test_nct_identifier_requires_eight_ascii_digits(self):
        for invalid in ("NCT1", "NCT1234567", "NCT123456789",
                        "NCT١٢٣٤٥٦٧٨", "nct12345678", "NCT1234abcd"):
            with self.subTest(nct=invalid):
                item = sample()
                item["nct"] = invalid
                with self.assertRaisesRegex(ValueError, "Invalid NCT identifier"):
                    module.validate_evidence(item)

    def test_valid_eight_digit_nct_is_preserved(self):
        item = sample()
        item["nct"] = "NCT12345678"
        result = module.validate_evidence(item)
        self.assertEqual(result["nct"], "NCT12345678")
        self.assertFalse(result["scientifically_verified"])


if __name__ == "__main__":
    unittest.main()
