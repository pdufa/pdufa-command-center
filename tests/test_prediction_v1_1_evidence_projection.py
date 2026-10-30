"""Research-only read model tests for the evidence review dashboard."""
import json
import unittest
from pathlib import Path
from research.prediction_v1_1_authorization import ResearchPrincipal
from research.prediction_v1_1_submitter_binding import initialize_submitter_bindings, bind_verified_submitter
from research.prediction_v1_1_audit_ledger import connect_ledger, append_submission
from research.prediction_v1_1_review_workflow import initialize_review_ledger, record_review
from research.prediction_v1_1_evidence_projection import program_evidence_summary

CATALOG=json.loads((Path(__file__).parents[1]/"research/evidence/prediction_v1_1_field_catalog_draft.json").read_text())
RECORD=dict(program_id="TEST|NCT00000000",field_id="TRIAL-001",
 source_url="https://clinicaltrials.gov/study/NCT00000000",source_document_sha256="a"*64,
 source_published_at="2026-01-01T00:00:00Z",observed_at="2026-01-02T00:00:00Z",
 evidence_excerpt="Synthetic example",applicability_rationale="Pivotal trial",
 reviewer_id=None,reviewed_at=None,independent_review_confirmed=False,status="UNVERIFIED")

class EvidenceProjectionTests(unittest.TestCase):
 def setUp(self):
  self.db=connect_ledger(":memory:")
  initialize_review_ledger(self.db)
  initialize_submitter_bindings(self.db)
 def tearDown(self):
  self.db.close()
 def test_empty_program_is_not_ready(self):
  result=program_evidence_summary(self.db,CATALOG,"TEST|NCT00000000")
  self.assertEqual(result["defined_fields"],8)
  self.assertEqual(result["independently_verified"],0)
  self.assertTrue(all(f["status"]=="NOT_COLLECTED" for f in result["fields"]))
  self.assertEqual(result["decision"],"ABSTAIN")
 def test_reviewed_provenance_does_not_auto_verify(self):
  event=append_submission(self.db,RECORD,CATALOG)["event_id"]
  submitter=ResearchPrincipal("submitter-1",frozenset({"evidence_submitter"}),frozenset({RECORD["program_id"]}))
  bind_verified_submitter(self.db,event,submitter)
  auth=ResearchPrincipal("reviewer-2",frozenset({"evidence_reviewer"}),frozenset({RECORD["program_id"]}))
  record_review(self.db,evidence_event_id=event,reviewer_principal="reviewer-2",
   outcome="APPROVE_PROVENANCE",checks={"source_bytes":True,"publication_date":True,"identity":True},
   rationale="Synthetic review",trusted_identity=auth)
  result=program_evidence_summary(self.db,CATALOG,RECORD["program_id"])
  field=next(f for f in result["fields"] if f["id"]=="TRIAL-001")
  self.assertEqual(field["latest_provenance_review"],"APPROVE_PROVENANCE")
  self.assertFalse(field["independently_verified"])
  self.assertEqual(result["decision"],"ABSTAIN")
 def test_different_program_is_isolated(self):
  append_submission(self.db,RECORD,CATALOG)
  result=program_evidence_summary(self.db,CATALOG,"OTHER|PROGRAM")
  self.assertTrue(all(f["status"]=="NOT_COLLECTED" for f in result["fields"]))

if __name__=="__main__":
 unittest.main()
