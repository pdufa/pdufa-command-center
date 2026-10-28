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

    def test_offline_hash_is_visible_but_not_certified(self):
        data = {"cases": [{"event_key": "X", "application_id": "NDA218607",
            "action_date": "2025-06-27", "reconstruction_cutoff": "2025-06-26",
            "observations": [{"id": "obs", "source_role": "OUTCOME_ONLY",
                "source_url": "https://example.test/crl.pdf", "available_on": "2025-06-27"}]}]}
        intake = {"obs": {"schema_version": "fda-crl-offline-intake-v1",
                          "sha256": "a" * 64, "status": "HASHED_UNVERIFIED_SOURCE",
                          "application": "NDA218607", "action_date": "2025-06-27",
                          "source_url_claimed": "https://example.test/crl.pdf",
                          "fda_authenticity_verified": False,
                          "eligible_for_predictive_training": False}}
        report = build_science_source_review_queue(data, intake)
        self.assertEqual(report["sources"][0]["offline_intake_sha256"], "a" * 64)
        self.assertFalse(report["sources"][0]["ready_for_independent_science"])
        self.assertEqual(report["eligible_for_predictive_training"], 0)

    def test_self_certified_intake_rejected(self):
        data = {"cases": [{"event_key": "X", "reconstruction_cutoff": "2025-01-01",
            "observations": [{"id": "obs", "source_role": "PREDECISION_RESEARCH",
                "available_on": "2024-12-01"}]}]}
        with self.assertRaises(ValueError):
            build_science_source_review_queue(data, {"obs": {
                "schema_version": "fda-crl-offline-intake-v1",
                "fda_authenticity_verified": True}})

    def test_outcome_pdf_cannot_be_attached_to_predecision_input(self):
        data = {"cases": [{"event_key": "X", "application_id": "NDA218607",
            "action_date": "2025-06-27", "reconstruction_cutoff": "2025-06-26",
            "observations": [{"id": "obs", "source_role": "PREDECISION_RESEARCH",
                "source_url": "https://example.test/crl.pdf", "available_on": "2025-06-25"}]}]}
        intake = {"obs": {"schema_version": "fda-crl-offline-intake-v1",
                          "application": "NDA218607", "action_date": "2025-06-27",
                          "source_url_claimed": "https://example.test/crl.pdf"}}
        with self.assertRaisesRegex(ValueError, "predecision"):
            build_science_source_review_queue(data, intake)

    def test_wrong_application_is_rejected(self):
        data = {"cases": [{"event_key": "X", "application_id": "NDA218607",
            "action_date": "2025-06-27", "reconstruction_cutoff": "2025-06-26",
            "observations": [{"id": "obs", "source_role": "OUTCOME_ONLY",
                "source_url": "https://example.test/crl.pdf", "available_on": "2025-06-27"}]}]}
        intake = {"obs": {"schema_version": "fda-crl-offline-intake-v1",
                          "application": "NDA999999", "action_date": "2025-06-27",
                          "source_url_claimed": "https://example.test/crl.pdf"}}
        with self.assertRaisesRegex(ValueError, "application"):
            build_science_source_review_queue(data, intake)


if __name__ == "__main__":
    unittest.main()
