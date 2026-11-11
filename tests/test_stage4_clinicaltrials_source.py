import importlib.util
import io
import json
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "stage4_clinicaltrials_source.py"
spec = importlib.util.spec_from_file_location("stage4_clinicaltrials_source", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ClinicalTrialsSourceTests(unittest.TestCase):
    def test_registry_metadata_is_not_scientific_verification(self):
        payload = {"protocolSection": {
            "identificationModule": {"nctId": "NCT05507203"},
            "designModule": {"phases": ["PHASE3"]},
            "statusModule": {"overallStatus": "COMPLETED"}}}
        result = module.fetch_study("NCT05507203", opener=lambda request, timeout: Response(json.dumps(payload).encode()))
        self.assertEqual(result["phase"], ["PHASE3"])
        self.assertFalse(result["scientifically_verified"])
        self.assertIsNone(result["prediction"])

    def test_mismatched_registry_id_fails(self):
        payload = {"protocolSection": {"identificationModule": {"nctId": "NCT00000000"}}}
        with self.assertRaises(ValueError):
            module.fetch_study("NCT05507203", opener=lambda request, timeout: Response(json.dumps(payload).encode()))

    def test_bad_id_rejected_before_request(self):
        with self.assertRaises(ValueError):
            module.fetch_study("https://example.com")

    def test_failures_are_recorded_not_counted_as_verified(self):
        roster = json.loads(module.ROSTER.read_text(encoding="utf-8"))
        result = module.collect(roster, fetcher=lambda nct: (_ for _ in ()).throw(TimeoutError()))
        self.assertEqual(len(result["trials"]), 29)
        self.assertTrue(all(t["status"] == "retrieval_failed" for t in result["trials"]))
        self.assertEqual(result["scientific_adjudications"], 0)


if __name__ == "__main__":
    unittest.main()
