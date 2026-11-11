"""Level 2: research-only hypothesis intake must preserve uncertainty."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "level2_scientific_hypothesis_intake.py"
SPEC = importlib.util.spec_from_file_location("level2_scientific_hypothesis_intake", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sample():
    return {
        "nct": "NCT00000001",
        "mechanism_claim": "Hypothetical receptor-mediated pathway",
        "biological_rationale": "Biological rationale requires independent evidence",
        "expected_observation": "Prespecified biomarker may change",
        "alternative_explanation": "Observed signal may reflect selection bias",
        "potential_refutation": "Reproducible target engagement is absent",
        "sources": [{
            "url": "https://example.org/synthetic-research-source",
            "published_at": "2026-09-01",
            "retrieved_at": "2026-10-01",
            "excerpt": "Synthetic source observation; not independently adjudicated",
        }],
    }


class LevelTwoHypothesisIntakeTests(unittest.TestCase):
    def assess(self, record=None):
        return MODULE.prepare_hypothesis_review(
            record if record is not None else sample(), "2026-10-27"
        )

    def test_complete_metadata_is_not_scientifically_verified(self):
        result = self.assess()
        self.assertEqual(result["status"], "DOCUMENTED_HYPOTHESIS_AWAITING_REVIEW")
        self.assertFalse(result["scientifically_verified"])
        self.assertFalse(result["assessment_complete"])
        self.assertFalse(result["clinical_efficacy_established"])
        self.assertIsNone(result["fda_prediction"])
        self.assertIsNone(result["approval_probability"])
        self.assertIsNone(result["score"])
        self.assertEqual(result["sources"][0]["status"], "SOURCE_REPORTED_UNADJUDICATED")

    def test_missing_alternative_is_incomplete_not_positive(self):
        item = sample()
        item.pop("alternative_explanation")
        result = self.assess(item)
        self.assertIn("alternative_explanation", result["missing_for_review"])
        self.assertEqual(result["status"], "INCOMPLETE_HYPOTHESIS_AWAITING_EVIDENCE")
        self.assertFalse(result["assessment_complete"])

    def test_missing_source_is_not_publicly_disproven(self):
        item = sample()
        item["sources"] = []
        result = self.assess(item)
        self.assertIn("source_documentation", result["missing_for_review"])
        self.assertFalse(result["source_documentation_complete"])
        self.assertFalse(result["scientifically_verified"])

    def test_early_phase_does_not_require_phase_three_results(self):
        item = sample()
        item["phase"] = "PHASE1"
        result = self.assess(item)
        self.assertEqual(result["nct"], "NCT00000001")
        self.assertNotIn("phase3_results", result["missing_for_review"])
        self.assertFalse(result["assessment_complete"])

    def test_nct_is_exact_eight_ascii_digits(self):
        for invalid in ("NCT01", "NCT123456789", "NCT١٢٣٤٥٦٧٨", "nct12345678"):
            with self.subTest(nct=invalid):
                item = sample()
                item["nct"] = invalid
                with self.assertRaises(ValueError):
                    self.assess(item)

    def test_after_cutoff_and_impossible_dates_fail(self):
        for published, retrieved in (
            ("2026-10-28", "2026-10-28"),
            ("2026-10-01", "2026-10-28"),
            ("2026-02-30", "2026-10-01"),
            ("2026-10-02", "2026-10-01"),
        ):
            with self.subTest(published=published, retrieved=retrieved):
                item = sample()
                item["sources"][0]["published_at"] = published
                item["sources"][0]["retrieved_at"] = retrieved
                with self.assertRaises(ValueError):
                    self.assess(item)

    def test_invalid_urls_fail_closed(self):
        for invalid in (
            "http://example.org/source",
            "https://user:password@example.org/source",
            "https://example.org/source#fragment",
            "https://example.org/source name",
            "https://localhost/source",
            "https://example.org:bad/source",
        ):
            with self.subTest(url=invalid):
                item = sample()
                item["sources"][0]["url"] = invalid
                with self.assertRaises(ValueError):
                    self.assess(item)

    def test_duplicate_receipt_rejected(self):
        item = sample()
        item["sources"] = [item["sources"][0].copy(), item["sources"][0].copy()]
        with self.assertRaises(ValueError):
            self.assess(item)

    def test_external_claim_of_verification_or_prediction_rejected(self):
        for field, value in (
            ("scientifically_verified", True), ("scientifically_verified", False),
            ("fda_prediction", "APPROVE"), ("approval_probability", 0.99),
            ("adjudication", {"result": "PASS"}),
        ):
            with self.subTest(field=field):
                item = sample()
                item[field] = value
                with self.assertRaises(ValueError):
                    self.assess(item)

    def test_blank_or_nonstring_claim_is_rejected(self):
        for value in ("  ", 42, "x" * 2501):
            with self.subTest(value_type=type(value).__name__):
                item = sample()
                item["mechanism_claim"] = value
                with self.assertRaises(ValueError):
                    self.assess(item)


if __name__ == "__main__":
    unittest.main()
