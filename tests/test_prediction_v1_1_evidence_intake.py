"""Regression checks for the v1.1 unverified evidence intake boundary."""
import json
import unittest
from pathlib import Path
from research.prediction_v1_1_evidence_intake import make_unverified_receipt, validate_evidence_record

CATALOG = json.loads((Path(__file__).parents[1] / "research/evidence/prediction_v1_1_field_catalog_draft.json").read_text())
BASE = dict(program_id="TEST|NCT00000000", field_id="TRIAL-001",
            source_url="https://clinicaltrials.gov/study/NCT00000000",
            source_document_sha256="a" * 64,
            source_published_at="2026-01-01T00:00:00Z",
            observed_at="2026-01-02T00:00:00Z",
            evidence_excerpt="Research-only illustrative text; not clinical evidence.",
            applicability_rationale="Pivotal trial identity is applicable.",
            reviewer_id=None, reviewed_at=None,
            independent_review_confirmed=False, status="UNVERIFIED")


class EvidenceIntakeTests(unittest.TestCase):
    def test_unverified_receipt_never_scores(self):
        result = make_unverified_receipt(BASE, CATALOG, "2026-01-03T00:00:00Z")
        self.assertTrue(result["accepted"])
        self.assertFalse(result["independently_verified"])
        self.assertFalse(result["audit_persisted"])
        self.assertEqual(result["decision"], "ABSTAIN")

    def test_self_attested_verified_is_rejected(self):
        record = dict(BASE, status="VERIFIED", independent_review_confirmed=True)
        self.assertFalse(make_unverified_receipt(record, CATALOG)["accepted"])

    def test_post_cutoff_evidence_rejected(self):
        result = make_unverified_receipt(BASE, CATALOG, "2025-12-31T00:00:00Z")
        self.assertFalse(result["accepted"])
        self.assertIn("evidence not proven available by cutoff", result["errors"])

    def test_unknown_field_rejected(self):
        self.assertIn("unknown field ID", validate_evidence_record(dict(BASE, field_id="INVALID"), CATALOG))

    def test_missing_not_equivalent_to_not_applicable(self):
        record = dict(BASE, status="NOT_APPLICABLE", applicability_rationale="")
        self.assertIn("not-applicable requires documented rationale", validate_evidence_record(record, CATALOG))

    def test_untrusted_url_rejected(self):
        record = dict(BASE, source_url="http://example.org/data")
        self.assertIn("source must be a valid HTTPS URL", validate_evidence_record(record, CATALOG))


if __name__ == "__main__":
    unittest.main()
