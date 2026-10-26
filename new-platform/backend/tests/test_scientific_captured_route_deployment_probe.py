"""No-secret route presence probe; never certifies clinical source authenticity."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from app import scientific_captured_route_deployment_probe as probe


class CapturedRouteDeploymentProbeTests(unittest.TestCase):
    def test_anonymous_401_indicates_guard_only_never_verified_documents(self):
        data = probe.classify(401)
        self.assertEqual(data["classification"], "ANONYMOUS_AUTH_GUARD_PRESENT")
        self.assertTrue(data["anonymousAccessSafelyDenied"])
        self.assertFalse(data["capturedManifestReadWithCredential"])
        self.assertFalse(data["archivedPdfCountKnown"])
        self.assertFalse(data["originalSourceAuthenticated"])
        self.assertFalse(data["reviewerIdentityVerified"])
        self.assertFalse(data["scientificAdjudicationCompleted"])
        self.assertFalse(data["promotionAllowed"])
        self.assertIsNone(data["fdaApprovalProbability"])

    def test_missing_route_is_not_mistaken_for_an_empty_archive(self):
        value = probe.classify(404)
        self.assertEqual(value["classification"], "CAPTURED_ROUTE_NOT_DEPLOYED")
        self.assertFalse(value["archivedPdfCountKnown"])
        self.assertFalse(value["anonymousAccessSafelyDenied"])
        self.assertFalse(value["promotionAllowed"])

    def test_security_failure_anonymous_success_is_detected(self):
        for code in (200, 201, 204, 206, 299):
            with self.subTest(code=code):
                self.assertEqual(probe.classify(code)["classification"],
                                 "SECURITY_FAILURE_ANONYMOUS_READ_ACCEPTED")
        for code in (403, 407, 302, 500, 502, 503, None):
            with self.subTest(code=code):
                data = probe.classify(code)
                self.assertNotEqual(data["classification"], "ANONYMOUS_AUTH_GUARD_PRESENT")
                self.assertNotEqual(data["classification"], "SECURITY_FAILURE_ANONYMOUS_READ_ACCEPTED")
                self.assertFalse(data["capturedManifestReadWithCredential"])
        for code in (-1, 0, 600, "401", True):
            with self.subTest(code=code), self.assertRaises(ValueError):
                probe.classify(code)

    def test_fixed_unauthenticated_url_never_follows_redirects_or_sends_keys(self):
        requests = []
        class FakeOpener:
            def open(self, request, timeout):
                requests.append((request, timeout))
                raise HTTPError(probe.ROUTE, 401, "Unauthorized", {}, None)
        with patch.object(probe, "build_opener", return_value=FakeOpener()) as build:
            status = probe.anonymous_http_status()
        self.assertEqual(status, 401)
        request, timeout = requests[0]
        self.assertEqual(request.full_url, probe.ROUTE)
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.headers, {"Accept": "application/json"})
        self.assertLessEqual(timeout, 35)
        self.assertEqual(len(build.call_args.args), 2)
        self.assertIsInstance(build.call_args.args[0], probe.ProxyHandler)
        self.assertIsInstance(build.call_args.args[1], probe._NoRedirect)

    def test_network_failure_stays_unavailable_not_a_science_grade(self):
        class FakeOpener:
            def open(self, request, timeout):
                raise URLError("offline")
        with patch.object(probe, "build_opener", return_value=FakeOpener()):
            self.assertIsNone(probe.anonymous_http_status())
        self.assertEqual(probe.classify(None)["classification"], "RENDER_BACKEND_UNAVAILABLE")

    def test_cli_writes_credential_free_summary_and_fails_only_for_anonymous_2xx(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.md"
            for http_code, expected_exit in ((401, 0), (404, 0), (503, 0), (200, 1)):
                with self.subTest(http_code=http_code), patch.object(
                    probe, "anonymous_http_status", return_value=http_code
                ), patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(path)}):
                    self.assertEqual(probe.main(), expected_exit)
                saved = path.read_text(encoding="utf-8")
                self.assertIn("Captured PDF archive backend deployment parity", saved)
                self.assertNotIn("PDUFA_INTERNAL_API_KEY", saved)
                self.assertNotIn("secret", saved.lower())
                self.assertNotIn("source_url", saved.lower())
                self.assertNotIn("fda approval probability:", saved.lower())


if __name__ == "__main__":
    unittest.main()
