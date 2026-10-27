import unittest
from scripts.prepare_fda_review_packet import prepare


class ReviewPacketTests(unittest.TestCase):
    def test_review_packet_never_promotes_claimed_decision(self):
        row = {"application_id": "NDA221276", "submission_id": "ORIG-1",
               "review_cycle": 1, "official_source_url": "https://www.fda.gov/a.pdf",
               "action_type": "APPROVAL", "action_date": "2026-10-20"}
        report = prepare({"candidate_review_cycles": [row]},
                         {"records": [dict(row, status="SOURCE_HASH_AVAILABLE_ADJUDICATION_PENDING",
                                           source_sha256="a" * 64)]})
        self.assertEqual(report["verified"], 0)
        self.assertFalse(report["records"][0]["model_eligible"])

    def test_duplicate_identity_rejected(self):
        row = {"application_id": "NDA221276", "submission_id": "ORIG-1",
               "review_cycle": 1, "official_source_url": "https://www.fda.gov/a.pdf"}
        with self.assertRaises(ValueError):
            prepare({"candidate_review_cycles": [row, row]},
                    {"records": [row, row]})

    def test_blocked_source_is_prioritized(self):
        row = {"application_id": "NDA221276", "submission_id": "ORIG-1",
               "review_cycle": 1, "official_source_url": "https://www.fda.gov/a.pdf"}
        report = prepare({"candidate_review_cycles": [row]},
                         {"records": [dict(row, status="NO_MATCHING_SOURCE_REPORT")]})
        self.assertEqual(report["records"][0]["review_priority"], "SOURCE_EVIDENCE_BLOCKED")

    def test_mismatched_cycle_rejected(self):
        row = {"application_id": "NDA221276", "submission_id": "ORIG-1",
               "review_cycle": 1, "official_source_url": "https://www.fda.gov/a.pdf"}
        with self.assertRaises(ValueError):
            prepare({"candidate_review_cycles": [row]},
                    {"records": [dict(row, review_cycle=2)]})
