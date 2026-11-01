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
    exporter = module

    def run_cli(self, args, env=None):
        with patch.object(sys, "argv", ["export_render_postgres.py", *args]), patch.dict(os.environ, env or {}, clear=True):
            return self.exporter.main()

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
            with patch.object(self.exporter.shutil, "which", return_value="/usr/bin/pg_dump"):
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
            with patch.object(self.exporter.shutil, "which", return_value="/usr/bin/pg_dump"), patch.object(self.exporter.subprocess, "run", side_effect=fake_run):
                self.assertEqual(self.run_cli(["--output", str(target)], {"DATABASE_URL": "postgresql://user:secret-pass@localhost:5432/sample"}), 0)
            self.assertEqual(target.read_bytes(), b"PGDMP")
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_racing_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "backup.dump"
            real_open = os.open
            def raced_open(path, flags, mode=0o777, **kwargs):
                if Path(path) == target:
                    target.write_bytes(b"another-process-backup")
                return real_open(path, flags, mode, **kwargs)
            with patch.object(self.exporter.shutil, "which", return_value="/usr/bin/pg_dump"), \
                 patch.object(self.exporter.os, "open", side_effect=raced_open), \
                 patch.object(self.exporter.subprocess, "run") as dump:
                self.assertEqual(self.run_cli(["--output", str(target)], {"DATABASE_URL": "postgresql://user:pass@localhost:5432/sample"}), 1)
            dump.assert_not_called()
            self.assertEqual(target.read_bytes(), b"another-process-backup")

    def test_failed_dump_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "backup.dump"
            def fake_run(argv, stdout, stderr, env, timeout, check):
                stdout.write(b"incomplete")
                return type("Result", (), {"returncode": 1})()
            with patch.object(self.exporter.shutil, "which", return_value="/usr/bin/pg_dump"), patch.object(self.exporter.subprocess, "run", side_effect=fake_run):
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
            with patch.object(self.exporter.shutil, "which", return_value="/usr/bin/pg_dump"), patch.object(self.exporter.subprocess, "run", side_effect=fake_run):
                self.assertEqual(self.run_cli(["--output", str(target)], {"DATABASE_URL": "postgresql://test%40user:s%3Ap%40ss%2Fword@localhost:5432/my%20db"}), 0)
            self.assertEqual(target.read_bytes(), b"PGDMP")

# Exercise the actual container-packaged entrypoint as well as the root CLI.
container_script = SCRIPT.parents[1] / "new-platform/backend/scripts/export_render_postgres.py"
container_spec = importlib.util.spec_from_file_location("container_export_render_postgres", container_script)
container_module = importlib.util.module_from_spec(container_spec)
container_spec.loader.exec_module(container_module)


class ContainerExportTests(ExportTests):
    exporter = container_module


if __name__ == "__main__":
    unittest.main()
