import tempfile
import unittest
from pathlib import Path
from level7_evidence import make_record
from level7_store import EvidenceStore
from level7_focus_monitor_adapter import persist_focus_monitor_report

class Level7AtomicityTests(unittest.TestCase):
    def test_unknown_status_cannot_be_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = EvidenceStore(Path(folder) / "evidence.sqlite3")
            store.initialize()
            with self.assertRaisesRegex(ValueError, "Unknown evidence status"):
                make_record(
                    trial_id="NCT00000001", source_id="registry",
                    source_url="https://clinicaltrials.gov/study/NCT00000001",
                    publisher="registry", source_version="v1",
                    content=b"source", status="approved",
                    retrieved_at="2026-11-17T00:00:00+00:00",
                )
            self.assertEqual(store.history("NCT00000001"), [])

    def test_batch_conflict_rolls_back_prior_insert(self):
        with tempfile.TemporaryDirectory() as folder:
            store = EvidenceStore(Path(folder) / "evidence.sqlite3")
            store.initialize()
            def record(nct, content):
                return make_record(trial_id=nct, source_id="registry",
                    source_url="https://clinicaltrials.gov/study/" + nct,
                    publisher="registry", source_version="v1", content=content,
                    retrieved_at="2026-11-17T00:00:00+00:00")
            store.add(record("NCT00000002", b"original"))
            with self.assertRaises(ValueError):
                store.add_many([record("NCT00000001", b"new"),
                                record("NCT00000002", b"conflict")])
            self.assertEqual(store.history("NCT00000001"), [])
            self.assertEqual(len(store.history("NCT00000002")), 1)

    def test_invalid_second_trial_does_not_write_first(self):
        with tempfile.TemporaryDirectory() as folder:
            store = EvidenceStore(Path(folder) / "evidence.sqlite3")
            report = {"kind": "FOCUS_NIGHTLY_PRIMARY_SOURCE_MONITOR_NOT_FDA_PREDICTIONS",
                      "runAtUTC": "2026-11-17T00:00:00+00:00",
                      "trials": [{"nct":"NCT00000001",
                                  "sourceStatus":"OFFICIAL_REGISTRY_RETRIEVED"},
                                 {"nct":"INVALID",
                                  "sourceStatus":"OFFICIAL_SOURCE_UNAVAILABLE"}]}
            with self.assertRaises(ValueError):
                persist_focus_monitor_report(store, report)
            store.initialize()
            self.assertEqual(store.history("NCT00000001"), [])

if __name__ == "__main__":
    unittest.main()
