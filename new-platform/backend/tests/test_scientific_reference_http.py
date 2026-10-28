"""Source lookup API contract: explicit opt-in, authentication and no-scoring."""
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
from app.scientific_external_sources import SourceLookupError


class ScientificDossierReferenceHttpTests(unittest.TestCase):
    def setUp(self):
        source = {"protocolSection": {
            "identificationModule": {"nctId": "NCT12345678"},
            "designModule": {"designInfo": {"allocation": "RANDOMIZED"}},
        }}
        raw = json.dumps(source, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode()
        self.record = SimpleNamespace(
            payload_gzip=gzip.compress(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            fetched_at=datetime(2026, 10, 24, tzinfo=timezone.utc),
        )
        app.dependency_overrides[require_storage] = lambda: None
        self.client = TestClient(app)
        self.headers = {"x-pdufa-internal-key": "external-references-test"}
        self.env = patch.dict(os.environ, {
            "PDUFA_INTERNAL_API_KEY": "external-references-test",
            "PDUFA_SCIENTIFIC_EXTERNAL_LOOKUP_ENABLED": "1",
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

    def get(self, exact_id="TRIAL|NCT12345678", application_number="", auth=True):
        params = {"exact_id": exact_id}
        if application_number:
            params["application_number"] = application_number
        return self.client.get("/api/scientific-assessment/dossier/references",
                               params=params, headers=self.headers if auth else {})

    @patch("app.scientific_external_sources.lookup_pubmed_nct")
    def test_disabled_by_default_no_db_no_network(self, lookup):
        with patch.dict(os.environ, {"PDUFA_SCIENTIFIC_EXTERNAL_LOOKUP_ENABLED": ""}):
            response = self.get()
        self.assertEqual(response.status_code, 404)
        self.Session.assert_not_called()
        lookup.assert_not_called()

    @patch("app.scientific_external_sources.lookup_pubmed_nct")
    def test_auth_required_even_when_disabled(self, lookup):
        self.assertEqual(self.get(auth=False).status_code, 401)
        self.Session.assert_not_called()
        lookup.assert_not_called()

    @patch("app.scientific_external_sources.lookup_pubmed_nct")
    def test_success_pubmed_only_unscored(self, lookup):
        lookup.return_value = {
            "status": "indexed_references_found", "requested_nct_id": "NCT12345678",
            "references": [{
                "kind": "pubmed_citation", "pmid": "123",
                "source_url": "https://pubmed.ncbi.nlm.nih.gov/123/",
                "scientifically_verified": False,
            }],
        }
        response = self.get()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(body["reference_lookups"]["fda"], "not_requested")
        self.assertFalse(body["reference_lookups"]["fda_application_linked_to_trial"])
        self.assertEqual(len(body["domains"]["clinical_results"]["research_leads"]), 1)
        self.assertTrue(all(x["score"] is None for x in body["domains"].values()))
        self.assertIsNone(body["fda_approval_probability"])
        self.assertIsNone(body["overall_score"])
        lookup.assert_called_once_with("NCT12345678")

    @patch("app.scientific_external_sources.lookup_fda_application")
    @patch("app.scientific_external_sources.lookup_pubmed_nct")
    def test_fda_requires_explicit_application_number(self, pubmed, fda):
        pubmed.return_value = {
            "status": "no_indexed_references_found",
            "requested_nct_id": "NCT12345678", "references": [],
        }
        fda.return_value = {
            "status": "application_found",
            "requested_application_number": "NDA012345",
            "references": [{
                "application_number": "NDA012345",
                "trial_association_verified": False,
                "scientifically_verified": False,
            }],
        }
        self.assertEqual(self.get().status_code, 200)
        fda.assert_not_called()
        response = self.get(application_number="NDA012345")
        self.assertEqual(response.status_code, 200)
        fda.assert_called_once_with("NDA012345")
        self.assertEqual(response.json()["reference_lookups"]["fda"], "application_found")
        self.assertFalse(response.json()["reference_lookups"]["fda_application_linked_to_trial"])

    @patch("app.scientific_external_sources.lookup_pubmed_nct")
    def test_invalid_ids_fail_before_network_and_storage(self, lookup):
        for exact in ("BAD", "TRIAL|NCT12345678Z", "PDUFA-000123"):
            with self.subTest(exact=exact):
                self.assertEqual(self.get(exact_id=exact).status_code, 422)
        self.assertEqual(self.get(application_number="NDA123456X").status_code, 422)
        self.Session.assert_not_called()
        lookup.assert_not_called()

    @patch("app.scientific_external_sources.lookup_pubmed_nct")
    def test_missing_stored_record_does_not_call_external_source(self, lookup):
        self.Session.return_value.__enter__.return_value.get.return_value = None
        self.assertEqual(self.get().status_code, 404)
        lookup.assert_not_called()

    @patch("app.scientific_external_sources.lookup_pubmed_nct")
    def test_bad_archive_does_not_call_external_source(self, lookup):
        self.record.sha256 = "0" * 64
        self.assertEqual(self.get().status_code, 503)
        lookup.assert_not_called()

    @patch("app.scientific_external_sources.lookup_pubmed_nct")
    def test_source_failure_is_not_negative_trial_evidence(self, lookup):
        lookup.side_effect = SourceLookupError("Scientific source unavailable")
        response = self.get()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("domains", response.json())


if __name__ == "__main__":
    unittest.main()
