import io
import json
from email.message import Message
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_system_status_production import REQUIRED_TEXT, normalize_base_url, verify_html, verify_unauthenticated_protected_api, main


def http_error(status: int, body: dict, url="https://pdufa-new-dashboard.vercel.app/api/assessments"):
    headers = Message()
    headers["Content-Type"] = "application/json"
    return urllib.error.HTTPError(
        url,
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
        for label in ["Final Acceptance", "Deep Medical Intelligence · independent investigation", "OUTCOME · historical FDA validation"]:
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "Production page did not contain"):
                    verify_html(" ".join(REQUIRED_TEXT).replace(label, ""))

    def test_both_protected_api_routes_fail_closed_with_unauthenticated_401(self):
        for endpoint in ["/api/assessments", "/api/hop/readiness", "/api/phase3-registry?exact_nct=NCT02142738"]:
            with self.subTest(endpoint=endpoint):
                with patch("check_system_status_production.urllib.request.urlopen", side_effect=http_error(401, {"error": "Authentication required"}, "https://pdufa-new-dashboard.vercel.app" + endpoint)):
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


class SmokeBaseUrlTests(unittest.TestCase):
    def test_only_project_https_or_ci_loopback_origins_are_allowed(self):
        for value, expected in [
            ("https://pdufa-new-dashboard.vercel.app/", "https://pdufa-new-dashboard.vercel.app"),
            ("https://pdufa-new-dashboard-pdufa.vercel.app:443", "https://pdufa-new-dashboard-pdufa.vercel.app"),
            ("http://127.0.0.1:3012", "http://127.0.0.1:3012"),
            ("http://localhost:3012/", "http://localhost:3012"),
        ]:
            with self.subTest(value=value):
                self.assertEqual(normalize_base_url(value), expected)
        for value in [
            "http://pdufa-new-dashboard.vercel.app", "https://attacker.example",
            "https://pdufa-new-dashboard.vercel.app.attacker.example",
            "https://other-project.vercel.app", "file:///etc/passwd", "ftp://localhost:3012",
            "https://user:password@pdufa-new-dashboard.vercel.app",
            "https://pdufa-new-dashboard.vercel.app:8443", "http://127.0.0.2:3012",
            "http://127.0.0.1:0", "http://localhost:99999", "http://localhost:3012/admin",
            "http://localhost:3012?token=private", "http://localhost:3012#fragment",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_base_url(value)

    def test_local_protected_routes_require_same_origin_and_same_path(self):
        base = "http://127.0.0.1:3012"
        path = "/api/hop/readiness"
        with patch("check_system_status_production.urllib.request.urlopen",
                   side_effect=http_error(401, {"error": "Authentication required"}, base + path)) as fetch:
            verify_unauthenticated_protected_api(path, base)
            self.assertEqual(fetch.call_args.args[0].full_url, base + path)
        for url in ["http://127.0.0.1:3013" + path, "http://localhost:3012" + path,
                    "https://127.0.0.1:3012" + path, base + "/api/assessments"]:
            with self.subTest(url=url):
                with patch("check_system_status_production.urllib.request.urlopen",
                           side_effect=http_error(401, {"error": "Authentication required"}, url)):
                    with self.assertRaisesRegex(ValueError, "redirect"):
                        verify_unauthenticated_protected_api(path, base)

    def test_invalid_cli_base_is_rejected_before_any_request(self):
        with patch("check_system_status_production.urllib.request.urlopen") as fetch:
            self.assertEqual(main(["--base-url", "https://attacker.example"]), 1)
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
