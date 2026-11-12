"""Offline safety tests for encrypted archive replication."""
import tempfile
import unittest
from pathlib import Path
from scripts.replicate_recovery_archive import (
    inspect_archive, remote_key, stage_icloud,
)


def fake_age(path: Path, tail: bytes = b"x" * 128) -> None:
    # Format fixture only, not a real encrypted backup.
    path.write_bytes(b"age-encryption.org/v1\n" + tail)


class ReplicateRecoveryArchiveTests(unittest.TestCase):
    def test_requires_age_extension_and_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid = root / "recovery-20261108.age"
            fake_age(valid)
            digest, size = inspect_archive(valid)
            self.assertEqual(len(digest), 64)
            self.assertEqual(size, valid.stat().st_size)
            invalid = root / "plain.age"
            invalid.write_bytes(b"not an encrypted file" * 20)
            with self.assertRaises(ValueError):
                inspect_archive(invalid)

    def test_cloud_key_is_content_addressed(self):
        path = Path("/private/recovery-20261108.age")
        key = remote_key(path, "a" * 64, "2026-11-08")
        self.assertEqual(
            key,
            "pdufa-recovery/2026-11-08/" + "a" * 64 + "-recovery-20261108.age",
        )

    def test_icloud_is_exact_local_copy_and_never_overwrites_differences(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "recovery-20261108.age"
            folder = root / "icloud"
            folder.mkdir()
            fake_age(source)
            digest, size = inspect_archive(source)
            stage_icloud(source, folder, digest, size)
            self.assertEqual((folder / source.name).read_bytes(), source.read_bytes())
            stage_icloud(source, folder, digest, size)  # safe idempotent retry
            fake_age(folder / source.name, b"z" * 128)
            with self.assertRaises(RuntimeError):
                stage_icloud(source, folder, digest, size)

    def test_rejects_missing_icloud_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "recovery.age"
            fake_age(archive)
            digest, size = inspect_archive(archive)
            with self.assertRaises(ValueError):
                stage_icloud(archive, root / "not-synced", digest, size)


if __name__ == "__main__":
    unittest.main()
