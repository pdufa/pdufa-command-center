"""Operational schedule consistency and saved-label drift are distinct facts."""
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_scan_schedule import CONFIG, GATE, WORKFLOW, audit_schedule, main

ROOT = Path(__file__).resolve().parents[1]


class ScheduleMetadataAuditTests(unittest.TestCase):
    def fixture(self, folder, *, saved_time="20:00", wrong_gate=False):
        root = Path(folder)
        for name in (CONFIG, GATE, WORKFLOW):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        workflow = (root / WORKFLOW).read_text()
        import re
        crons = re.findall(r"^\s+- cron: '([^']+)'", workflow, re.M)
        config = json.loads((root / CONFIG).read_text())
        schedule = config["clinical_source_schedule"]
        schedule.update(pacific_daylight_time=saved_time,
                        pacific_standard_time=saved_time, cron_utc=crons)
        (root / CONFIG).write_text(json.dumps(config))
        if wrong_gate:
            path = root / GATE
            path.write_text(path.read_text().replace("start = night.replace(hour=20,", "start = night.replace(hour=22,"))
        return root

    def test_matching_saved_metadata_has_no_false_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_schedule(self.fixture(tmp))
        self.assertEqual(report["status"], "CONSISTENT")
        self.assertTrue(report["metadata_matches_runtime"])
        self.assertEqual(report["warnings"], [])

    def test_saved_labels_cannot_override_the_operational_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_schedule(self.fixture(tmp, saved_time="22:00"))
        self.assertEqual(report["status"], "METADATA_DRIFT")
        self.assertEqual(report["runtime_status"], "CONSISTENT")
        self.assertEqual(report["effective_pacific_start"], "20:00")
        self.assertEqual(report["saved_pacific_standard_time"], "22:00")
        self.assertTrue(report["warnings"])

    def test_runtime_admission_and_launcher_conflict_is_not_metadata_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_schedule(self.fixture(tmp, saved_time="22:00", wrong_gate=True))
        self.assertEqual(report["status"], "RUNTIME_CONFLICT")
        self.assertTrue(report["missing_primary_crons"])
        self.assertFalse(report["metadata_matches_runtime"])

    def test_audit_does_not_write_any_input_and_cli_returns_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp, saved_time="22:00")
            paths = [root / name for name in (CONFIG, GATE, WORKFLOW)]
            before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code = main(["--root", str(root)])
            report = json.loads(out.getvalue())
            self.assertEqual(code, 2)
            self.assertEqual(report["scan_dispatches"], 0)
            self.assertFalse(report["changes_applied"])
            self.assertEqual(before, [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths])

    def test_unknown_or_unparseable_runtime_clock_stays_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(tmp)
            (root / GATE).write_text("# Clock dynamically defined elsewhere; cannot infer it\n")
            report = audit_schedule(root)
        self.assertEqual(report["status"], "NOT_VERIFIED")
        self.assertTrue(report["issues"])


if __name__ == "__main__":
    unittest.main()
