import io
import json
from email.message import Message
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_system_status_production import REQUIRED_TEXT, verify_html, verify_unauthenticated_protected_api


def http_error(status: int, body: dict):
    headers = Message()
    headers["Content-Type"] = "application/json"
    return urllib.error.HTTPError(
        "https://pdufa-new-dashboard.vercel.app/api/assessments",
        status, "Unauthenticated", headers,
        io.BytesIO(json.dumps(body).encode("utf-8")),
    )


class ProductionSmokeValidatorTests(unittest.TestCase):
    def test_all_fifteen_sections_and_protected_science_outcome_controls_are_required(self):
        self.assertEqual(len(REQUIRED_TEXT), 23)
        self.assertEqual(len(set(REQUIRED_TEXT)), 23)
        self.assertIn("These gate counts do not measure percentage of engineering hours remaining.", REQUIRED_TEXT)
        verify_html("<html>" + " ".join(REQUIRED_TEXT).replace("&", "&amp;") + "</html>")

    def test_unauthenticated_challenge_or_partial_page_fails(self):
        with self.assertRaisesRegex(ValueError, "Production page did not contain"):
            verify_html("<html><title>Authentication Required</title></html>")
        for label in ["Final Acceptance", "SCIENCE · 40 investigations", "OUTCOME · historical FDA validation"]:
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "Production page did not contain"):
                    verify_html(" ".join(REQUIRED_TEXT).replace(label, ""))

    def test_both_protected_api_routes_fail_closed_with_unauthenticated_401(self):
        for endpoint in ["/api/assessments", "/api/hop/readiness"]:
            with self.subTest(endpoint=endpoint):
                with patch("check_system_status_production.urllib.request.urlopen", side_effect=http_error(401, {"error": "Authentication required"})):
                    verify_unauthenticated_protected_api(endpoint)

    def test_unprotected_or_misconfigured_endpoints_fail(self):
        for status, payload in [(403, {"error": "Forbidden"}), (401, {"private": "evidence"}), (200, {})]:
            with self.subTest(status=status):
                if status == 200:
                    from unittest.mock import MagicMock
                    with patch("check_system_status_production.urllib.request.urlopen", return_value=MagicMock(status=200)):
                        with self.assertRaisesRegex(ValueError, "accessible without a session"):
                            verify_unauthenticated_protected_api("/api/assessments")
                else:
                    with patch("check_system_status_production.urllib.request.urlopen", side_effect=http_error(status, payload)):
                        with self.assertRaises(ValueError):
                            verify_unauthenticated_protected_api("/api/assessments")
        with self.assertRaisesRegex(ValueError, "Unexpected protected API path"):
            verify_unauthenticated_protected_api("/api/orders")


if __name__ == "__main__":
    unittest.main()
