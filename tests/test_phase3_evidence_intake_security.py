"""Adversarial safeguards for research-only evidence intake."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase3_evidence_intake import validate_evidence

class IntakeSecurityTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"total": 741, "records": [{"nct_id": f"NCT{i:08d}"} for i in range(1, 742)]}
        self.item = {"nct_id": "NCT00000001", "gate": "current_commercial_rights",
                     "source_url": "https://example.org/rights",
                     "observed_at_utc": "2026-10-01T00:00:00Z",
                     "claim": "Source describes a rights arrangement", "reviewer_status": "PENDING"}
    def test_accepted_evidence_still_does_not_qualify(self):
        item = dict(self.item, reviewer_status="ACCEPTED", reviewer="Independent reviewer",
                    reviewed_at_utc="2026-10-02T00:00:00Z")
        result = validate_evidence(self.ledger, [item])
        self.assertIsNone(result["qualified_pipeline_total"])
        self.assertEqual(result["items"][0]["intake_status"], "EVIDENCE_RECORDED_NOT_QUALIFIED")
    def test_rejected_evidence_still_does_not_qualify(self):
        result = validate_evidence(self.ledger, [dict(self.item, reviewer_status="REJECTED")])
        self.assertIsNone(result["qualified_pipeline_total"])
    def test_registry_identity_cannot_be_self_attested(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [dict(self.item, gate="registry_identity")])
    def test_missing_claim_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [dict(self.item, claim="   ")])
    def test_naive_observation_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [dict(self.item, observed_at_utc="2026-10-01T00:00:00")])
    def test_incomplete_ledger_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence({"total": 740, "records": self.ledger["records"][:-1]}, [self.item])
    def test_non_list_submissions_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, {"evidence": [self.item]})
if __name__ == "__main__":
    unittest.main()
