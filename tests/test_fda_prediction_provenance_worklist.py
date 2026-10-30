import json
import unittest
from pathlib import Path
from research.fda_prediction_provenance_worklist import build_prediction_provenance_worklist

ROOT = Path(__file__).resolve().parents[1] / "research/evidence"

class PredictionProvenanceWorklistTests(unittest.TestCase):
    def test_all_six_cases_remain_unverified(self):
        archive = json.loads((ROOT / "2025_holdout_archive_provenance_audit.json").read_text())
        reconstruction = json.loads((ROOT / "2025_holdout_predecision_reconstruction.json").read_text())
        report = build_prediction_provenance_worklist(archive, reconstruction)
        self.assertTrue(report["research_only"])
        self.assertFalse(report["trading_authorized"])
        self.assertEqual(report["verified_prospective_predictions"], 0)
        self.assertEqual(len(report["worklist"]), 6)
        self.assertEqual(len({r["event_key"] for r in report["worklist"]}), 6)
        for row in report["worklist"]:
            self.assertFalse(row["verified_original_prediction"])
            self.assertEqual(row["validation_status"], "BLOCKED_PENDING_ORIGINAL_PREDICTION_ARTIFACTS")
            self.assertGreaterEqual(len(row["required_artifacts"]), 6)

if __name__ == "__main__":
    unittest.main()
