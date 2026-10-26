import sys
from pathlib import Path
from datetime import date
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_phase3_issuer_pdufa_event_provenance import audit, classify_event


class IssuerPdufaProvenanceTests(unittest.TestCase):
    def test_future_maple_event_is_not_fda_verified(self):
        result = audit(date(2026, 10, 26))
        self.assertEqual(result["original_historical_trials"], 741)
        self.assertEqual(result["original_issuers"], 130)
        self.assertGreaterEqual(result["rights_claim_links"], 16)
        self.assertEqual(result["issuer_reported_events"], 1)
        self.assertEqual(result["future_issuer_reported_events"], 1)
        self.assertEqual(result["past_issuer_reported_events_needing_outcome_reconciliation"], 0)
        self.assertEqual(result["independently_fda_confirmed_events"], 0)
        self.assertIsNone(result["qualified_pipeline_count"])
        e = result["events"][0]
        self.assertEqual(e["supporting_nct"], "NCT05767346")
        self.assertEqual(e["study"], "MAPLE-HCM")
        self.assertEqual(e["application_type"], "sNDA")
        self.assertEqual(e["issuer_reported_pdufa_target"], "2026-11-14")
        self.assertTrue(e["issuer_reported_fda_filing_accepted"])
        self.assertFalse(e["fda_independent_goal_date_confirmed"])
        self.assertFalse(e["application_decision_outcome_verified"])
        self.assertIsNone(e["qualified_pipeline"])

    def test_after_target_requires_outcome_reconciliation(self):
        result = audit(date(2026, 11, 15))
        self.assertEqual(result["future_issuer_reported_events"], 0)
        self.assertEqual(result["past_issuer_reported_events_needing_outcome_reconciliation"], 1)
        self.assertEqual(result["events"][0]["research_status"], "PAST_TARGET_REQUIRES_OUTCOME_RECONCILIATION")
        self.assertFalse(result["events"][0]["application_decision_outcome_verified"])

    def test_on_target_day_is_not_still_future(self):
        result = audit(date(2026, 11, 14))
        self.assertEqual(result["future_issuer_reported_events"], 0)
        self.assertEqual(result["past_issuer_reported_events_needing_outcome_reconciliation"], 1)

    def test_missing_primary_evidence_is_rejected(self):
        event = {"issuer_reported_target_date": "2026-11-14",
                 "agency_independent_verification": False,
                 "issuer_reported_accepted_application": True,
                 "issuer_primary_source_url": ""}
        with self.assertRaisesRegex(ValueError, "primary-source"):
            classify_event(event, date(2026, 10, 26))

    def test_false_agency_confirmation_is_rejected(self):
        event = {"issuer_reported_target_date": "2026-11-14",
                 "agency_independent_verification": True,
                 "issuer_reported_accepted_application": True,
                 "issuer_primary_source_url": "https://ir.cytokinetics.com/"}
        with self.assertRaisesRegex(ValueError, "FDA-verified"):
            classify_event(event, date(2026, 10, 26))


if __name__ == "__main__":
    unittest.main()
