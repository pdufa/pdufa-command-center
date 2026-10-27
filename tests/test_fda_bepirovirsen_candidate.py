"""Ensure FDA bepirovirsen candidate is never silently promoted by metadata alone."""
import json
import unittest
from pathlib import Path
from scripts.screen_fda_evidence import screen_candidate

ROOT = Path(__file__).resolve().parents[1]

class BepirovirsenCandidateTests(unittest.TestCase):
    def test_official_approval_candidate_is_not_model_eligible(self):
        row = json.loads((ROOT / "data/fda_candidate_bepirovirsen_20261020.json").read_text())
        self.assertEqual(row["event_key"], "IONS|BEPIROVIRSEN_CHB_20261026")
        self.assertEqual(row["application_id"], "NDA221276")
        self.assertEqual(row["action_date"], "2026-10-20")
        self.assertEqual(row["action_type"], "APPROVAL")
        self.assertIsNone(row["document_sha256"])
        self.assertFalse(row["independently_verified"])
        self.assertFalse(row["model_eligible"])
        result = screen_candidate(row)
        self.assertEqual(result["status"], "CANDIDATE_METADATA_COMPLETE")
        self.assertFalse(result["independently_verified"])
        self.assertFalse(result["model_eligible"])

if __name__ == "__main__":
    unittest.main()
