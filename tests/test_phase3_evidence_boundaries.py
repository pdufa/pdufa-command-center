import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase3_evidence_intake import validate_evidence

class EvidenceBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"total": 741, "records": [{"nct_id": f"NCT{i:08d}"} for i in range(1, 742)]}
        self.base = {"nct_id": "NCT00000001", "gate": "public_listing",
                     "source_url": "https://example.org/evidence",
                     "observed_at_utc": "2026-10-01T00:00:00Z",
                     "claim": "Research-only assertion", "reviewer_status": "PENDING"}
    def test_registry_identity_cannot_be_submitted(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [dict(self.base, gate="registry_identity")])
    def test_unsupported_gate_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [dict(self.base, gate="approval_probability")])
    def test_http_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [dict(self.base, source_url="http://example.org/evidence")])
    def test_blank_claim_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [dict(self.base, claim="   ")])
    def test_invalid_review_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [dict(self.base, reviewer_status="PASS")])
    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [dict(self.base, observed_at_utc="2026-10-01T00:00:00")])
    def test_accepted_review_still_not_qualification(self):
        item = dict(self.base, reviewer_status="ACCEPTED", reviewer="Independent reviewer",
                    reviewed_at_utc="2026-10-02T00:00:00Z")
        result = validate_evidence(self.ledger, [item])
        self.assertIsNone(result["qualified_pipeline_total"])
        self.assertEqual(result["items"][0]["intake_status"], "EVIDENCE_RECORDED_NOT_QUALIFIED")
if __name__ == "__main__":
    unittest.main()
