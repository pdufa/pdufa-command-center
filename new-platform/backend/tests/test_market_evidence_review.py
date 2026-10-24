"""Market evidence is additive, program-specific, and fails closed."""
import unittest
from app.market_evidence_review import market_evidence_review


class MarketEvidenceReviewTests(unittest.TestCase):
    def test_valid_observations_do_not_change_assessments(self):
        r = market_evidence_review("PDUFA-000001", "TRIAL|ONE",
                                   {"status": "OK", "return20Pct": 12.5, "volumeRatio20": 1.3})
        self.assertEqual(r["status"], "RESEARCH_ONLY")
        self.assertEqual(len(r["observations"]), 2)
        self.assertIsNone(r["recommendation"])
        self.assertFalse(r["assessmentScoreChange"])
        self.assertFalse(r["fsFaChange"])

    def test_missing_volume_withholds_market_evidence(self):
        r = market_evidence_review("PDUFA-000002", "TRIAL|TWO",
                                   {"status": "OK", "return20Pct": 5, "volumeRatio20": None})
        self.assertEqual(r["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(r["observations"], [])

    def test_same_ticker_can_have_separate_program_evidence(self):
        signals = {"status": "OK", "return20Pct": 5, "volumeRatio20": 1.2}
        first = market_evidence_review("PDUFA-000001", "TRIAL|ONE", signals)
        second = market_evidence_review("PDUFA-000002", "TRIAL|TWO", signals)
        self.assertNotEqual(first["programId"], second["programId"])
        self.assertNotEqual(first["exactKey"], second["exactKey"])


if __name__ == "__main__":
    unittest.main()
