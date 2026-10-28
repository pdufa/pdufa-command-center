import unittest
from research.fda_archive_lock_chronology import audit_archive_lock_chronology


class ArchiveLockChronologyTests(unittest.TestCase):
    def test_retrospective_lock_never_counts_as_prospective(self):
        inventory = {"cases": [{"event_key": "TNXP|2025-08-15", "action_date": "2025-08-15"}]}
        archive = {"prediction_archives": [{
            "matched_priority_event_keys": ["TNXP|2025-08-15"],
            "archive_lock_created_at": "2026-10-04T03:16:07Z",
        }]}
        result = audit_archive_lock_chronology(inventory, archive)
        self.assertEqual(result["archives_locked_after_action"], 1)
        self.assertEqual(result["verified_prospective_predictions"], 0)
        self.assertFalse(result["cases"][0]["archive_lock_is_prospective_evidence"])

    def test_duplicate_archive_match_rejected(self):
        inventory = {"cases": [{"event_key": "TNXP|2025-08-15", "action_date": "2025-08-15"}]}
        group = {"matched_priority_event_keys": ["TNXP|2025-08-15"],
                 "archive_lock_created_at": "2026-10-04T03:16:07Z"}
        with self.assertRaises(ValueError):
            audit_archive_lock_chronology(inventory, {"prediction_archives": [group, group]})


if __name__ == "__main__":
    unittest.main()
