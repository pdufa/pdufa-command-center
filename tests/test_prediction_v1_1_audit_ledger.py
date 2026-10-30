"""Research evidence ledger regression checks; does not test production deployment."""
import json
import sqlite3
import unittest
from pathlib import Path
from research.prediction_v1_1_audit_ledger import connect_ledger, append_submission, audit_chain

CATALOG = json.loads((Path(__file__).parents[1] / "research/evidence/prediction_v1_1_field_catalog_draft.json").read_text())
SAMPLE = dict(program_id="TEST|NCT00000000", field_id="TRIAL-001",
              source_url="https://clinicaltrials.gov/study/NCT00000000",
              source_document_sha256="a"*64, source_published_at="2026-01-01T00:00:00Z",
              observed_at="2026-01-02T00:00:00Z",
              evidence_excerpt="Synthetic test excerpt only.",
              applicability_rationale="Pivotal trial", reviewer_id=None,
              reviewed_at=None, independent_review_confirmed=False,
              status="UNVERIFIED")

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.db = connect_ledger(":memory:")

    def tearDown(self):
        self.db.close()

    def test_append_and_chain(self):
        first = append_submission(self.db, SAMPLE, CATALOG)
        second = append_submission(self.db, dict(SAMPLE, evidence_excerpt="Another synthetic excerpt"), CATALOG)
        self.assertTrue(first["audit_persisted"])
        self.assertFalse(first["independently_verified"])
        self.assertEqual(second["decision"], "ABSTAIN")
        self.assertEqual(audit_chain(self.db)["checked"], 2)
        self.assertTrue(audit_chain(self.db)["valid"])

    def test_rejection_is_also_audited(self):
        result = append_submission(self.db, dict(SAMPLE, status="VERIFIED", independent_review_confirmed=True), CATALOG)
        self.assertFalse(result["receipt"]["accepted"])
        self.assertEqual(self.db.execute("SELECT event_kind FROM evidence_events").fetchone()[0], "REJECTED")

    def test_update_and_delete_are_prohibited(self):
        append_submission(self.db, SAMPLE, CATALOG)
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("DELETE FROM evidence_events")
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("UPDATE evidence_events SET event_kind='REJECTED'")

    def test_tamper_detection(self):
        append_submission(self.db, SAMPLE, CATALOG)
        self.db.execute("DROP TRIGGER evidence_events_no_update")
        self.db.execute("UPDATE evidence_events SET payload_json='{}'")
        self.assertFalse(audit_chain(self.db)["valid"])

if __name__ == "__main__":
    unittest.main()
