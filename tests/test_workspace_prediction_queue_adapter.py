"""Tests for actual workspace member rows and saved WT identity resolution."""
import unittest
from scripts.workspace_prediction_queue_adapter import workspace_to_priority_queue


class WorkspaceAdapterTests(unittest.TestCase):
    def test_actual_workspace_shape_and_exact_wt_identity(self):
        payload = {
            "members": {
                "GEM_JR": {"rows": [{"id": "row-1", "programId": "NCT-AAA", "indication": "Disease A"}]},
                "GEM": {"rows": [{"id": "row-2", "programId": "NCT-AAA"}]},
            },
            "program_watch_trade": {
                "identities": [{"id": "row-1", "programId": "NCT-AAA"}],
                "watch": ["row-1"], "trade": [],
            },
        }
        result = workspace_to_priority_queue(payload)
        self.assertEqual(result["unique_program_count"], 1)
        self.assertEqual(result["queue"][0]["lists"], ["GEM JR", "GEM", "WT"])
        self.assertEqual(result["queue"][0]["classification"]["indication"], "Disease A")
        self.assertEqual(result["phase3_results_released_count"], 0)
        self.assertFalse(result["trading_ready"])

    def test_missing_wt_does_not_invent_members(self):
        result = workspace_to_priority_queue({"members": {
            "GEM_JR": {"rows": [{"id": "one", "programId": "P"}]},
            "GEM": {"rows": []},
        }})
        self.assertEqual(result["status"], "SOURCE_PARTIAL")
        self.assertEqual(result["source_groups_missing"], ["WT"])
        self.assertEqual(result["queue"][0]["lists"], ["GEM JR"])

    def test_phase3_stage_label_alone_does_not_qualify(self):
        result = workspace_to_priority_queue({"lists": {
            "GEM_JR": [{"programId": "P1", "phase3Status": "results posted"}],
            "GEM": [], "WT": [],
        }})
        self.assertEqual(result["phase3_results_released_count"], 0)
        self.assertFalse(result["queue"][0]["eligible_for_first_pass"])

    def test_phase3_status_requires_cited_source(self):
        result = workspace_to_priority_queue({"lists": {
            "GEM_JR": [{"programId": "P1",
                        "phase3_evidence_status": "phase3_results_published"}],
            "GEM": [], "WT": [],
        }})
        self.assertEqual(result["phase3_results_released_count"], 0)

    def test_cited_phase3_status_is_provisional_not_trading_ready(self):
        result = workspace_to_priority_queue({"lists": {
            "GEM_JR": [{"programId": "P1",
                        "phase3_evidence_status": "phase3_results_published",
                        "phase3_evidence_url": "https://clinicaltrials.gov/study/NCT00000000"}],
            "GEM": [], "WT": [],
        }})
        self.assertEqual(result["phase3_results_released_count"], 1)
        self.assertTrue(result["queue"][0]["requires_source_verification"])
        self.assertFalse(result["trading_ready"])

    def test_missing_source_fails_closed(self):
        result = workspace_to_priority_queue({"pipeline": []})
        self.assertEqual(result["status"], "SOURCE_SCHEMA_UNVERIFIED")
        self.assertEqual(result["queue"], [])


if __name__ == "__main__":
    unittest.main()
