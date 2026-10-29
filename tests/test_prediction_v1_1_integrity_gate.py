"""Regression tests for fail-closed research evidence integrity checks."""
import tempfile
import unittest
from pathlib import Path
from research.prediction_v1_1_storage_adapter import open_research_evidence_store
from research.prediction_v1_1_integrity_gate import audit_all_research_chains
from research.prediction_v1_1_authorization import ResearchPrincipal
from research.prediction_v1_1_read_service import read_program_evidence

class IntegrityGateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.path=Path(self.tmp.name)/"research.sqlite3"
  self.db=open_research_evidence_store(self.path)
  self.reader=ResearchPrincipal("reader",frozenset({"evidence_reader"}),frozenset({"P1"}))
 def tearDown(self):
  self.db.close()
  self.tmp.cleanup()
 def add_event(self):
  self.db.execute("""INSERT INTO evidence_events(event_time,program_id,field_id,event_kind,payload_sha256,event_sha256,receipt_json,payload_json)
   VALUES('2026-01-01','P1','F1','RECEIVED_UNVERIFIED','x','hash1','{}','{}')""")
  return self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
 def test_clean_store_valid(self):
  self.assertTrue(audit_all_research_chains(self.db)["valid"])
 def test_wrong_program_binding_rejected(self):
  event=self.add_event()
  self.db.execute("INSERT INTO evidence_submitter_bindings VALUES(?,?,?)",(event,"alice","P2"))
  self.assertFalse(audit_all_research_chains(self.db)["valid"])
  with self.assertRaises(RuntimeError):
   read_program_evidence(self.db,{"fields":[]} ,self.reader,"P1")
  with self.assertRaises(RuntimeError):
   open_research_evidence_store(self.path)
 def test_blank_submitter_binding_rejected(self):
  event=self.add_event()
  self.db.execute("INSERT INTO evidence_submitter_bindings VALUES(?,?,?)",(event," ","P1"))
  self.assertFalse(audit_all_research_chains(self.db)["valid"])
 def test_unbound_review_rejected(self):
  event=self.add_event()
  self.db.execute("""INSERT INTO review_events(reviewed_at,evidence_event_id,reviewer_principal,review_outcome,
   source_bytes_verified,publication_date_verified,identity_verified,rationale,previous_review_hash,review_hash)
   VALUES('2026-01-01',?,'bob','REQUEST_MORE_EVIDENCE',0,0,0,'test',NULL,'fake')""",(event,))
  self.assertFalse(audit_all_research_chains(self.db)["valid"])
 def test_self_review_rejected(self):
  event=self.add_event()
  self.db.execute("INSERT INTO evidence_submitter_bindings VALUES(?,?,?)",(event,"bob","P1"))
  self.db.execute("""INSERT INTO review_events(reviewed_at,evidence_event_id,reviewer_principal,review_outcome,
   source_bytes_verified,publication_date_verified,identity_verified,rationale,previous_review_hash,review_hash)
   VALUES('2026-01-01',?,'bob','REQUEST_MORE_EVIDENCE',0,0,0,'test',NULL,'fake')""",(event,))
  self.assertFalse(audit_all_research_chains(self.db)["valid"])

if __name__=="__main__": unittest.main()
