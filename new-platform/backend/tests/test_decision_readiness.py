"""Fail-closed readiness checks for investment research."""
import unittest
from app.decision_readiness import decision_readiness


class DecisionReadinessTests(unittest.TestCase):
    def test_missing_evidence_prevents_readiness(self):
        r = decision_readiness(program_id="PDUFA-000001", exact_key="A",
                               assessment_score=None, assessment_coverage=0,
                               market_review={}, catalyst_verified=False,
                               financing_risk_reviewed=False)
        self.assertEqual(r["status"], "NOT_READY")
        self.assertEqual(len(r["missingRequirements"]), 4)
        self.assertIsNone(r["tradeCall"])

    def test_complete_evidence_requires_matching_program(self):
        market = {"status": "RESEARCH_ONLY", "programId": "PDUFA-000001", "exactKey": "A"}
        r = decision_readiness(program_id="PDUFA-000001", exact_key="A",
                               assessment_score=80, assessment_coverage=100,
                               market_review=market, catalyst_verified=True,
                               financing_risk_reviewed=True)
        self.assertEqual(r["status"], "READY_FOR_HUMAN_RESEARCH_REVIEW")
        self.assertFalse(r["ordersEnabled"])
        market["exactKey"] = "B"
        mismatch = decision_readiness(program_id="PDUFA-000001", exact_key="A",
                                      assessment_score=80, assessment_coverage=100,
                                      market_review=market, catalyst_verified=True,
                                      financing_risk_reviewed=True)
        self.assertEqual(mismatch["status"], "NOT_READY")

    def test_partial_assessment_cannot_pass(self):
        market = {"status": "RESEARCH_ONLY", "programId": "PDUFA-000001", "exactKey": "A"}
        r = decision_readiness(program_id="PDUFA-000001", exact_key="A",
                               assessment_score=85, assessment_coverage=75,
                               market_review=market, catalyst_verified=True,
                               financing_risk_reviewed=True)
        self.assertEqual(r["status"], "NOT_READY")


if __name__ == "__main__":
    unittest.main()
