"""End-to-end offline CLI coverage for opt-in Level 7 monitor persistence."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "level7_monitor_cli", ROOT / "scripts/focus_nightly_source_monitor.py"
)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)

class Level7MonitorCliTests(unittest.TestCase):
    def test_opt_in_ledger_and_archive_are_written_without_prediction(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            archive, current, db = (base / "archive.json", base / "current.json",
                                    base / "evidence.sqlite3")
            report = {
                "kind": "FOCUS_NIGHTLY_PRIMARY_SOURCE_MONITOR_NOT_FDA_PREDICTIONS",
                "runAtUTC": "2026-11-17T12:00:00+00:00",
                "summary": {"sourceRetrieved": 1, "sourceUnavailable": 0},
                "trials": [{"nct": "NCT00000001",
                            "sourceStatus": "OFFICIAL_REGISTRY_RETRIEVED",
                            "sourceHash": "abc", "delta": "FIRST_SOURCE_OBSERVATION"}],
            }
            argv = ["focus_nightly_source_monitor.py", "--archive", str(archive),
                    "--current", str(current), "--level7-db", str(db)]
            with patch.object(sys, "argv", argv), patch.object(
                monitor, "build_report", return_value=report
            ), patch.object(monitor, "load_json", return_value={}):
                monitor.main()
            self.assertTrue(archive.is_file())
            self.assertTrue(current.is_file())
            self.assertEqual(json.loads(archive.read_text()), report)
            from level7_store import EvidenceStore
            history = EvidenceStore(db).history("NCT00000001")
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].status, "unverified")

    def test_opt_in_monitor_emits_32_trial_coverage_report(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            archive, current, db, output = (
                base / "archive.json", base / "current.json",
                base / "evidence.sqlite3", base / "coverage.json")
            roster = json.loads(monitor.ROSTER_PATH.read_text(encoding="utf-8"))
            ncts = [row["nct"] for row in roster["records"]]
            self.assertEqual(len(ncts), 32)
            report = {
                "kind": "FOCUS_NIGHTLY_PRIMARY_SOURCE_MONITOR_NOT_FDA_PREDICTIONS",
                "runAtUTC": "2026-11-18T12:00:00+00:00",
                "summary": {"sourceRetrieved": 1, "sourceUnavailable": 31},
                "trials": [
                    {"nct": nct, "sourceStatus": "OFFICIAL_REGISTRY_RETRIEVED",
                     "sourceHash": "abc", "delta": "FIRST_SOURCE_OBSERVATION"}
                    for nct in ncts
                ],
            }
            argv = ["focus_nightly_source_monitor.py", "--archive", str(archive),
                    "--current", str(current), "--level7-db", str(db),
                    "--level7-coverage-output", str(output)]
            with patch.object(sys, "argv", argv), patch.object(
                monitor, "build_report", return_value=report
            ), patch.object(monitor, "load_json", return_value={}):
                monitor.main()
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["total"], 32)
            self.assertEqual(len(payload["trials"]), 32)
            self.assertTrue(all(row["fdaPrediction"] is None for row in payload["trials"]))
            self.assertTrue(archive.exists())

    def test_coverage_output_requires_explicit_database(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "coverage.json"
            argv = ["focus_nightly_source_monitor.py", "--archive",
                    str(Path(folder) / "archive.json"),
                    "--level7-coverage-output", str(output)]
            with patch.object(sys, "argv", argv), self.assertRaises(SystemExit):
                monitor.main()
            self.assertFalse(output.exists())

    def test_default_cli_does_not_create_level7_database(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            archive = base / "archive.json"
            report = {
                "kind": "FOCUS_NIGHTLY_PRIMARY_SOURCE_MONITOR_NOT_FDA_PREDICTIONS",
                "runAtUTC": "2026-11-17T12:00:00+00:00",
                "summary": {"sourceRetrieved": 1, "sourceUnavailable": 0},
                "trials": [],
            }
            argv = ["focus_nightly_source_monitor.py", "--archive", str(archive),
                    "--current", str(base / "current.json")]
            with patch.object(sys, "argv", argv), patch.object(
                monitor, "build_report", return_value=report
            ), patch.object(monitor, "load_json", return_value={}):
                monitor.main()
            self.assertTrue(archive.is_file())
            self.assertFalse((base / "evidence.sqlite3").exists())

if __name__ == "__main__":
    unittest.main()
