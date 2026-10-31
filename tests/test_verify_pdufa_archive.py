"""Regression tests for fail-closed structural scan archive checks.

These unit tests do not establish that nightly scans ran on schedule or
that FDA/SEC/source-family data are complete.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_pdufa_archive import ARCHIVE, check_archive


class ArchiveIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads(ARCHIVE.read_text(encoding="utf-8"))

    def check_mutation(self, mutation):
        payload = copy.deepcopy(self.original)
        mutation(payload)
        with tempfile.TemporaryDirectory() as directory:
            test_path = Path(directory) / "archive.json"
            test_path.write_text(json.dumps(payload), encoding="utf-8")
            return check_archive(test_path)

    def test_existing_archive_has_valid_structure_but_is_not_certified(self):
        errors, summary = check_archive()
        self.assertEqual(errors, [])
        self.assertGreater(summary["archive_date_count"], 0)
        self.assertEqual(summary["archive_date_count"], summary["unique_dates"])
        self.assertFalse(summary["full_source_coverage_certified"])

    def test_duplicate_date_is_not_accepted(self):
        errors, _ = self.check_mutation(
            lambda report: report["days"][1].update(
                date_pacific=report["days"][0]["date_pacific"]
            )
        )
        self.assertTrue(any("duplicate Pacific date" in item for item in errors))

    def test_false_complete_status_fails_if_source_families_unknown(self):
        errors, _ = self.check_mutation(
            lambda report: report["days"][0].update(status="COMPLETE")
        )
        self.assertTrue(any("COMPLETE requires qualified Pipeline" in item for item in errors))
        self.assertTrue(any("COMPLETE requires explicit same-run" in item for item in errors))

    def test_complete_requires_explicit_coverage_and_mandatory_totals(self):
        def update(report):
            latest = report["days"][0]
            latest["status"] = "COMPLETE"
            latest["full_source_coverage_verified"] = True
            latest["sections"]["pipeline"]["total"] = 0
            latest["sections"]["designations"]["total"] = 0

        errors, summary = self.check_mutation(update)
        self.assertEqual(errors, [])
        self.assertEqual(summary["statuses"]["COMPLETE"], 1)
        # A syntactically complete saved record is not independent FDA certification.
        self.assertFalse(summary["full_source_coverage_certified"])

    def test_negative_counts_are_invalid(self):
        errors, _ = self.check_mutation(
            lambda report: report["days"][0]["sections"]["gem_jr"].update(total=-1)
        )
        self.assertTrue(any("gem_jr.total" in item for item in errors))

    def test_registration_timestamp_requires_timezone(self):
        errors, _ = self.check_mutation(
            lambda report: report["days"][0].update(registered_at_utc="2026-10-30T20:00:00")
        )
        self.assertTrue(any("timestamp missing timezone" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
