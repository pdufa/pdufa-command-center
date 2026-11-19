import sqlite3
import tempfile
import unittest
from pathlib import Path
from scripts.level7_focus_report import run
from level7_store import EvidenceStore

class Level7FocusReportRunnerTests(unittest.TestCase):
    def test_packaged_focus_roster_reports_all_members(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "evidence.sqlite3"
            EvidenceStore(db).initialize()
            result = run(db)
            self.assertEqual(result["total"], 32)
            self.assertEqual(len(result["trials"]), 32)
            self.assertEqual(result["trialsWithEvidence"], 0)
            self.assertTrue(all(row["fdaPrediction"] is None for row in result["trials"]))

    def test_missing_db_does_not_create_empty_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                run(Path(folder) / "missing.sqlite3")

    def test_missing_table_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "empty.sqlite3"
            with sqlite3.connect(db):
                pass
            with self.assertRaisesRegex(ValueError, "not initialized"):
                run(db)

if __name__ == "__main__":
    unittest.main()
