import unittest
from scripts.reconcile_fda_source_evidence import reconcile


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"candidate_review_cycles": [{"application_id": "NDA221276", "submission_id": "ORIG-1",
                         "review_cycle": 1, "official_source_url": "https://www.fda.gov/a.pdf"}]}

    def test_hashed_pdf_remains_unverified(self):
        f = {"records": [{"application_id": "NDA221276", "submission_id": "ORIG-1", "review_cycle": 1,
             "official_source_url": "https://www.fda.gov/a.pdf",
             "status": "BYTES_HASHED_NOT_ADJUDICATED", "sha256": "a" * 64}]}
        r = reconcile(self.ledger, f)
        self.assertEqual(r["records"][0]["status"], "SOURCE_HASH_AVAILABLE_ADJUDICATION_PENDING")
        self.assertFalse(r["records"][0]["model_eligible"])
        self.assertEqual(r["independently_verified"], 0)

    def test_mismatched_url_does_not_join(self):
        f = {"records": [{"application_id": "NDA221276",
             "official_source_url": "https://www.fda.gov/other.pdf",
             "status": "BYTES_HASHED_NOT_ADJUDICATED", "sha256": "a" * 64}]}
        self.assertEqual(reconcile(self.ledger, f)["records"][0]["status"], "NO_MATCHING_SOURCE_REPORT")

    def test_different_cycle_cannot_borrow_source_hash(self):
        f = {"records": [{"application_id": "NDA221276", "submission_id": "ORIG-1",
             "review_cycle": 2, "official_source_url": "https://www.fda.gov/a.pdf",
             "status": "BYTES_HASHED_NOT_ADJUDICATED", "sha256": "a" * 64}]}
        self.assertEqual(reconcile(self.ledger, f)["records"][0]["status"], "NO_MATCHING_SOURCE_REPORT")

    def test_claimed_hash_mismatch_is_flagged(self):
        ledger = {"candidate_review_cycles": [dict(self.ledger["candidate_review_cycles"][0],
                                                   document_sha256="b" * 64)]}
        source = dict(self.ledger["candidate_review_cycles"][0],
                      status="BYTES_HASHED_NOT_ADJUDICATED", sha256="a" * 64)
        self.assertEqual(reconcile(ledger, {"records": [source]})["records"][0]["status"],
                         "CANDIDATE_SOURCE_HASH_MISMATCH")

    def test_malformed_hash_is_not_accepted(self):
        source = dict(self.ledger["candidate_review_cycles"][0],
                      status="BYTES_HASHED_NOT_ADJUDICATED", sha256="z" * 64)
        self.assertEqual(reconcile(self.ledger, {"records": [source]})["records"][0]["status"],
                         "SOURCE_FETCH_UNSUCCESSFUL_OR_BLOCKED")

    def test_conflicting_hashes_are_flagged(self):
        f = {"records": [{"application_id": "NDA221276", "submission_id": "ORIG-1",
             "review_cycle": 1, "official_source_url": "https://www.fda.gov/a.pdf",
             "status": "BYTES_HASHED_NOT_ADJUDICATED", "sha256": x * 64} for x in ("a", "b")]}
        self.assertEqual(reconcile(self.ledger, f)["records"][0]["status"], "CONFLICTING_SOURCE_HASHES")


if __name__ == "__main__":
    unittest.main()
