"""Regression tests for the quarantined FDA historical candidate ledger."""
import unittest
from scripts.build_fda_historical_candidate_ledger import build_ledger


class LedgerTests(unittest.TestCase):
    def test_unverified_candidate_never_promoted(self):
        row = {"application_id": "NDA221276", "submission_id": "ORIG-1",
               "review_cycle": 1, "action_type": "APPROVAL",
               "action_date": "2026-10-20", "retrieved_at": "2026-10-27T00:00:00Z",
               "official_source_url": "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/example.pdf",
               "document_title": "Original approval letter", "evidence_locator": "page 1",
               "independently_verified": True, "model_eligible": True}
        result = build_ledger([row])
        self.assertEqual(result["input_candidates"], 1)
        self.assertEqual(result["independently_verified_pass"], 0)
        self.assertEqual(result["model_eligible"], 0)
        self.assertFalse(result["candidate_review_cycles"][0]["model_eligible"])

    def test_duplicate_cycle_quarantined(self):
        row = {"application_id": "NDA221276", "submission_id": "ORIG-1",
               "review_cycle": 1, "action_type": "APPROVAL",
               "action_date": "2026-10-20", "retrieved_at": "2026-10-27T00:00:00Z",
               "official_source_url": "https://www.fda.gov/drugs/example",
               "document_title": "Letter", "evidence_locator": "page 1"}
        result = build_ledger([row, dict(row)])
        self.assertEqual(result["status_counts"], {"QUARANTINED": 2})
        self.assertTrue(all("duplicate_review_cycle_requires_adjudication" in r["issues"]
                            for r in result["candidate_review_cycles"]))


if __name__ == "__main__":
    unittest.main()
