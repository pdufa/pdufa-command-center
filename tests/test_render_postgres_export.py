"""Offline tests: never connect to Render or execute a real pg_dump."""
import importlib.util
import os
from pathlib import Path
import sys
from unittest.mock import patch
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_render_postgres.py"
spec = importlib.util.spec_from_file_location("export_render_postgres", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExportTests(unittest.TestCase):
    SCRIPT_PATH = SCRIPT

    def setUp(self):
        spec = importlib.util.spec_from_file_location("export_under_test", self.SCRIPT_PATH)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def run_cli(self, args, env=None):
        with patch.object(sys, "argv", ["export_render_postgres.py", *args]), patch.dict(os.environ, env or {}, clear=True):
            return self.module.main()

    def test_missing_url_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit):
                self.run_cli(["--output", str(Path(directory) / "out.dump")])

    def test_non_postgres_url_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit):
                self.run_cli(["--output", str(Path(directory) / "out.dump")], {"DATABASE_URL": "sqlite:///tmp/db"})

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing.dump"
            target.write_bytes(b"preserve")
            with patch.object(self.module.shutil, "which", return_value="/usr/bin/pg_dump"):
                with self.assertRaises(SystemExit):
                    self.run_cli(["--output", str(target)], {"DATABASE_URL": "postgresql://user:pass@localhost:5432/sample"})
            self.assertEqual(target.read_bytes(), b"preserve")

    def test_success_keeps_password_out_of_argv(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "backup.dump"
            def fake_run(argv, stdout, stderr, env, timeout, check):
                self.assertNotIn("secret-pass", " ".join(argv))
                self.assertEqual(env["PGPASSWORD"], "secret-pass")
                stdout.write(b"PGDMP")
                return type("Result", (), {"returncode": 0})()
            with patch.object(self.module.shutil, "which", return_value="/usr/bin/pg_dump"), patch.object(self.module.subprocess, "run", side_effect=fake_run):
                self.assertEqual(self.run_cli(["--output", str(target)], {"DATABASE_URL": "postgresql://user:secret-pass@localhost:5432/sample"}), 0)
            self.assertEqual(target.read_bytes(), b"PGDMP")

    def test_failed_dump_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "backup.dump"
            def fake_run(argv, stdout, stderr, env, timeout, check):
                stdout.write(b"incomplete")
                return type("Result", (), {"returncode": 1})()
            with patch.object(self.module.shutil, "which", return_value="/usr/bin/pg_dump"), patch.object(self.module.subprocess, "run", side_effect=fake_run):
                self.assertEqual(self.run_cli(["--output", str(target)], {"DATABASE_URL": "postgresql://user:pass@localhost:5432/sample"}), 1)
            self.assertFalse(target.exists())


    def test_encoded_credentials_are_decoded_without_leaking(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "encoded.dump"
            def fake_run(argv, stdout, stderr, env, timeout, check):
                self.assertEqual(env["PGUSER"], "test@user")
                self.assertEqual(env["PGPASSWORD"], "s:p@ss/word")
                self.assertEqual(env["PGDATABASE"], "my db")
                self.assertEqual(env["PGHOST"], "localhost")
                self.assertNotIn("s:p@ss/word", " ".join(argv))
                stdout.write(b"PGDMP")
                return type("Result", (), {"returncode": 0})()
            with patch.object(self.module.shutil, "which", return_value="/usr/bin/pg_dump"), patch.object(self.module.subprocess, "run", side_effect=fake_run):
                self.assertEqual(self.run_cli(["--output", str(target)], {"DATABASE_URL": "postgresql://test%40user:s%3Ap%40ss%2Fword@localhost:5432/my%20db"}), 0)
            self.assertEqual(target.read_bytes(), b"PGDMP")

    def test_dump_file_is_owner_only(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "private.dump"
            def fake_run(argv, stdout, **kwargs):
                stdout.write(b"PGDMP")
                return type("Result", (), {"returncode": 0})()
            with patch.object(self.module.shutil, "which", return_value="/usr/bin/pg_dump"), patch.object(self.module.subprocess, "run", side_effect=fake_run):
                previous = os.umask(0)
                try:
                    self.assertEqual(self.run_cli(["--output", str(target)], {"DATABASE_URL": "postgresql://user:pass@localhost/sample"}), 0)
                finally:
                    os.umask(previous)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_file_created_concurrently_is_never_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "concurrent.dump"
            def raced_open(*args, **kwargs):
                target.write_bytes(b"preserve-other-process-backup")
                raise FileExistsError("output appeared after preflight")
            with patch.object(self.module.shutil, "which", return_value="/usr/bin/pg_dump"), patch.object(self.module.os, "open", side_effect=raced_open):
                self.assertEqual(self.run_cli(["--output", str(target)], {"DATABASE_URL": "postgresql://user:pass@localhost/sample"}), 1)
            self.assertEqual(target.read_bytes(), b"preserve-other-process-backup")


class DeployedExportTests(ExportTests):
    SCRIPT_PATH = SCRIPT.parent.parent / "new-platform" / "backend" / "scripts" / "export_render_postgres.py"


if __name__ == "__main__":
    unittest.main()
