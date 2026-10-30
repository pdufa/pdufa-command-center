"""Reviewer workflow security regression tests (research only)."""
import json
import unittest
from pathlib import Path
from research.prediction_v1_1_authorization import ResearchPrincipal
from research.prediction_v1_1_submitter_binding import initialize_submitter_bindings, bind_verified_submitter
from research.prediction_v1_1_audit_ledger import connect_ledger, append_submission
from research.prediction_v1_1_review_workflow import initialize_review_ledger, record_review, audit_review_chain

CATALOG=json.loads((Path(__file__).parents[1]/"research/evidence/prediction_v1_1_field_catalog_draft.json").read_text())
RECORD=dict(program_id="TEST|NCT00000000",field_id="TRIAL-001",
            source_url="https://clinicaltrials.gov/study/NCT00000000",
            source_document_sha256="a"*64,source_published_at="2026-01-01T00:00:00Z",
            observed_at="2026-01-02T00:00:00Z",evidence_excerpt="Synthetic data only",
            applicability_rationale="Pivotal trial",reviewer_id=None,reviewed_at=None,
            independent_review_confirmed=False,status="UNVERIFIED")
CHECKS={"source_bytes":True,"publication_date":True,"identity":True}

class ReviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.db=connect_ledger(":memory:")
        initialize_review_ledger(self.db)
        initialize_submitter_bindings(self.db)
        self.event=append_submission(self.db,RECORD,CATALOG)["event_id"]
        submitter=ResearchPrincipal("submitter-1",frozenset({"evidence_submitter"}),frozenset({"TEST|NCT00000000"}))
        bind_verified_submitter(self.db,self.event,submitter)
        self.auth=ResearchPrincipal("reviewer-2",frozenset({"evidence_reviewer"}),frozenset({"TEST|NCT00000000"}))
    def tearDown(self):
        self.db.close()
    def test_self_review_rejected_by_record_review(self):
        self.db.execute("DROP TRIGGER evidence_submitter_bindings_no_update")
        self.db.execute("UPDATE evidence_submitter_bindings SET submitter_principal='reviewer-2' WHERE evidence_event_id=?", (self.event,))
        with self.assertRaises(PermissionError):
            record_review(self.db,evidence_event_id=self.event,reviewer_principal="reviewer-2",
                          outcome="APPROVE_PROVENANCE",checks=CHECKS,rationale="Self review",
                          trusted_identity=self.auth)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM review_events").fetchone()[0],0)
    def test_cross_program_review_rejected_by_record_review(self):
        outsider=ResearchPrincipal("reviewer-3",frozenset({"evidence_reviewer"}),frozenset({"OTHER"}))
        with self.assertRaises(PermissionError):
            record_review(self.db,evidence_event_id=self.event,reviewer_principal="reviewer-3",
                          outcome="APPROVE_PROVENANCE",checks=CHECKS,rationale="Cross program",
                          trusted_identity=outsider)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM review_events").fetchone()[0],0)
    def test_missing_binding_rejected_by_record_review(self):
        self.db.execute("DROP TRIGGER evidence_submitter_bindings_no_delete")
        self.db.execute("DELETE FROM evidence_submitter_bindings WHERE evidence_event_id=?", (self.event,))
        with self.assertRaises(PermissionError):
            record_review(self.db,evidence_event_id=self.event,reviewer_principal="reviewer-2",
                          outcome="APPROVE_PROVENANCE",checks=CHECKS,rationale="Unbound",
                          trusted_identity=self.auth)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM review_events").fetchone()[0],0)
    def test_reject_without_authenticated_identity(self):
        with self.assertRaises(PermissionError):
            record_review(self.db,evidence_event_id=self.event,reviewer_principal="reviewer-2",
                          outcome="APPROVE_PROVENANCE",checks=CHECKS,rationale="Reviewed")
    def test_reject_role_or_principal_mismatch(self):
        with self.assertRaises(PermissionError):
            record_review(self.db,evidence_event_id=self.event,reviewer_principal="other",
                          outcome="APPROVE_PROVENANCE",checks=CHECKS,rationale="Reviewed",trusted_identity=self.auth)
    def test_reject_incomplete_checks(self):
        with self.assertRaises(ValueError):
            record_review(self.db,evidence_event_id=self.event,reviewer_principal="reviewer-2",
                          outcome="APPROVE_PROVENANCE",checks={**CHECKS,"identity":False},
                          rationale="Incomplete",trusted_identity=self.auth)
    def test_review_does_not_verify_or_predict(self):
        result=record_review(self.db,evidence_event_id=self.event,reviewer_principal="reviewer-2",
                             outcome="APPROVE_PROVENANCE",checks=CHECKS,rationale="Synthetic test",
                             trusted_identity=self.auth)
        self.assertFalse(result["independently_verified"])
        self.assertEqual(result["decision"],"ABSTAIN")
    def test_review_chain_detects_modified_review(self):
        record_review(self.db,evidence_event_id=self.event,reviewer_principal="reviewer-2",
                      outcome="REQUEST_MORE_EVIDENCE",checks=CHECKS,
                      rationale="Synthetic test",trusted_identity=self.auth)
        self.assertTrue(audit_review_chain(self.db)["valid"])
        self.db.execute("DROP TRIGGER review_events_no_update")
        self.db.execute("UPDATE review_events SET rationale='tampered'")
        self.assertFalse(audit_review_chain(self.db)["valid"])

    def test_review_rows_are_append_only(self):
        record_review(self.db,evidence_event_id=self.event,reviewer_principal="reviewer-2",
                      outcome="REQUEST_MORE_EVIDENCE",checks=CHECKS,rationale="Synthetic test",trusted_identity=self.auth)
        with self.assertRaises(Exception):
            self.db.execute("DELETE FROM review_events")

if __name__=="__main__":
    unittest.main()
