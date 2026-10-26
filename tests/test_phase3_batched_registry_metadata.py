import csv
import io
import json
from unittest.mock import patch
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_phase3_batched_registry_metadata import audit, parse_batch, fetch_batch, TRIALS


class BatchedRegistryMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with TRIALS.open(newline="", encoding="utf-8-sig") as handle:
            cls.rows = list(csv.DictReader(handle))
        cls.by_id = {r["nct_id"]: r for r in cls.rows}

    def fake_fetch(self, nct_ids):
        return {nct: {"nct_id": nct, "live_registry_lead_sponsor": self.by_id[nct]["company"]}
                for nct in nct_ids}

    def test_happy_path_all_741_still_no_rights_or_pdufa(self):
        result = audit(self.fake_fetch, lambda _: None)
        self.assertEqual(result["registry_metadata_retrieved"], 741)
        self.assertEqual(result["saved_vs_current_lead_sponsor_equal"], 741)
        self.assertEqual(result["registry_metadata_unresolved"], 0)
        self.assertEqual(len({r["ticker"] for r in result["trials"]}), 130)
        self.assertEqual(result["current_legal_rights_verified"], 0)
        self.assertEqual(result["fda_pdufa_verified"], 0)
        self.assertIsNone(result["qualified_pipeline_count"])
        self.assertTrue(all(r["qualified_pipeline"] is None for r in result["trials"]))

    def test_missing_one_id_remains_unresolved(self):
        omitted = self.rows[0]["nct_id"]
        def missing(ids):
            found = self.fake_fetch(ids)
            found.pop(omitted, None)
            return found
        result = audit(missing, lambda _: None)
        self.assertEqual(result["registry_metadata_retrieved"], 740)
        self.assertEqual(result["registry_metadata_unresolved"], 1)
        item = next(r for r in result["trials"] if r["nct_id"] == omitted)
        self.assertIsNone(item["current_registry_metadata"])
        self.assertIsNone(item["sponsor_name_equal"])
        self.assertIsNone(item["qualified_pipeline"])

    def test_entire_failed_batches_are_never_silently_successful(self):
        def fail(ids):
            raise ValueError("Mock 429 rate limit")
        result = audit(fail, lambda _: None)
        self.assertEqual(result["registry_metadata_retrieved"], 0)
        self.assertEqual(result["registry_metadata_unresolved"], 741)
        self.assertTrue(all(x["error"] for x in result["trials"]))

    def test_api_pagination_returns_only_exact_requested_ids(self):
        class FakeResponse:
            status = 200
            def __init__(self, content):
                self._handle = io.BytesIO(json.dumps(content).encode())
            def read(self, count):
                return self._handle.read(count)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        first = {"studies": [{"protocolSection": {
            "identificationModule": {"nctId": "NCT12345678"},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Sponsor A"}}}}],
            "nextPageToken": "opaque-one"}
        second = {"studies": [{"protocolSection": {
            "identificationModule": {"nctId": "NCT12345679"},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Sponsor B"}}}}]}
        responses = iter([FakeResponse(first), FakeResponse(second)])
        seen_urls = []
        def fake_urlopen(request, timeout):
            seen_urls.append(request.full_url)
            return next(responses)
        with patch("audit_phase3_batched_registry_metadata.urllib.request.urlopen", fake_urlopen):
            result = fetch_batch(["NCT12345678", "NCT12345679"], lambda _: None)
        self.assertEqual(set(result), {"NCT12345678", "NCT12345679"})
        self.assertEqual(len(seen_urls), 2)
        self.assertIn("pageToken=opaque-one", seen_urls[1])

    def test_reject_unexpected_identity(self):
        response = {"studies": [{"protocolSection": {
            "identificationModule": {"nctId": "NCT99999999"}}}]}
        with self.assertRaisesRegex(ValueError, "unexpected"):
            parse_batch(["NCT12345678"], response)


if __name__ == "__main__":
    unittest.main()
