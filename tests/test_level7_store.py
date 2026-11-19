import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from level7_evidence import make_record
from level7_store import EvidenceStore

class EvidenceStoreTests(unittest.TestCase):
    def test_persistence_idempotence_and_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'evidence.sqlite3'
            store = EvidenceStore(path)
            store.initialize()
            record = make_record(trial_id='NCT00000001', source_id='registry',
                source_url='https://clinicaltrials.gov/study/NCT00000001',
                publisher='ClinicalTrials.gov', source_version='v1',
                content=b'example', retrieved_at='2026-11-17T00:00:00+00:00')
            self.assertTrue(store.add(record))
            reopened = EvidenceStore(path)
            self.assertFalse(reopened.add(record))
            self.assertEqual(reopened.history('NCT00000001'), [record])
            with self.assertRaises(ValueError):
                reopened.add(replace(record, sha256_digest='different'))
            self.assertEqual(reopened.history('NCT00000001'), [record])

if __name__ == '__main__':
    unittest.main()
