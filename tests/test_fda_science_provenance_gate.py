import json
import unittest
from pathlib import Path
from research.fda_science_provenance_gate import bind_science_research_gate

ROOT = Path(__file__).resolve().parents[1]

class ScienceProvenanceGateTests(unittest.TestCase):
    def setUp(self):
        self.reconstruction = json.loads((ROOT/"research/evidence/2025_holdout_predecision_reconstruction.json").read_text())
        self.dossiers = [{"event_key": c["event_key"], "research_only": True,
                          "original_prediction_cutoff": None,
                          "schema_version": "fda-science-research-dossier-v1"}
                         for c in self.reconstruction["cases"]]

    def test_all_six_remain_research_only(self):
        report = bind_science_research_gate(self.reconstruction, self.dossiers)
        self.assertEqual(len(report["cases"]), 6)
        self.assertEqual(report["validated_science_dossiers"], 0)
        self.assertFalse(report["trading_authorized"])
        self.assertTrue(all(not row["eligible_for_training"] for row in report["cases"]))
        self.assertTrue(all(row["independently_completed_assessments"] == 0 for row in report["cases"]))

    def test_missing_duplicate_and_promoted_dossiers_rejected(self):
        with self.assertRaises(ValueError):
            bind_science_research_gate(self.reconstruction, self.dossiers[:-1])
        with self.assertRaises(ValueError):
            bind_science_research_gate(self.reconstruction, self.dossiers + [self.dossiers[0]])
        promoted = [dict(x) for x in self.dossiers]
        promoted[0]["research_only"] = False
        with self.assertRaises(ValueError):
            bind_science_research_gate(self.reconstruction, promoted)

if __name__ == "__main__":
    unittest.main()
