"""Test dated feed loading, rank integrity and strict-score expiry."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from step7_cached_snapshot import load_current_snapshot
from step7_live import build_snapshot, write_csv
import json

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 11, 14, 30, tzinfo=timezone.utc)


class SavedFeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trials, cls.finance, cls.manifest = build_snapshot(ROOT / "data", NOW)

    def _save(self, folder):
        write_csv(folder / "step7_pre_phase3_feed.csv", self.trials)
        write_csv(folder / "step7_financing_review.csv", self.finance)
        (folder / "step7_live_status.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_all_trials_loaded_without_recomputing_and_scores_are_numeric(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._save(root)
            with patch("step7_live.build_snapshot", side_effect=AssertionError("Do not recompute")):
                loaded = load_current_snapshot(root, NOW + timedelta(minutes=5))
            self.assertIsNotNone(loaded)
            trials, financing, status = loaded
            self.assertEqual(len(trials), 3105)
            self.assertEqual(len(financing), len(self.finance))
            self.assertEqual(status["review_priority_ranked"] + status["review_priority_excluded"], 3105)
            self.assertTrue(all(type(r["Review priority /100"]) is int for r in trials))
            self.assertTrue(all(type(r["Review priority rank"]) is int for r in trials if r["Review priority rank"] is not None))

    def test_cutoff_fail_closed_no_carryover_on_next_pacific_day(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._save(root)
            self.assertIsNone(load_current_snapshot(root, datetime(2026, 10, 12, 8, tzinfo=timezone.utc)))
            self.assertIsNone(load_current_snapshot(root, NOW - timedelta(seconds=1)))
            (root / "step7_financing_review.csv").unlink()
            self.assertIsNone(load_current_snapshot(root, NOW + timedelta(minutes=1)))

    def test_tampered_priorities_do_not_render(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._save(root)
            path = root / "step7_pre_phase3_feed.csv"
            value = path.read_text()
            self.assertIn("REVIEW-PRIORITY-V1", value)
            path.write_text(value.replace("REVIEW-PRIORITY-V1", "INVALID-VERSION", 1))
            self.assertIsNone(load_current_snapshot(root, NOW + timedelta(minutes=1)))


if __name__ == "__main__":
    unittest.main()
