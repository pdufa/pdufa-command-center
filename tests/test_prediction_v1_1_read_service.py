import tempfile
import unittest
from pathlib import Path
from research.prediction_v1_1_authorization import ResearchPrincipal
from research.prediction_v1_1_storage_adapter import open_research_evidence_store
from research.prediction_v1_1_read_service import read_program_evidence

class ReadServiceTests(unittest.TestCase):
 def test_authorized_program_receives_unverified_only(self):
  with tempfile.TemporaryDirectory() as root:
   conn=open_research_evidence_store(Path(root)/"test.sqlite3")
   principal=ResearchPrincipal("reader",frozenset({"evidence_reader"}),frozenset({"P1"}))
   result=read_program_evidence(conn,{"status":"PARTIAL_CATALOG_NOT_VALIDATED","fields":[{"id":"F1","segment":"BIO","critical":False,"mandatory":True}]},principal,"P1")
   self.assertEqual(result["readiness"],"NOT_READY")
   self.assertEqual(result["decision"],"ABSTAIN")
   self.assertEqual(result["fields"][0]["status"],"NOT_COLLECTED")
   conn.close()
 def test_cross_program_read_rejected(self):
  with tempfile.TemporaryDirectory() as root:
   conn=open_research_evidence_store(Path(root)/"test.sqlite3")
   principal=ResearchPrincipal("reader",frozenset({"evidence_reader"}),frozenset({"P2"}))
   with self.assertRaises(PermissionError):
    read_program_evidence(conn,{"fields":[]} ,principal,"P1")
   conn.close()

if __name__=="__main__":
 unittest.main()
