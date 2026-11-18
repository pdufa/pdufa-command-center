import tempfile
import unittest
from pathlib import Path
from level7_evidence import make_record
from level7_store import EvidenceStore
from level7_focus_coverage import focus_level7_coverage

class FocusLevel7CoverageTests(unittest.TestCase):
    def test_all_roster_trials_reported_without_fabricated_scores(self):
        with tempfile.TemporaryDirectory() as folder:
            store = EvidenceStore(Path(folder) / "evidence.sqlite3")
            store.initialize()
            store.add(make_record(
                trial_id="NCT00000001", source_id="registry",
                source_url="https://clinicaltrials.gov/study/NCT00000001",
                publisher="registry", source_version="v1",
                content=b"source", retrieved_at="2026-11-17T00:00:00+00:00",
            ))
            result = focus_level7_coverage(store, [
                {"nct": "NCT00000001"}, {"nct": "NCT00000002"}
            ])
            self.assertEqual(result["total"], 2)
            self.assertEqual(result["trialsWithEvidence"], 1)
            self.assertEqual(result["trials"][1]["readiness"], "NO_LEVEL7_EVIDENCE")
            self.assertTrue(all(t["assessmentStatus"] == "NOT_SCORED" and
                                t["fdaPrediction"] is None for t in result["trials"]))

    def test_duplicate_roster_identity_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            store = EvidenceStore(Path(folder) / "evidence.sqlite3")
            store.initialize()
            with self.assertRaisesRegex(ValueError, "duplicate"):
                focus_level7_coverage(store, [
                    {"nct": "NCT00000001"}, {"nct": "NCT00000001"}
                ])

if __name__ == "__main__":
    unittest.main()
