"""Offline tests for the anonymous isolated source-route diagnostic.

All HTTP status responses are mocked; these tests never contact Render,
access credentials, capture PDFs or claim a deployed scientific backend.
"""
import io
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from app import scientific_captured_route_probe as probe


class Response:
    def __init__(self, status):
        self.status = status
        self.read_called = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, *_):
        self.read_called = True
        raise AssertionError("Never read protected backend payload")


class FakeOpener:
    def __init__(self, status):
        self.status = status
        self.requests = []
        self.response = Response(status)

    def open(self, request, timeout=0):
        self.requests.append((request, timeout))
        if isinstance(self.status, Exception):
            raise self.status
        if self.status >= 400:
            raise HTTPError(request.full_url, self.status, "intentionally unread", {}, None)
        return self.response


class CapturedRouteProbeTests(TestCase):
    def test_one_read_only_request_to_frozen_pilot_without_auth_or_body_reads(self):
        for status in (200, 302, 401, 404, 403, 503):
            with self.subTest(status=status):
                opener = FakeOpener(status)
                result = probe.probe(opener)
                self.assertEqual(result.http_status, status)
                self.assertEqual(len(opener.requests), 1)
                request, timeout = opener.requests[0]
                self.assertEqual(request.full_url, probe.PILOT_URL)
                self.assertEqual(request.get_method(), "GET")
                self.assertEqual(timeout, 90)
                self.assertFalse(request.data)
                self.assertEqual(request.header_items(), [])
                self.assertFalse(opener.response.read_called)
                self.assertFalse(result.evidence_of_deployed_contract)
                self.assertFalse(result.independent_clinical_verification)

    def test_401_alone_cannot_attest_current_backend_contract(self):
        report = probe.render_report(probe.classify(401))
        self.assertEqual(report["routeObservation"], "ANONYMOUS_ACCESS_DENIED_VERSION_UNCONFIRMED")
        self.assertFalse(report["authenticatedContractAndDeploymentVerified"])
        self.assertFalse(report["clinicalSourceAuthenticated"])
        self.assertIsNone(report["scientificScore"])
        self.assertIsNone(report["fdaApprovalProbability"])

    def test_404_is_unconfirmed_version_not_validated_empty_archive(self):
        r = probe.classify(404)
        self.assertEqual(r.status, "ROUTE_NOT_FOUND_POSSIBLY_NOT_DEPLOYED")
        self.assertFalse(r.evidence_of_deployed_contract)

    def test_2xx_and_redirect_are_fail_closed_but_other_statuses_remain_unconfirmed(self):
        for status in (200, 204, 301, 302, 307, 308):
            with self.subTest(status=status):
                self.assertEqual(
                    probe.classify(status).status,
                    "ANONYMOUS_ACCESS_OR_REDIRECT_SECURITY_FAILURE",
                )
        for status in (403, 404, 429, 500, 503, None):
            with self.subTest(status=status):
                self.assertNotEqual(
                    probe.classify(status).status,
                    "ANONYMOUS_ACCESS_OR_REDIRECT_SECURITY_FAILURE",
                )

    def test_redirect_handler_refuses_following_remote_login_redirect(self):
        self.assertIsNone(
            probe.NoRedirect().redirect_request(
                object(), None, 302, "Redirect", {},
                "https://other.example.com/steal",
            )
        )

    def test_network_error_is_not_reported_as_route_failure_or_deployment_success(self):
        opener = FakeOpener(URLError("fake network failure"))
        result = probe.probe(opener)
        self.assertEqual(result.status, "NETWORK_OR_SERVICE_UNAVAILABLE")
        self.assertIsNone(result.http_status)

    def test_safe_summary_reports_truthful_status_with_no_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            summary = os.path.join(temp, "summary.md")
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": summary}):
                with patch.object(probe, "probe", return_value=probe.classify(404)):
                    with patch("sys.stdout", new=io.StringIO()) as console:
                        self.assertEqual(probe.main(), 0)
                        emitted = console.getvalue()
            self.assertIn("ROUTE_NOT_FOUND_POSSIBLY_NOT_DEPLOYED", emitted)
            self.assertIn("Authenticated backend contract/commit verified: **NO**", open(summary).read())
            self.assertNotIn("Authorization", emitted)
            self.assertNotIn("Bearer ", emitted)

    def test_anonymous_success_and_redirect_produce_error_exit(self):
        for status in (200, 302):
            with self.subTest(status=status):
                with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}):
                    with patch.object(probe, "probe", return_value=probe.classify(status)):
                        with patch("sys.stdout", new=io.StringIO()):
                            self.assertEqual(probe.main(), 1)
