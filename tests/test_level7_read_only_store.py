"""Regression checks for read-only Level 7 evidence store access."""
import tempfile
import unittest
from pathlib import Path

from level7_store import EvidenceStore


class Level7ReadOnlyStoreTests(unittest.TestCase):
    def test_read_only_missing_file_does_not_create_it(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "missing.sqlite3"
            with self.assertRaises(Exception):
                EvidenceStore(path, read_only=True).history("NCT00000001")
            self.assertFalse(path.exists())

    def test_read_only_store_reads_existing_history(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "evidence.sqlite3"
            EvidenceStore(path).initialize()
            self.assertEqual(EvidenceStore(path, read_only=True).history("NCT00000001"), [])

    def test_read_only_store_refuses_initialize(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "evidence.sqlite3"
            with self.assertRaises(PermissionError):
                EvidenceStore(path, read_only=True).initialize()
            self.assertFalse(path.exists())

    def test_read_only_store_refuses_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "evidence.sqlite3"
            EvidenceStore(path).initialize()
            before = path.read_bytes()
            with self.assertRaises(PermissionError):
                EvidenceStore(path, read_only=True).add_many([])
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
