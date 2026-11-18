"""Offline checks for Level 7 activation preflight."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "level7_activation_preflight", ROOT / "scripts/level7_activation_preflight.py")
import sys
sys.path.insert(0, str(ROOT / "scripts"))
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class Level7ActivationPreflightTests(unittest.TestCase):
    def test_missing_database_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "missing.sqlite3"
            result = preflight.check(db)
            self.assertEqual(result["database"]["status"], "DATABASE_NOT_FOUND")
            self.assertEqual(result["reportStatus"], "BLOCKED")
            self.assertFalse(db.exists())

    def test_initialized_empty_store_is_not_scored(self):
        from level7_store import EvidenceStore
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "evidence.sqlite3"
            EvidenceStore(db).initialize()
            result = preflight.check(db)
            self.assertEqual(result["reportStatus"], "READY_TO_GENERATE")
            self.assertEqual(result["focusTrials"], 32)
            self.assertEqual(result["trialsWithEvidence"], 0)
            self.assertEqual(result["dashboardStatus"], "NOT_CONFIGURED")

    def test_report_mismatch_fails_closed(self):
        from level7_store import EvidenceStore
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "evidence.sqlite3"
            output = Path(folder) / "report.json"
            EvidenceStore(db).initialize()
            output.write_text(json.dumps({"kind": "invalid"}), encoding="utf-8")
            result = preflight.check(db, output)
            self.assertEqual(result["dashboardStatus"], "REPORT_STALE_OR_MISMATCHED")


if __name__ == "__main__":
    unittest.main()
