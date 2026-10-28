import json
import unittest
from pathlib import Path
from research.fda_science_source_review_queue import build_science_source_review_queue


class ScienceSourceReviewQueueTests(unittest.TestCase):
    def test_six_case_sources_do_not_become_training_evidence(self):
        path = Path(__file__).resolve().parents[1] / "research" / "evidence" / "2025_holdout_predecision_reconstruction.json"
        reconstruction = json.loads(path.read_text())
        result = build_science_source_review_queue(reconstruction)
        self.assertGreater(result["sources_reviewed"], 0)
        self.assertEqual(result["ready_for_independent_science"], 0)
        self.assertEqual(result["eligible_for_predictive_training"], 0)
        self.assertFalse(result["trading_authorized"])
        self.assertTrue(all(not row["eligible_for_predictive_training"] for row in result["sources"]))

    def test_post_cutoff_outcome_document_cannot_be_science_input(self):
        data = {"cases": [{"event_key": "X|2025-01-01", "reconstruction_cutoff": "2024-12-31",
            "observations": [{"id": "outcome", "source_role": "OUTCOME_ONLY",
                "available_on": "2025-01-01", "source_bytes_retained": True,
                "original_document_sha256": "a"*64, "independently_reviewed": True}]}]}
        result = build_science_source_review_queue(data)
        self.assertFalse(result["sources"][0]["ready_for_independent_science"])


if __name__ == "__main__":
    unittest.main()
