import unittest
from level7_evidence import EvidenceLedger
from level7_published_snapshot import record_published_snapshot

class PublishedSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.ledger = EvidenceLedger()
        self.args = dict(ledger=self.ledger, trial_id="NCT00000001",
                         relative_path="data/pdufa_candidates.csv",
                         revision="a" * 40, content=b"example snapshot",
                         retrieved_at="2026-11-17T00:00:00+00:00")

    def test_records_source_version_and_digest(self):
        record = record_published_snapshot(**self.args)
        self.assertEqual(record.source_version, "a" * 40)
        self.assertEqual(len(record.sha256_digest), 64)
        self.assertEqual(len(self.ledger.history("NCT00000001")), 1)

    def test_repeat_is_idempotent(self):
        record_published_snapshot(**self.args)
        record_published_snapshot(**self.args)
        self.assertEqual(len(self.ledger.history("NCT00000001")), 1)

    def test_mutable_revision_cannot_claim_verified(self):
        with self.assertRaises(ValueError):
            record_published_snapshot(**{**self.args, "revision":"main", "status":"verified"})

    def test_missing_is_explicit(self):
        record = record_published_snapshot(**{**self.args, "content":None, "status":"missing"})
        self.assertIsNone(record.sha256_digest)

    def test_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            record_published_snapshot(**{**self.args, "relative_path":"data/../secret"})

if __name__ == "__main__":
    unittest.main()
