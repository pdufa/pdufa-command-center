"""Regression tests for the read-only Level 7 store diagnostic."""
import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "level7_store_diagnostic.py"
spec = importlib.util.spec_from_file_location("level7_store_diagnostic", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Level7StoreDiagnosticTests(unittest.TestCase):
    def test_missing_db_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "absent.sqlite3"
            self.assertEqual(module.inspect(path)["status"], "DATABASE_NOT_FOUND")
            self.assertFalse(path.exists())

    def test_missing_table(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.sqlite3"
            with sqlite3.connect(path):
                pass
            self.assertEqual(module.inspect(path)["status"], "LEVEL7_TABLE_NOT_FOUND")

    def test_schema_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.sqlite3"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE level7_evidence (trial_id TEXT)")
            self.assertEqual(module.inspect(path)["status"], "LEVEL7_SCHEMA_MISMATCH")

    def test_aggregates_without_modifying_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.sqlite3"
            with sqlite3.connect(path) as db:
                db.execute("""CREATE TABLE level7_evidence (
                    trial_id TEXT NOT NULL, source_id TEXT NOT NULL,
                    source_version TEXT NOT NULL, record_json TEXT NOT NULL,
                    PRIMARY KEY (trial_id, source_id, source_version))""")
                db.executemany("INSERT INTO level7_evidence VALUES (?,?,?,?)", [
                    ("NCT1", "source-a", "v1", "{}"),
                    ("NCT1", "source-a", "v2", "{}"),
                    ("NCT2", "source-b", "v1", "{}"),
                ])
            before = path.read_bytes()
            self.assertEqual(module.inspect(path), {
                "status": "LEVEL7_STORE_FOUND", "tablePresent": True,
                "sourceVersions": 3, "trialIdentities": 2, "trialSourcePairs": 2
            })
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
