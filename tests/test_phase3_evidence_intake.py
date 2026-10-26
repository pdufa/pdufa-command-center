import unittest
import sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase3_evidence_intake import validate_evidence

class EvidenceIntakeTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"total": 741, "records": [{"nct_id": f"NCT{i:08d}"} for i in range(1, 742)]}
        self.item = {"nct_id": "NCT00000001", "gate": "current_commercial_rights",
                     "source_url": "https://example.org/rights",
                     "observed_at_utc": "2026-10-01T00:00:00Z",
                     "claim": "Researcher proposes rights evidence",
                     "reviewer_status": "PENDING"}

    def test_pending_evidence_never_qualifies(self):
        result = validate_evidence(self.ledger, [self.item])
        self.assertEqual(result["submitted_total"], 1)
        self.assertIsNone(result["qualified_pipeline_total"])

    def test_accepted_requires_reviewer(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [dict(self.item, reviewer_status="ACCEPTED")])

    def test_unknown_nct_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [dict(self.item, nct_id="NCT99999999")])

    def test_duplicate_evidence_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [self.item, self.item])

    def test_future_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(self.ledger, [dict(self.item, observed_at_utc="2099-01-01T00:00:00Z")])

if __name__ == "__main__":
    unittest.main()
