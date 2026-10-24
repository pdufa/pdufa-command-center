import gzip
import hashlib
import json
import unittest
from app.scientific_stored_record import evidence_from_archive


class StoredRecordEvidenceTests(unittest.TestCase):
    def setUp(self):
        raw = json.dumps({"protocolSection": {"identificationModule": {"nctId": "NCT12345678"}}}).encode()
        self.archive = gzip.compress(raw)
        self.digest = hashlib.sha256(raw).hexdigest()

    def test_valid_archive_preserves_provenance_and_no_scores(self):
        result = evidence_from_archive("NCT12345678", self.archive, self.digest)
        self.assertEqual(result["sourceUrl"], "https://clinicaltrials.gov/study/NCT12345678")
        self.assertEqual(result["scoringEvidence"], {})

    def test_modified_checksum_rejected(self):
        with self.assertRaisesRegex(ValueError, "checksum"):
            evidence_from_archive("NCT12345678", self.archive, "0" * 64)

    def test_mismatched_nct_rejected(self):
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            evidence_from_archive("NCT87654321", self.archive, self.digest)


if __name__ == "__main__":
    unittest.main()
