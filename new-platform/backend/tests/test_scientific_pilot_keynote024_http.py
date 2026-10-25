"""Read-only endpoint contracts for the historic KEYNOTE-024 pilot.

All storage is mocked; no live database, external service, or deployment needed.
"""
import gzip
import hashlib
import json
import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app, require_storage


class Keynote024PilotHttpTests(unittest.TestCase):
    def setUp(self):
        source = {"protocolSection": {
            "identificationModule": {"nctId": "NCT02142738"},
            "designModule": {"designInfo": {
                "allocation": "RANDOMIZED", "maskingInfo": {"masking": "NONE"}},
                "enrollmentInfo": {"count": 305}},
        }}
        raw = json.dumps(source, sort_keys=True,
                         separators=(",", ":"), ensure_ascii=False).encode()
        self.record = SimpleNamespace(
            payload_gzip=gzip.compress(raw), sha256=hashlib.sha256(raw).hexdigest(),
            fetched_at=datetime(2026, 10, 24, tzinfo=timezone.utc),
        )
        app.dependency_overrides[require_storage] = lambda: None
        self.client = TestClient(app)
        self.header = {"x-pdufa-internal-key": "historical-pilot-test-secret"}
        self.env = patch.dict(os.environ, {
            "PDUFA_INTERNAL_API_KEY": "historical-pilot-test-secret",
        })
        self.env.start()
        self.db = patch("app.main.Session")
        self.Session = self.db.start()
        self.Session.return_value.__enter__.return_value.get.return_value = self.record

    def tearDown(self):
        self.db.stop()
        self.env.stop()
        app.dependency_overrides.clear()
        self.client.close()

    def get(self, authenticated=True):
        return self.client.get(
            "/api/scientific-assessment/pilot/keynote024",
            headers=self.header if authenticated else {},
        )

    def test_requires_authentication_without_touching_database(self):
        response = self.get(authenticated=False)
        self.assertEqual(response.status_code, 401)
        self.Session.assert_not_called()

    def test_no_archive_returns_404(self):
        self.Session.return_value.__enter__.return_value.get.return_value = None
        self.assertEqual(self.get().status_code, 404)

    def test_corrupt_archive_fails_closed(self):
        self.record.sha256 = "0" * 64
        response = self.get()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("publishedResults", response.json())

    def test_research_response_contains_separate_results_and_no_scores(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        result = response.json()
        self.assertEqual(result["dossier"]["nct_id"], "NCT02142738")
        self.assertEqual(result["pilot"]["nct_id"], "NCT02142738")
        self.assertEqual(result["publishedResults"]["nct_id"], "NCT02142738")
        self.assertEqual(len(result["publishedResults"]["analysis_snapshots"]), 3)
        self.assertIsNone(result["dossier"]["overall_score"])
        self.assertIsNone(result["publishedResults"]["overall_score"])
        self.assertIsNone(result["publishedResults"]["fda_approval_probability"])
        self.assertFalse(result["scoringModified"])
        self.assertFalse(result["qualificationPresetsModified"])
        self.assertTrue(result["researchOnly"])
        self.Session.return_value.__enter__.return_value.get.assert_called_once()

    def test_no_live_lookup_or_background_scan_in_endpoint(self):
        with patch("app.scientific_external_sources._read_json") as external:
            response = self.get()
            self.assertEqual(response.status_code, 200)
            external.assert_not_called()


if __name__ == "__main__":
    unittest.main()
