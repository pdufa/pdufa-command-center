"""Tests for the read-only initial GEM JR/GEM/WT queue."""
import unittest
from scripts.build_priority_prediction_queue import build_initial_queue, CLASSIFICATION_FIELDS


class QueueTests(unittest.TestCase):
    def test_deduplicates_memberships_and_prioritizes_released_results(self):
        rows = [
            {"list_name": "WT", "program_id": "B", "phase3_evidence_status": "not_released"},
            {"list_name": "GEM", "program_id": "A", "indication": "Disease X",
             "phase3_evidence_status": "phase3_results_released"},
            {"list_name": "GEM JR", "program_id": "A", "mechanism": "Target Y"},
            {"list_name": "GEM JR", "program_id": "C", "phase3_evidence_status": "unknown"},
        ]
        result = build_initial_queue(rows)
        self.assertEqual(result["unique_program_count"], 3)
        self.assertEqual(result["phase3_results_released_count"], 1)
        first = result["queue"][0]
        self.assertEqual(first["program_id"], "A")
        self.assertEqual(first["lists"], ["GEM JR", "GEM"])
        self.assertEqual(first["classification"]["indication"], "Disease X")
        self.assertEqual(first["classification"]["mechanism"], "Target Y")
        self.assertFalse(result["trading_ready"])

    def test_missing_data_is_not_fabricated(self):
        result = build_initial_queue([{"list_name": "GEM JR", "program_id": "X"}])
        item = result["queue"][0]
        self.assertEqual(len(item["missing_classification_fields"]), len(CLASSIFICATION_FIELDS))
        self.assertFalse(item["eligible_for_first_pass"])
        self.assertTrue(item["requires_source_verification"])
        self.assertEqual(item["prediction_status"], "not_started")

    def test_invalid_rows_excluded(self):
        result = build_initial_queue([{"list_name": "PIPELINE", "program_id": "A"},
                                      {"list_name": "WT", "program_id": ""}])
        self.assertEqual(result["unique_program_count"], 0)
        self.assertEqual(result["skipped_rows"]["invalid_group_or_program_id"], 2)


if __name__ == "__main__":
    unittest.main()
