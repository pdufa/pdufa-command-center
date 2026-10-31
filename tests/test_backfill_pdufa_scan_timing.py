"""Safety tests for historical PDUFA start-time reconciliation."""
import copy
import unittest

from scripts.backfill_pdufa_scan_timing import ARCHIVE, HISTORY, PROVENANCE, reconcile
import json


class HistoricalTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = json.loads(ARCHIVE.read_text(encoding="utf-8"))
        cls.history = json.loads(HISTORY.read_text(encoding="utf-8"))

    def test_dated_records_remain_unchanged_except_timing(self):
        original = copy.deepcopy(self.saved)
        updated, report = reconcile(original, self.history)
        self.assertEqual(len(updated["days"]), len(original["days"]))
        self.assertEqual(len(report["unavailable"]), 0)
        self.assertEqual(len(report["preserved"]) + len(report["filled"]), len(original["days"]))
        for before, after in zip(original["days"], updated["days"]):
            for key, value in before.items():
                self.assertEqual(value, after[key])
            self.assertEqual(after["status"], before["status"])
            self.assertEqual(after["sections"], before["sections"])

    def test_historical_start_times_never_infer_on_time(self):
        updated, _ = reconcile(self.saved, self.history)
        for row in updated["days"]:
            self.assertGreaterEqual(row["start_delay_minutes"], 0)
            if row["scan_night_source"] == PROVENANCE:
                self.assertTrue(row["timing_evidence_url"].endswith("data/nightly_scan_report.json"))
        latest = updated["days"][0]
        self.assertEqual(latest["start_delay_minutes"], 15)
        self.assertEqual(latest["date_pacific"], "2026-10-30")

    def test_idempotent_preservation_of_existing_rows(self):
        updated, _ = reconcile(self.saved, self.history)
        second, report = reconcile(updated, self.history)
        self.assertEqual(updated, second)
        self.assertEqual(report["filled"], [])

    def test_mismatched_run_history_never_fabricates_start(self):
        source = copy.deepcopy(self.history)
        first_run = self.saved["days"][0]["run_id"]
        for item in source["history"]:
            if item.get("run_id") == first_run:
                item["run_url"] = "https://github.com/pdufa/pdufa-command-center/actions/runs/99999"
                break
        # Remove timing fields to exercise the source-validation path even
        # if the checked-in archive has already been backfilled.
        archived = copy.deepcopy(self.saved)
        for key in ("run_started_at_utc", "scheduled_8pm_pacific_utc",
                    "start_delay_minutes", "scan_night_source", "timing_evidence_url"):
            archived["days"][0].pop(key, None)
        with self.assertRaises(ValueError):
            reconcile(archived, source)

    def test_partial_timing_fields_refused(self):
        archived = copy.deepcopy(self.saved)
        for key in ("run_started_at_utc", "scheduled_8pm_pacific_utc",
                    "start_delay_minutes", "scan_night_source", "timing_evidence_url"):
            archived["days"][0].pop(key, None)
        archived["days"][0]["run_started_at_utc"] = "2026-10-31T03:15:44Z"
        with self.assertRaises(ValueError):
            reconcile(archived, self.history)


if __name__ == "__main__":
    unittest.main()
