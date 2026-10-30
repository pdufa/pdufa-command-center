import json
import unittest
from pathlib import Path
from research.fda_provenance_checkpoint import build_provenance_checkpoint

ROOT = Path(__file__).resolve().parents[1]

class ProvenanceCheckpointTests(unittest.TestCase):
    def test_six_case_checkpoint_stays_blocked(self):
        archive = json.loads((ROOT/"research/evidence/2025_holdout_archive_provenance_audit.json").read_text())
        reconstruction = json.loads((ROOT/"research/evidence/2025_holdout_predecision_reconstruction.json").read_text())
        report = build_provenance_checkpoint(archive, reconstruction)
        self.assertEqual(report["total_priority_cases"], 6)
        self.assertEqual(report["verified_prospective_predictions"], 0)
        self.assertEqual(report["evidence_records_reviewed"], 0)
        self.assertEqual(len(report["missing_evidence_events"]), 6)
        self.assertEqual(len(report["retrospective_archive_hashes"]), 2)
        self.assertIsNone(report["historical_accuracy"])
        self.assertFalse(report["trading_authorized"])

if __name__ == "__main__":
    unittest.main()
