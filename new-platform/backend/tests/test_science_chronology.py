"""Run: python -m unittest discover -s tests -p 'test_science_chronology.py'"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.science_chronology import strict_iso_day, registry_publication_day, source_eligible_at_cutoff, preliminary_archive_gate


class ChronologyTests(unittest.TestCase):
    def test_valid_date(self):
        self.assertEqual(strict_iso_day("2026-10-26").isoformat(), "2026-10-26")

    def test_rejects_non_iso(self):
        for value in ("2026-1-2", "2026-10-26T00:00:00", "10/26/2026", None, 42):
            self.assertIsNone(strict_iso_day(value))

    def test_rejects_impossible_dates(self):
        self.assertIsNone(strict_iso_day("2026-02-30"))
        self.assertIsNone(strict_iso_day("2025-02-29"))
        self.assertEqual(strict_iso_day("2024-02-29").isoformat(), "2024-02-29")

    def test_missing_publication_is_unknown(self):
        self.assertIsNone(registry_publication_day(None))
        self.assertIsNone(registry_publication_day("unknown"))


if __name__ == "__main__":
    unittest.main()

class SourceCutoffTests(unittest.TestCase):
    def test_pre_cutoff_source(self):
        self.assertTrue(source_eligible_at_cutoff("2026-09-01", "2026-09-30", "2026-10-01"))

    def test_post_cutoff_publication_rejected(self):
        self.assertFalse(source_eligible_at_cutoff("2026-10-02", "2026-09-30", "2026-10-01"))

    def test_post_cutoff_verification_rejected(self):
        self.assertFalse(source_eligible_at_cutoff("2026-09-01", "2026-10-02", "2026-10-01"))

    def test_missing_or_invalid_dates_rejected(self):
        self.assertFalse(source_eligible_at_cutoff(None, "2026-09-30", "2026-10-01"))
        self.assertFalse(source_eligible_at_cutoff("2026-09-01", None, "2026-10-01"))
        self.assertFalse(source_eligible_at_cutoff("2026-09-01", "2026-09-30", "2026-02-30"))

class ArchiveGateTests(unittest.TestCase):
    def test_all_preliminary_checks_pass(self):
        self.assertTrue(preliminary_archive_gate(True, "2026-09-01", "2026-09-02", "2026-10-01"))

    def test_digest_mismatch_fails(self):
        self.assertFalse(preliminary_archive_gate(False, "2026-09-01", "2026-09-02", "2026-10-01"))

    def test_future_archive_fails(self):
        self.assertFalse(preliminary_archive_gate(True, "2026-10-02", "2026-09-02", "2026-10-01"))

    def test_future_registry_update_fails(self):
        self.assertFalse(preliminary_archive_gate(True, "2026-09-01", "2026-10-02", "2026-10-01"))

    def test_missing_registry_date_fails(self):
        self.assertFalse(preliminary_archive_gate(True, "2026-09-01", None, "2026-10-01"))
