"""Confirm isolated HTTP scientific release contract without any source import."""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app, get_scientific_assessment


class ScientificIntegratedHttpContractTests(unittest.TestCase):
    def test_integrated_contract_is_reported_only_by_authenticated_http(self):
        with patch.dict(os.environ, {"PDUFA_INTERNAL_API_KEY": "integration-unit-test-key"}), \
             patch("app.main.storage_ready", return_value=False):
            with TestClient(app) as client:
                denied = client.get("/api/scientific-assessment",
                                    params={"exact_id": "TRIAL|NCT12345678"})
                self.assertEqual(denied.status_code, 401)
                accepted = client.get(
                    "/api/scientific-assessment",
                    params={"exact_id": "TRIAL|NCT12345678"},
                    headers={"x-pdufa-internal-key": "integration-unit-test-key"},
                )
                self.assertEqual(accepted.status_code, 200, accepted.text[:250])
                self.assertEqual(
                    accepted.headers.get("x-pdufa-scientific-api-contract"),
                    "science-integrated-v1",
                )
                self.assertEqual(accepted.headers.get("cache-control"),
                                 "private, no-store")
                payload = accepted.json()
                self.assertEqual(payload["exactId"], "TRIAL|NCT12345678")
                self.assertIsNone(payload["assessment"]["overall_score"])
                self.assertIsNone(payload["readinessGrades"])
                self.assertIsNone(payload["investigation20"])
                self.assertIsNone(payload["investigation40"])
                self.assertIsNone(payload["registryEvidence"])

    def test_direct_api_helper_retains_old_single_argument_signature(self):
        with patch("app.main.storage_ready", return_value=False):
            result = get_scientific_assessment("TRIAL|NCT12345678")
        self.assertEqual(result["exactId"], "TRIAL|NCT12345678")
        self.assertIsNone(result["assessment"]["overall_score"])


if __name__ == "__main__":
    unittest.main()
