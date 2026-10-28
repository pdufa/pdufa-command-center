"""KEYNOTE-024 live-archive smoke uses only source-verified local evidence."""
import gzip
import hashlib
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.scientific_pilot_live_verify import verify_archived_keynote024


class ArchivedPilotLiveContractTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT02142738"},
                "designModule": {
                    "designInfo": {"allocation": "RANDOMIZED"},
                    "enrollmentInfo": {"count": 305},
                },
            },
        }
        raw = json.dumps(self.record, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode()
        self.payload = gzip.compress(raw)
        self.sha = hashlib.sha256(raw).hexdigest()
        self.fetched = datetime(2026, 10, 24, tzinfo=timezone.utc)

    def verify(self, **changes):
        fields = {
            "nct_id": "NCT02142738",
            "payload_gzip": self.payload,
            "expected_sha256": self.sha,
            "fetched_at": self.fetched,
        }
        fields.update(changes)
        return verify_archived_keynote024(**fields)

    def test_exact_archived_record_passes_only_as_unscored_diagnostic(self):
        result = self.verify()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["nct_id"], "NCT02142738")
        self.assertEqual(result["scientific_domains"], 8)
        self.assertEqual(result["published_analyses"], 3)
        self.assertFalse(result["scientific_assessment_completed"])
        self.assertFalse(result["score_assigned"])
        self.assertTrue(result["read_only"])
        self.assertNotIn("source_raw", result)
        self.assertNotIn("claims", result)

    def test_wrong_trial_identity_fails_closed(self):
        with self.assertRaises(ValueError):
            self.verify(nct_id="NCT12345678")

    def test_corrupt_or_mismatched_archive_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.verify(expected_sha256="0" * 64)
        with self.assertRaises(ValueError):
            self.verify(payload_gzip=self.payload[:10])

    def test_original_pubmed_citations_cannot_be_swapped(self):
        from app.scientific_pilot_keynote024_results import keynote024_published_results
        report = keynote024_published_results()
        report["analysis_snapshots"][0]["source_id"] = "99999999"
        with patch(
            "app.scientific_pilot_live_verify.keynote024_published_results",
            return_value=report,
        ):
            with self.assertRaisesRegex(ValueError, "source identity|sources not present"):
                self.verify()

    def test_automatic_scoring_fails_closed(self):
        from app.scientific_pilot_keynote024_results import keynote024_published_results
        report = keynote024_published_results()
        report["domain_scores"]["clinical_results"] = 99
        with patch(
            "app.scientific_pilot_live_verify.keynote024_published_results",
            return_value=report,
        ):
            with self.assertRaisesRegex(ValueError, "scientifically unscored"):
                self.verify()

    def test_archive_metadata_only_never_claims_scientific_validation(self):
        with patch(
            "app.scientific_pilot_live_verify.dossier_from_archive",
            wraps=__import__(
                "app.scientific_dossier_archive", fromlist=["dossier_from_archive"]
            ).dossier_from_archive,
        ) as verified:
            result = self.verify()
            verified.assert_called_once()
            self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
