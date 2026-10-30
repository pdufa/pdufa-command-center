import unittest
from types import SimpleNamespace
from research.prediction_v1_1_audit_ledger import connect_ledger
from research.prediction_v1_1_authorization import ResearchPrincipal
from research.prediction_v1_1_submitter_binding import initialize_submitter_bindings,bind_verified_submitter,authorize_independent_review

class SubmitterBindingTests(unittest.TestCase):
 def setUp(self):
  self.db=connect_ledger(":memory:")
  initialize_submitter_bindings(self.db)
  self.db.execute("""INSERT INTO evidence_events(event_time,program_id,field_id,event_kind,payload_sha256,event_sha256,receipt_json,payload_json)
    VALUES('2026-01-01','P1','F1','RECEIVED_UNVERIFIED','x','hash1','{}','{}')""")
  self.submitter=ResearchPrincipal("alice",frozenset({"evidence_submitter"}),frozenset({"P1"}))
  self.reviewer=ResearchPrincipal("bob",frozenset({"evidence_reviewer"}),frozenset({"P1"}))
 def tearDown(self):self.db.close()
 def test_unbound_review_denied(self):
  with self.assertRaises(PermissionError):authorize_independent_review(self.db,1,self.reviewer)
 def test_binding_and_independent_review(self):
  bind_verified_submitter(self.db,1,self.submitter)
  self.assertTrue(authorize_independent_review(self.db,1,self.reviewer))
 def test_self_review_denied(self):
  bind_verified_submitter(self.db,1,self.submitter)
  reviewer=ResearchPrincipal("alice",frozenset({"evidence_reviewer"}),frozenset({"P1"}))
  with self.assertRaises(PermissionError):authorize_independent_review(self.db,1,reviewer)
 def test_cross_program_denied(self):
  bind_verified_submitter(self.db,1,self.submitter)
  reviewer=ResearchPrincipal("bob",frozenset({"evidence_reviewer"}),frozenset({"P2"}))
  with self.assertRaises(PermissionError):authorize_independent_review(self.db,1,reviewer)
 def test_untrusted_claims_rejected(self):
  with self.assertRaises(PermissionError):bind_verified_submitter(self.db,1,SimpleNamespace(principal="alice",roles=("evidence_submitter",),program_ids=("P1",),is_authenticated=True))
 def test_binding_immutable(self):
  bind_verified_submitter(self.db,1,self.submitter)
  with self.assertRaises(Exception):self.db.execute("UPDATE evidence_submitter_bindings SET submitter_principal='mallory'")
  with self.assertRaises(Exception):bind_verified_submitter(self.db,1,self.submitter)

if __name__=="__main__":unittest.main()
