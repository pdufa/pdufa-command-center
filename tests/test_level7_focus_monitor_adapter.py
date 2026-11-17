import tempfile
import unittest
from pathlib import Path
from level7_focus_monitor_adapter import persist_focus_monitor_report
from level7_store import EvidenceStore

class FocusMonitorAdapterTests(unittest.TestCase):
    def test_report_persists_without_claiming_primary_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            store = EvidenceStore(Path(folder) / "evidence.sqlite3")
            report = {
                "kind": "FOCUS_NIGHTLY_PRIMARY_SOURCE_MONITOR_NOT_FDA_PREDICTIONS",
                "runAtUTC": "2026-11-17T00:00:00+00:00",
                "trials": [{"nct": "NCT00000001",
                            "sourceStatus": "OFFICIAL_REGISTRY_RETRIEVED",
                            "sourceHash": "abc", "delta": "FIRST_SOURCE_OBSERVATION"},
                           {"nct": "NCT00000002",
                            "sourceStatus": "OFFICIAL_SOURCE_UNAVAILABLE"}],
            }
            self.assertEqual(persist_focus_monitor_report(store, report)["added"], 2)
            self.assertEqual(persist_focus_monitor_report(store, report)["unchanged"], 2)
            first = store.history("NCT00000001")[0]
            self.assertEqual(first.status, "unverified")
            self.assertIn("derived", first.notes.lower())
            self.assertEqual(store.history("NCT00000002")[0].status, "inaccessible")

    def test_duplicate_nct_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            trial = {"nct": "NCT00000001", "sourceStatus": "OFFICIAL_SOURCE_UNAVAILABLE"}
            with self.assertRaises(ValueError):
                persist_focus_monitor_report(
                    EvidenceStore(Path(folder) / "evidence.sqlite3"),
                    {"kind":"FOCUS_NIGHTLY_PRIMARY_SOURCE_MONITOR_NOT_FDA_PREDICTIONS",
                     "runAtUTC":"2026-11-17T00:00:00+00:00", "trials":[trial, trial]})

if __name__ == "__main__":
    unittest.main()
