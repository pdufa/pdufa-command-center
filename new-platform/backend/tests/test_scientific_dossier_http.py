"""HTTP contracts for authenticated, read-only eight-domain dossiers.

All responses use a mocked archive record. No staging/production credentials,
live network, import, or database mutation is required.
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


class ScientificDossierHttpTests(unittest.TestCase):
    def setUp(self):
        self.source = {"protocolSection": {
            "identificationModule": {"nctId": "NCT12345678"},
            "designModule": {"designInfo": {"allocation": "RANDOMIZED"}},
        }}
        raw = json.dumps(self.source, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode()
        self.record = SimpleNamespace(
            payload_gzip=gzip.compress(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            fetched_at=datetime(2026, 10, 24, tzinfo=timezone.utc),
        )
        app.dependency_overrides[require_storage] = lambda: None
        self.client = TestClient(app)
        self.header = {"x-pdufa-internal-key": "dossier-test-secret"}
        self.env = patch.dict(os.environ, {"PDUFA_INTERNAL_API_KEY": "dossier-test-secret"})
        self.env.start()
        self.mock_session = patch("app.main.Session")
        self.Session = self.mock_session.start()
        self.Session.return_value.__enter__.return_value.get.return_value = self.record

    def tearDown(self):
        self.mock_session.stop()
        self.env.stop()
        app.dependency_overrides.clear()
        self.client.close()

    def request(self, exact_id="TRIAL|NCT12345678", headers=None):
        return self.client.get("/api/scientific-assessment/dossier",
                               params={"exact_id": exact_id}, headers=headers or {})

    def test_requires_authentication(self):
        response = self.request()
        self.assertEqual(response.status_code, 401)
        self.Session.assert_not_called()

    def test_success_source_only_never_scored(self):
        response = self.request(headers=self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        body = response.json()
        self.assertEqual(body["exact_program_id"], "TRIAL|NCT12345678")
        self.assertEqual(len(body["domains"]), 8)
        self.assertEqual(body["domains"]["clinical_design"]["status"], "source_record_only")
        self.assertIsNone(body["overall_score"])
        self.assertIsNone(body["fda_approval_probability"])
        self.Session.return_value.__enter__.return_value.get.assert_called_once()

    def test_rejects_incorrect_identity_without_touching_storage(self):
        for bad in ("TRIAL|NCT12345678X", "PDUFA-000123", "TRIAL|BAD", "NCT12345678"):
            with self.subTest(bad=bad):
                self.assertEqual(self.request(bad, self.header).status_code, 422)
        self.Session.assert_not_called()

    def test_unknown_record_returns_404(self):
        self.Session.return_value.__enter__.return_value.get.return_value = None
        self.assertEqual(self.request(headers=self.header).status_code, 404)

    def test_bad_archive_fails_closed(self):
        self.record.sha256 = "0" * 64
        response = self.request(headers=self.header)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("domains", response.json())


if __name__ == "__main__":
    unittest.main()
