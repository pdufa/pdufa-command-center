"""Persistent research evidence storage safety tests."""
import tempfile
import unittest
from pathlib import Path
from research.prediction_v1_1_storage_adapter import open_research_evidence_store, store_health

class ResearchStorageTests(unittest.TestCase):
 def test_requires_explicit_path(self):
  with self.assertRaises(RuntimeError):
   open_research_evidence_store(":memory:")
 def test_rejects_wrong_extension(self):
  with tempfile.TemporaryDirectory() as root:
   with self.assertRaises(ValueError):
    open_research_evidence_store(Path(root)/"evidence.txt")
 def test_persistent_store_reopens_and_is_not_production(self):
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/"evidence.sqlite3"
   conn=open_research_evidence_store(path)
   self.assertTrue(store_health(conn)["healthy"])
   self.assertFalse(store_health(conn)["production_connected"])
   conn.close()
   reopened=open_research_evidence_store(path)
   self.assertEqual(store_health(reopened)["evidence_events"],0)
   reopened.close()

if __name__=="__main__":
 unittest.main()
