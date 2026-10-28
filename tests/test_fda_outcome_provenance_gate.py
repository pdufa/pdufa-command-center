import json
import unittest
from pathlib import Path
from research.fda_outcome_provenance_gate import build_outcome_provenance_status

ROOT = Path(__file__).resolve().parents[1]

class OutcomeProvenanceGateTests(unittest.TestCase):
    def setUp(self):
        self.reconstruction = json.loads((ROOT/"research/evidence/2025_holdout_predecision_reconstruction.json").read_text())
        self.dossiers = [{"event_key": c["event_key"], "research_only": True,
                          "original_prediction_cutoff": None,
                          "schema_version": "fda-science-research-dossier-v1"}
                         for c in self.reconstruction["cases"]]

    def test_six_cases_abstain_without_probabilities(self):
        result = build_outcome_provenance_status(self.reconstruction, self.dossiers)
        self.assertEqual(len(result["cases"]), 6)
        self.assertEqual(result["validated_predictions"], 0)
        self.assertFalse(result["trading_authorized"])
        for case in result["cases"]:
            self.assertEqual(case["outcome_decision"], "ABSTAIN")
            self.assertIsNone(case["approval_probability"])
            self.assertIsNone(case["pass_fail_grade"])
            self.assertEqual(case["ready_for_analysis_grade"], "NOT_READY")
            self.assertFalse(case["eligible_for_validated_accuracy"])
            self.assertFalse(case["eligible_for_trading_recommendation"])

    def test_rejects_incomplete_and_promoted_science(self):
        with self.assertRaises(ValueError):
            build_outcome_provenance_status(self.reconstruction, self.dossiers[:-1])
        changed = [dict(x) for x in self.dossiers]
        changed[0]["research_only"] = False
        with self.assertRaises(ValueError):
            build_outcome_provenance_status(self.reconstruction, changed)

if __name__ == "__main__":
    unittest.main()
