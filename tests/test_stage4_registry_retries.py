import importlib.util
import io
import json
import unittest
from pathlib import Path
from urllib.error import HTTPError

PATH = Path(__file__).resolve().parents[1] / "scripts" / "stage4_clinicaltrials_source.py"
spec = importlib.util.spec_from_file_location("stage4_clinicaltrials_source_retry", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RetryTests(unittest.TestCase):
    def test_transient_http_failure_retries(self):
        calls = []
        def opener(request, timeout):
            calls.append(timeout)
            if len(calls) == 1:
                raise HTTPError(request.full_url, 503, "Unavailable", {}, None)
            return io.BytesIO(json.dumps({"protocolSection": {
                "identificationModule": {"nctId": "NCT00000001"}}}).encode())
        sleeps = []
        result = module.fetch_study("NCT00000001", opener=opener, sleeper=sleeps.append)
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [1])
        self.assertIsNone(result["prediction"])

    def test_nonretryable_http_failure_stops(self):
        calls = []
        def opener(request, timeout):
            calls.append(1)
            raise HTTPError(request.full_url, 404, "Not found", {}, None)
        with self.assertRaises(HTTPError):
            module.fetch_study("NCT00000001", opener=opener, sleeper=lambda _: None)
        self.assertEqual(len(calls), 1)

    def test_retry_budget_is_bounded(self):
        calls = []
        def opener(request, timeout):
            calls.append(1)
            raise HTTPError(request.full_url, 429, "Rate limit", {}, None)
        with self.assertRaises(HTTPError):
            module.fetch_study("NCT00000001", opener=opener, sleeper=lambda _: None)
        self.assertEqual(len(calls), 3)


if __name__ == "__main__":
    unittest.main()
