import json
import unittest
from pathlib import Path
from research.fda_science_outcome_status_view import build_research_status

ROOT = Path(__file__).resolve().parents[1]

class ScienceOutcomeStatusViewTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT/"research/evidence/2025_holdout_predecision_reconstruction.json").read_text())

    def test_six_cases_research_only_and_no_probabilities(self):
        view = build_research_status(self.data)
        self.assertEqual(view["schemaVersion"], "fda-science-outcome-research-status-v1")
        self.assertEqual(view["validatedPredictions"], 0)
        self.assertTrue(view["researchOnly"])
        self.assertFalse(view["tradingAuthorized"])
        self.assertEqual(len(view["cases"]), 6)
        self.assertEqual(len({row["eventKey"] for row in view["cases"]}), 6)
        for row in view["cases"]:
            self.assertEqual(row["outcomeDecision"], "ABSTAIN")
            self.assertIsNone(row["approvalProbability"])
            self.assertEqual(row["scienceStatus"], "NOT_INDEPENDENTLY_VERIFIED")
            self.assertEqual(row["readyForAnalysis"], "NOT_READY")
            self.assertTrue(row["blockers"])

    def test_missing_case_identity_is_rejected(self):
        bad = json.loads(json.dumps(self.data))
        bad["cases"][0]["event_key"] = bad["cases"][1]["event_key"]
        with self.assertRaises(ValueError):
            build_research_status(bad)

if __name__ == "__main__":
    unittest.main()
