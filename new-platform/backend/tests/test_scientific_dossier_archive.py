"""Offline contracts for read-only archived scientific dossiers."""
import gzip
import hashlib
import json
import unittest
from datetime import datetime, timezone

from app.scientific_dossier_archive import (
    MAX_ARCHIVE_BYTES, dossier_from_archive,
)


class ArchivedDossierTests(unittest.TestCase):
    def setUp(self):
        self.registry = {"protocolSection": {
            "identificationModule": {"nctId": "NCT12345678"},
            "designModule": {"designInfo": {
                "allocation": "RANDOMIZED",
                "maskingInfo": {"masking": "DOUBLE"},
            }, "enrollmentInfo": {"count": 250}},
            "outcomesModule": {"primaryOutcomes": [{"measure": "Overall survival"}]},
        }}
        self.raw = json.dumps(
            self.registry, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        self.payload = gzip.compress(self.raw)
        self.digest = hashlib.sha256(self.raw).hexdigest()

    def dossier(self, payload=None, digest=None, exact_id="TRIAL|NCT12345678",
                nct_id="NCT12345678", fetched_at=None):
        return dossier_from_archive(
            exact_id, nct_id,
            self.payload if payload is None else payload,
            self.digest if digest is None else digest,
            fetched_at,
        )

    def test_verified_archive_generates_only_unscored_registry_claims(self):
        dossier = self.dossier(fetched_at=datetime(2026, 10, 24, tzinfo=timezone.utc))
        self.assertEqual(dossier["exact_program_id"], "TRIAL|NCT12345678")
        self.assertEqual(dossier["source_sha256"], self.digest)
        self.assertIn("2026-10-24", dossier["source_fetched_at"])
        self.assertEqual(len(dossier["domains"]), 8)
        self.assertEqual(dossier["domains"]["clinical_design"]["status"], "source_record_only")
        self.assertIsNone(dossier["overall_score"])
        self.assertTrue(dossier["read_only"])
        for domain in dossier["domains"].values():
            self.assertIsNone(domain["score"])
            self.assertTrue(all(
                c["verification_status"] == "source_record_only" and
                not c["scientifically_verified"]
                for c in domain["claims"]
            ))

    def test_digest_tamper_rejected(self):
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.dossier(digest="0" * 64)

    def test_invalid_digest_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA256"):
            self.dossier(digest="wrong")

    def test_wrong_nct_rejected(self):
        with self.assertRaisesRegex(ValueError, "identities differ"):
            self.dossier(nct_id="NCT87654321")

    def test_truncated_archive_rejected(self):
        with self.assertRaises(ValueError):
            self.dossier(payload=self.payload[:15])

    def test_decompression_limit_rejected(self):
        oversized = b"x" * (MAX_ARCHIVE_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "size limit"):
            self.dossier(payload=gzip.compress(oversized))

    def test_noncanonical_archive_rejected(self):
        raw = json.dumps(self.registry, indent=2).encode()
        with self.assertRaisesRegex(ValueError, "canonical"):
            self.dossier(payload=gzip.compress(raw), digest=hashlib.sha256(raw).hexdigest())

    def test_timezone_naive_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            self.dossier(fetched_at=datetime(2026, 10, 24))


if __name__ == "__main__":
    unittest.main()
