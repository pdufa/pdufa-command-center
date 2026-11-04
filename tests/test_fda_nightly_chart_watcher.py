"""Offline safety tests for official FDA chart watcher; no network needed."""
from __future__ import annotations
from datetime import date, datetime, timezone
import unittest

from scripts.fda_nightly_chart_watcher import (
    APPLICATION, PROGRAM_ID, WATCHED_CATEGORIES, extract_published_actions, merge_snapshot
)

TODAY = date(2026, 11, 4)

def payload(submissions, application=APPLICATION):
    return {"results": [{
        "application_number": application,
        "sponsor_name": "CYTOKINETICS INC",
        "submissions": submissions,
    }]}


class FdaChartWatcherTests(unittest.TestCase):
    def test_exact_supplement_approval_creates_one_evidenced_marker(self):
        entries = [
            {"submission_type": "ORIG", "submission_number": "1",
             "submission_status": "AP", "submission_status_date": "20251219"},
            {"submission_type": "SUPPL", "submission_number": "2",
             "submission_status": "AP", "submission_status_date": "20261029"}
        ]
        results = extract_published_actions(payload(entries), TODAY)
        self.assertEqual(len(results), 1)
        marker = results[0]
        self.assertEqual(marker["id"], "verified-openfda-nda219083-suppl-2")
        self.assertEqual(marker["date"], "2026-10-29")
        self.assertEqual(marker["category"], "supplement-approval")
        self.assertNotIn("MAPLE-HCM approval", marker["label"])
        self.assertTrue(marker["source"].startswith("https://www.accessdata.fda.gov/"))
        self.assertEqual(marker["submissionStatus"], "AP")

    def test_pending_action_does_not_create_marker(self):
        rows = [{"submission_type": "SUPPL", "submission_number": "1",
                 "submission_status": None, "submission_status_date": None}]
        self.assertEqual(extract_published_actions(payload(rows), TODAY), [])

    def test_future_date_rejected(self):
        rows = [{"submission_type": "SUPPL", "submission_number": "1",
                 "submission_status": "AP", "submission_status_date": "20261114"}]
        with self.assertRaisesRegex(ValueError, "future"):
            extract_published_actions(payload(rows), TODAY)

    def test_application_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "match exact"):
            extract_published_actions(payload([], "NDA219084"), TODAY)

    def test_old_supplements_do_not_create_marker(self):
        rows = [{"submission_type": "SUPPL", "submission_number": "1",
                 "submission_status": "AP", "submission_status_date": "20240101"}]
        self.assertEqual(extract_published_actions(payload(rows), TODAY), [])

    def test_existing_markers_preserved_when_empty_successful_source(self):
        event = extract_published_actions(payload([{
            "submission_type": "SUPPL", "submission_number": "4",
            "submission_status": "AP", "submission_status_date": "20261020"
        }]), TODAY)[0]
        snapshot = merge_snapshot(
            {"events": [event]}, [], datetime(2026, 11, 4, tzinfo=timezone.utc)
        )
        self.assertEqual(snapshot["eventCount"], 1)
        self.assertEqual(snapshot["programId"], PROGRAM_ID)
        self.assertTrue(all(e["mode"] in ("official_drugsfda", "separate_source_required")
                            for e in WATCHED_CATEGORIES))

    def test_changed_fda_status_does_not_silently_rewrite_history(self):
        original = extract_published_actions(payload([{
            "submission_type": "SUPPL", "submission_number": "3",
            "submission_status": "AP", "submission_status_date": "20261028"
        }]), TODAY)[0]
        changed = dict(original, date="2026-10-27")
        with self.assertRaisesRegex(ValueError, "changed"):
            merge_snapshot({"events": [original]}, [changed],
                           datetime(2026, 11, 4, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
