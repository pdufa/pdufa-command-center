import tempfile
import unittest
from pathlib import Path
from level7_ingestion_bridge import persist_published_snapshot
from level7_store import EvidenceStore

class IngestionBridgeTests(unittest.TestCase):
    def test_versioned_snapshot_persists_and_replays(self):
        with tempfile.TemporaryDirectory() as folder:
            store = EvidenceStore(Path(folder) / "level7.sqlite3")
            args = dict(store=store, trial_id="NCT00000001",
                        relative_path="data/pdufa_candidates.csv",
                        revision="a" * 40, content=b"published-data",
                        retrieved_at="2026-11-17T00:00:00+00:00")
            self.assertTrue(persist_published_snapshot(**args))
            self.assertFalse(persist_published_snapshot(**args))
            self.assertEqual(len(store.history("NCT00000001")), 1)
            with self.assertRaises(ValueError):
                persist_published_snapshot(**{**args, "content":b"changed"})
            self.assertTrue(persist_published_snapshot(**{**args, "revision":"b"*40, "content":b"changed"}))
            self.assertEqual(len(store.history("NCT00000001")), 2)

    def test_missing_identity_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                persist_published_snapshot(
                    store=EvidenceStore(Path(folder) / "level7.sqlite3"),
                    trial_id="", relative_path="data/pdufa_candidates.csv",
                    revision="a"*40, content=b"x",
                    retrieved_at="2026-11-17T00:00:00+00:00")

if __name__ == "__main__":
    unittest.main()
