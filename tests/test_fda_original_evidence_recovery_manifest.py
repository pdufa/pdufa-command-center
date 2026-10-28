import json
import unittest
from pathlib import Path
from research.fda_original_evidence_recovery_manifest import build_recovery_manifest


class OriginalEvidenceRecoveryManifestTests(unittest.TestCase):
    def test_six_cases_remain_blocked(self):
        root = Path(__file__).resolve().parents[1] / "research" / "evidence"
        archive = json.loads((root / "2025_holdout_archive_provenance_audit.json").read_text())
        reconstruction = json.loads((root / "2025_holdout_predecision_reconstruction.json").read_text())
        result = build_recovery_manifest(archive, reconstruction)
        self.assertEqual(result["cases_requiring_original_evidence"], 6)
        self.assertEqual(result["retrospective_archives_after_action"], 6)
        self.assertEqual(result["verified_prospective_predictions"], 0)
        self.assertFalse(result["trading_authorized"])
        self.assertTrue(all(not row["original_prediction_found"] for row in result["cases"]))


if __name__ == "__main__":
    unittest.main()
