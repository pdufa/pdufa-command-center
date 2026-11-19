"""Offline tests for the primary registry retrieval boundary; no network needed."""
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_focus_registry_evidence import retrieve


class Response:
    def __init__(self, payload, url="https://clinicaltrials.gov/api/v2/studies/NCT05507203"):
        self.payload = payload
        self.url = url
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit):
        return self.payload
    def geturl(self):
        return self.url


class RegistryEvidenceTests(unittest.TestCase):
    def test_success_requires_matching_primary_nct_and_hashes_payload(self):
        raw = json.dumps({"protocolSection": {
            "identificationModule": {"nctId": "NCT05507203"},
            "statusModule": {"statusVerifiedDate": "2026-09"},
        }, "resultsSection": {"outcomeMeasuresModule": {}}}).encode()
        with patch("fetch_focus_registry_evidence.urlopen", return_value=Response(raw)) as call:
            record, metadata = retrieve("NCT05507203")
        self.assertEqual(metadata["source_url"], "https://clinicaltrials.gov/api/v2/studies/NCT05507203")
        self.assertEqual(metadata["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertTrue(metadata["has_results_section"])
        self.assertEqual(metadata["scientific_adjudication"], "NOT_ADJUDICATED")
        self.assertIsNone(metadata["fda_probability"])
        self.assertEqual(record["protocolSection"]["identificationModule"]["nctId"], "NCT05507203")

    def test_mismatched_nct_rejected(self):
        raw = b'{"protocolSection":{"identificationModule":{"nctId":"NCT00000000"}}}'
        with patch("fetch_focus_registry_evidence.urlopen", return_value=Response(raw)):
            with self.assertRaisesRegex(ValueError, "does not match"):
                retrieve("NCT05507203")

    def test_malformed_nct_never_calls_network(self):
        with patch("fetch_focus_registry_evidence.urlopen") as call:
            with self.assertRaisesRegex(ValueError, "exactly eight digits"):
                retrieve("NCT05507203/../../")
            call.assert_not_called()

    def test_oversized_response_rejected(self):
        with patch("fetch_focus_registry_evidence.urlopen", return_value=Response(b"x" * 12_000_001)):
            with self.assertRaisesRegex(ValueError, "size limit"):
                retrieve("NCT05507203")

    def test_redirected_response_is_rejected(self):
        raw = b'{"protocolSection":{"identificationModule":{"nctId":"NCT05507203"}}}'
        response = Response(raw, "https://example.org/NCT05507203")
        with patch("fetch_focus_registry_evidence.urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "did not originate"):
                retrieve("NCT05507203")

if __name__ == "__main__":
    unittest.main()
