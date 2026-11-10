"""Offline tests for direct registry retrieval provenance and fail-closed behavior."""
import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/fetch_focus_registry_record.py"
spec = importlib.util.spec_from_file_location("focus_registry_fetch", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class MockResponse:
    def __init__(self, body):
        self.body = io.BytesIO(body)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit):
        return self.body.read(limit)

class RegistryFetchTests(unittest.TestCase):
    def test_source_identity_and_provenance(self):
        body = json.dumps({"protocolSection": {
            "identificationModule": {"nctId": "NCT05507203"},
            "statusModule": {"statusVerifiedDate": "2026-10"},
            "outcomesModule": {"primaryOutcomes": []}
        }}).encode()
        with patch.object(module.urllib.request, "urlopen", return_value=MockResponse(body)) as fetch:
            result = module.retrieve("NCT05507203")
        self.assertEqual(result["nct"], "NCT05507203")
        self.assertEqual(result["source_url"], "https://clinicaltrials.gov/api/v2/studies/NCT05507203")
        self.assertEqual(len(result["raw_sha256"]), 64)
        self.assertFalse(result["results_section_present"])
        self.assertEqual(result["raw_record"]["protocolSection"]["identificationModule"]["nctId"], "NCT05507203")
        self.assertEqual(result["verification_status"], "SOURCE_RETRIEVED_NOT_INDEPENDENTLY_ADJUDICATED")
        self.assertEqual(fetch.call_count, 1)

    def test_mismatched_nct_is_rejected(self):
        body = b'{"protocolSection":{"identificationModule":{"nctId":"NCT00000000"}}}'
        with patch.object(module.urllib.request, "urlopen", return_value=MockResponse(body)):
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                module.retrieve("NCT05507203")

    def test_invalid_nct_is_rejected_before_network(self):
        with patch.object(module.urllib.request, "urlopen") as fetch:
            with self.assertRaises(ValueError):
                module.retrieve("../secrets")
            fetch.assert_not_called()

if __name__ == "__main__":
    unittest.main()
