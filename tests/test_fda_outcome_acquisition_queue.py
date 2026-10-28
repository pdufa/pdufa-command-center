import json
import unittest
from pathlib import Path

from research.fda_outcome_acquisition_queue import build_fda_outcome_acquisition_queue


class FDAOutcomeAcquisitionTests(unittest.TestCase):
    def test_six_case_inventory_and_later_cycle_separation(self):
        source = Path("research/evidence/2025_holdout_predecision_reconstruction.json")
        reconstruction = json.loads(source.read_text(encoding="utf-8"))
        queue = build_fda_outcome_acquisition_queue(reconstruction)
        self.assertEqual(len({r["ticker"] for r in queue["sources"]}), 6)
        self.assertEqual(queue["source_count"], 8)
        by_id = {r["observation_id"]: r for r in queue["sources"]}
        self.assertTrue(by_id["UNCY-LATER-CYCLE"]["source_is_later_or_corrected"])
        self.assertTrue(by_id["CORT-CORRECTED-CRL"]["source_is_later_or_corrected"])
        self.assertFalse(by_id["UNCY-ORIGINAL-CRL"]["source_is_later_or_corrected"])
        self.assertTrue(all(not r["eligible_for_predecision_science"] for r in queue["sources"]))
        self.assertTrue(all(not r["eligible_for_predictive_training"] for r in queue["sources"]))
        self.assertFalse(queue["trading_authorized"])

    def test_post_action_source_cannot_replace_original(self):
        data = {"cases": [{"event_key": "X", "ticker": "X",
            "application_id": "NDA123456", "action_date": "2025-01-01",
            "observations": [{"id": "X-REVISED", "source_role": "OUTCOME_ONLY",
                "available_on": "2025-02-01"}]}]}
        row = build_fda_outcome_acquisition_queue(data)["sources"][0]
        self.assertTrue(row["source_is_later_or_corrected"])
        self.assertFalse(row["may_substitute_for_original_action"])


if __name__ == "__main__":
    unittest.main()
