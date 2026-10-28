import unittest
from research.fda_original_prediction_evidence_check import assess_original_prediction_evidence

class OriginalPredictionEvidenceCheckTests(unittest.TestCase):
    def setUp(self):
        self.inventory = {"cases": [{"event_key": "TNXP|2025-08-15"}]}
        self.good = {
            "event_key": "TNXP|2025-08-15",
            "fda_action_at": "2025-08-15T16:00:00Z",
            "prediction_created_at": "2025-08-14T12:00:00Z",
            "model_frozen_at": "2025-08-13T12:00:00Z",
            "immutable_prediction_uri": "https://github.com/example/research/commit/1234567890abcdef1234567890abcdef12345678",
            "prediction_sha256": "a"*64,
            "model_sha256": "b"*64,
            "independent_reviewer": "reviewer",
            "source_timestamp_provenance": "independent immutable timestamp",
        }

    def test_plausible_metadata_never_certifies_accuracy(self):
        result = assess_original_prediction_evidence(self.inventory, [self.good])
        self.assertEqual(result["verified_prospective_predictions"], 0)
        self.assertFalse(result["trading_authorized"])
        self.assertTrue(result["cases"][0]["chronology_consistent"])
        self.assertTrue(result["cases"][0]["artifact_metadata_complete"])
        self.assertFalse(result["cases"][0]["independently_verified"])

    def test_mutable_page_cannot_count_as_immutable_artifact(self):
        record = {**self.good, "immutable_prediction_uri": "https://example.com/latest-prediction"}
        result = assess_original_prediction_evidence(self.inventory, [record])
        self.assertFalse(result["cases"][0]["artifact_metadata_complete"])
        self.assertEqual(result["cases"][0]["status"], "INSUFFICIENT_OR_NONPROSPECTIVE_EVIDENCE")

    def test_short_or_non_commit_github_path_rejected(self):
        for uri in ("https://github.com/example/research/commit/main",
                    "https://github.com/example/research/releases/download/latest/file",
                    "https://github.com/example/research/commit/1234"):
            with self.subTest(uri=uri):
                record = {**self.good, "immutable_prediction_uri": uri}
                result = assess_original_prediction_evidence(self.inventory, [record])
                self.assertFalse(result["cases"][0]["artifact_metadata_complete"])

    def test_commit_url_query_fragment_and_port_rejected(self):
        valid = self.good["immutable_prediction_uri"]
        for uri in (valid + "?ref=main", valid + "#fragment",
                    valid.replace("github.com", "github.com:8443")):
            with self.subTest(uri=uri):
                record = {**self.good, "immutable_prediction_uri": uri}
                result = assess_original_prediction_evidence(self.inventory, [record])
                self.assertFalse(result["cases"][0]["artifact_metadata_complete"])

    def test_inventory_action_date_mismatch_rejected(self):
        inventory = {"cases": [{"event_key": "TNXP|2025-08-15", "action_date": "2025-08-15"}]}
        record = {**self.good, "fda_action_at": "2025-08-16T16:00:00Z"}
        result = assess_original_prediction_evidence(inventory, [record])
        self.assertFalse(result["cases"][0]["action_date_matches_inventory"])
        self.assertFalse(result["cases"][0]["chronology_consistent"])

    def test_same_day_prediction_rejected_without_independent_action_time(self):
        inventory = {"cases": [{"event_key": "TNXP|2025-08-15", "action_date": "2025-08-15"}]}
        record = {**self.good, "prediction_created_at": "2025-08-15T08:00:00Z"}
        result = assess_original_prediction_evidence(inventory, [record])
        self.assertFalse(result["cases"][0]["chronology_consistent"])

    def test_inventory_date_prior_day_prediction_allowed_for_review(self):
        inventory = {"cases": [{"event_key": "TNXP|2025-08-15", "action_date": "2025-08-15"}]}
        result = assess_original_prediction_evidence(inventory, [self.good])
        self.assertTrue(result["cases"][0]["chronology_consistent"])
        self.assertFalse(result["cases"][0]["independently_verified"])

    def test_post_action_prediction_rejected(self):
        record = {**self.good, "prediction_created_at": "2025-08-16T12:00:00Z"}
        result = assess_original_prediction_evidence(self.inventory, [record])
        self.assertFalse(result["cases"][0]["chronology_consistent"])

    def test_naive_timestamps_and_invalid_hash_rejected(self):
        record = {**self.good, "prediction_created_at": "2025-08-14T12:00:00", "model_sha256": "x"*64}
        result = assess_original_prediction_evidence(self.inventory, [record])
        self.assertFalse(result["cases"][0]["chronology_consistent"])
        self.assertFalse(result["cases"][0]["artifact_metadata_complete"])

    def test_duplicate_and_unknown_events_rejected(self):
        with self.assertRaises(ValueError):
            assess_original_prediction_evidence(self.inventory, [self.good, self.good])
        with self.assertRaises(ValueError):
            assess_original_prediction_evidence(self.inventory, [{**self.good, "event_key": "UNKNOWN"}])

    def test_missing_event_reported(self):
        result = assess_original_prediction_evidence(self.inventory, [])
        self.assertEqual(result["missing_evidence_events"], ["TNXP|2025-08-15"])

if __name__ == "__main__":
    unittest.main()
