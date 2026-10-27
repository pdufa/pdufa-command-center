import unittest
from scripts.build_pdufa_integrated_readiness import assemble


class IntegratedReadinessTests(unittest.TestCase):
    def test_unverified_evidence_cannot_become_trade_ready(self):
        row = {"application_id": "NDA221276", "submission_id": "ORIG-1",
               "review_cycle": 1, "official_source_url": "https://www.fda.gov/a.pdf"}
        ledger = {"candidate_review_cycles": [row]}
        fingerprints = {"records": [{"sha256": "a" * 64}]}
        reconciliation = {"records": [dict(row, status="SOURCE_HASH_AVAILABLE_ADJUDICATION_PENDING")]}
        report = assemble(ledger, fingerprints, reconciliation)
        self.assertEqual(report["outcome"]["model_eligible_records"], 0)
        self.assertIsNone(report["main"]["dashboard_prediction_probability"])
        self.assertFalse(report["main"]["recommendation_ready"])

    def test_identity_mismatch_fails_closed(self):
        row = {"application_id": "NDA221276", "submission_id": "ORIG-1",
               "review_cycle": 1, "official_source_url": "https://www.fda.gov/a.pdf"}
        with self.assertRaises(ValueError):
            assemble({"candidate_review_cycles": [row]}, {"records": []},
                     {"records": [dict(row, application_id="NDA999999")]})
