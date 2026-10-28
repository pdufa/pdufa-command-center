import json
import unittest
from pathlib import Path
from research.fda_original_artifact_inventory import build_original_artifact_inventory

ROOT = Path(__file__).resolve().parents[1]

class OriginalArtifactInventoryTests(unittest.TestCase):
    def setUp(self):
        self.archive = json.loads((ROOT/"research/evidence/2025_holdout_archive_provenance_audit.json").read_text())
        self.reconstruction = json.loads((ROOT/"research/evidence/2025_holdout_predecision_reconstruction.json").read_text())

    def test_six_cases_require_original_sources(self):
        result = build_original_artifact_inventory(self.archive, self.reconstruction)
        self.assertEqual(len(result["cases"]), 6)
        self.assertEqual(result["verified_original_predictions"], 0)
        self.assertFalse(result["trading_authorized"])
        self.assertEqual({r["event_key"] for r in result["cases"]},
                         {"NVAX|2025-04-01", "UNCY|2025-06-28", "TNXP|2025-08-15",
                          "BCRX|2025-12-12", "CORT|2025-12-30", "VNDA|2025-12-30"})
        for case in result["cases"]:
            self.assertEqual(len(case["retrospective_archive_sha256"]), 64)
            self.assertFalse(case["pre_action_prediction_verified"])
            self.assertEqual(case["source_records_found"], 0)
            self.assertEqual(len(case["candidate_sources_to_inspect"]), 5)

    def test_ambiguous_archive_match_is_rejected(self):
        self.archive["prediction_archives"][1]["matched_priority_event_keys"].append("NVAX|2025-04-01")
        with self.assertRaises(ValueError):
            build_original_artifact_inventory(self.archive, self.reconstruction)

if __name__ == "__main__":
    unittest.main()
