"""Stage 4 FOCUS queue: roster coverage and no invented scientific conclusions."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_focus_adjudication_queue.py"
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"

class FocusAdjudicationQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queue = json.loads(subprocess.check_output(
            [sys.executable, str(SCRIPT)], cwd=ROOT, text=True))
        cls.roster = json.loads(ROSTER.read_text(encoding="utf-8"))

    def test_exact_canonical_roster(self):
        expected = {(r["ticker"], r["nct"]) for r in self.roster["records"]}
        actual = {(r["ticker"], r["nct"]) for r in self.queue["trials"]}
        self.assertEqual(len(expected), 29)
        self.assertEqual(actual, expected)
        self.assertEqual(self.queue["trial_count"], 29)

    def test_all_eight_dimensions_remain_unverified(self):
        self.assertEqual(self.queue["dimensions_per_trial"], 8)
        self.assertEqual(self.queue["adjudicated_count"], 0)
        self.assertEqual(self.queue["prediction_count"], 0)
        for trial in self.queue["trials"]:
            self.assertFalse(trial["adjudicated"])
            self.assertFalse(trial["prediction_published"])
            self.assertIsNone(trial["calibrated_fda_probability"])
            self.assertEqual(trial["source_review"], "PENDING_INDEPENDENT_REVIEW")
            self.assertEqual(trial["independent_challenge"], "PENDING_INDEPENDENT_REVIEW")
            self.assertEqual(len(trial["dimensions"]), 8)
            for dimension in trial["dimensions"].values():
                self.assertEqual(dimension["status"], "PENDING_INDEPENDENT_REVIEW")
                self.assertIsNone(dimension["primary_source_uri"])
                self.assertIsNone(dimension["reviewer"])
                self.assertIsNone(dimension["finding"])

    def test_preliminary_notes_are_only_leads(self):
        for trial in self.queue["trials"]:
            for rel in trial["preliminary_source_notes"]:
                note = ROOT / rel
                self.assertTrue(note.is_file(), rel)
                self.assertTrue(note.name.upper().startswith(trial["ticker"] + "-"))
                self.assertIn(trial["nct"], note.read_text(encoding="utf-8").upper())
        self.assertTrue(self.queue["research_is_not_adjudication"])

if __name__ == "__main__":
    unittest.main()
