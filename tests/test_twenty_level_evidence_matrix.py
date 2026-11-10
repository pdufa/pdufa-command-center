"""Tests for source-grounded twenty-level evidence readiness."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("matrix", ROOT/"scripts/medical/twenty_level_evidence_matrix.py")
matrix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matrix)
definition = json.loads((ROOT/"new-platform/frontend/data/deepMedicalTwentyLevelExpansion.json").read_text())

class EvidenceMatrixTests(unittest.TestCase):
    def setUp(self):
        self.roster = {"records": [{"nct": f"NCT{i:08d}"} for i in range(1, 30)]}

    def test_29_by_20_without_fabricated_science(self):
        report = matrix.build(definition, {"results": {}}, self.roster)
        self.assertEqual(report["trialCount"], 29)
        self.assertEqual(len(report["trials"][0]["levels"]), 20)
        self.assertEqual(report["scientificallyAdjudicatedTrials"], 0)
        for trial in report["trials"]:
            for level in trial["levels"]:
                self.assertIsNone(level["probability"])
                self.assertIsNone(level["decision"])

    def test_registry_fields_do_not_imply_review(self):
        nct = "NCT00000001"
        checkpoint = {"results": {nct: {"status": "CAPTURED_UNREVIEWED", "evidence": {
            "nct": nct, "source": "https://clinicaltrials.gov/study/"+nct,
            "fields": {"phase": {"status": "CAPTURED_UNREVIEWED"}}}}}}
        result = matrix.build(definition, checkpoint, self.roster)
        self.assertEqual(result["trials"][0]["levels"][0]["registryEvidenceStatus"],
                         "PARTIAL_SOURCE_CAPTURE_NOT_REVIEWED")
        self.assertEqual(result["trials"][0]["levels"][0]["scientificReviewStatus"], "NOT_ADJUDICATED")

    def test_cross_trial_data_rejected(self):
        checkpoint = {"results": {"NCT00000001": {"status": "CAPTURED_UNREVIEWED",
                      "evidence": {"nct": "NCT00000002", "fields": {}}}}}
        with self.assertRaises(ValueError):
            matrix.build(definition, checkpoint, self.roster)

if __name__ == "__main__":
    unittest.main()
