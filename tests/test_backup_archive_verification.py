import tempfile
import unittest
import zipfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_backup_archive import verify_zip


class BackupArchiveVerificationTests(unittest.TestCase):
    def test_valid_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backup.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("data/records.json", "{}")
            result = verify_zip(path)
            self.assertTrue(result["valid"])
            self.assertEqual(result["files"], 1)

    def test_empty_zip_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.zip"
            with zipfile.ZipFile(path, "w"):
                pass
            self.assertFalse(verify_zip(path)["valid"])

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../outside.txt", "no")
            self.assertFalse(verify_zip(path)["valid"])

    def test_corrupt_zip_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.zip"
            path.write_bytes(b"not a zip")
            self.assertFalse(verify_zip(path)["valid"])


if __name__ == "__main__":
    unittest.main()
