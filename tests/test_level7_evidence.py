import unittest
from dataclasses import replace
from level7_evidence import EvidenceLedger, make_record

class Level7EvidenceTests(unittest.TestCase):
    def record(self, **overrides):
        args = dict(trial_id="NCT00000001", source_id="registry", source_url="https://clinicaltrials.gov/study/NCT00000001", publisher="ClinicalTrials.gov", source_version="v1", content=b"example", retrieved_at="2026-11-17T00:00:00+00:00")
        args.update(overrides)
        return make_record(**args)

    def test_digest_and_idempotence(self):
        ledger = EvidenceLedger()
        record = self.record()
        self.assertEqual(len(record.sha256_digest), 64)
        self.assertTrue(ledger.add(record))
        self.assertFalse(ledger.add(record))
        self.assertEqual(len(ledger.history("NCT00000001")), 1)

    def test_conflicting_same_version_rejected(self):
        ledger = EvidenceLedger()
        record = self.record()
        ledger.add(record)
        with self.assertRaises(ValueError):
            ledger.add(replace(record, sha256_digest="changed"))

    def test_new_version_retained(self):
        ledger = EvidenceLedger()
        ledger.add(self.record())
        ledger.add(self.record(source_version="v2", content=b"corrected"))
        self.assertEqual(len(ledger.history("NCT00000001")), 2)

    def test_missing_not_treated_as_verified(self):
        record = self.record(status="missing", content=None)
        self.assertIsNone(record.sha256_digest)
        with self.assertRaises(ValueError):
            self.record(status="verified", content=None)

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            self.record(retrieved_at="2026-11-17T00:00:00")

if __name__ == "__main__":
    unittest.main()
