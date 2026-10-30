import json
import unittest
from pathlib import Path
from research.fda_archive_chronology_gate import audit_archive_chronology

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/evidence"

class ArchiveChronologyTests(unittest.TestCase):
    def test_archives_postdate_all_six_actions(self):
        archive = json.loads((SOURCE / "2025_holdout_archive_provenance_audit.json").read_text())
        cases = json.loads((SOURCE / "2025_holdout_predecision_reconstruction.json").read_text())
        report = audit_archive_chronology(archive, cases)
        self.assertEqual(len(report["cases"]), 6)
        self.assertEqual(report["eligible_cases"], 0)
        self.assertTrue(all(x["model_freeze_after_fda_action"] for x in report["cases"]))
        self.assertTrue(all(x["prediction_archive_lock_after_fda_action"] for x in report["cases"]))
        self.assertIsNone(report["historical_accuracy"])

if __name__ == "__main__":
    unittest.main()
