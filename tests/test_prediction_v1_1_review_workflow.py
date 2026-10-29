"""Reviewer workflow security regression tests (research only)."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from research.prediction_v1_1_audit_ledger import connect_ledger, append_submission
from research.prediction_v1_1_review_workflow import initialize_review_ledger, record_review

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
        self.event=append_submission(self.db,RECORD,CATALOG)["event_id"]
        self.auth=SimpleNamespace(is_authenticated=True,principal="reviewer-2",roles=("evidence_reviewer",))
    def tearDown(self):
        self.db.close()
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
    def test_review_rows_are_append_only(self):
        record_review(self.db,evidence_event_id=self.event,reviewer_principal="reviewer-2",
                      outcome="REQUEST_MORE_EVIDENCE",checks=CHECKS,rationale="Synthetic test",trusted_identity=self.auth)
        with self.assertRaises(Exception):
            self.db.execute("DELETE FROM review_events")

if __name__=="__main__":
    unittest.main()
