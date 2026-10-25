"""Browser-level single-operator scientific review acceptance with stubbed Google.

This is a simulated browser interaction only. It never requests a real
Google token, credentials, OAuth consent, source verification or scoring.
"""
from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

playwright = pytest.importorskip("playwright.sync_api").sync_playwright

from app.scientific_operator_ui import operator_html


FAKE_TOKEN = "browser-only-fake-google-token-for-tests"
GOOGLE_STUB = r"""
window.google = {accounts: {id: {
  initialize: function(opts) { window.__testGoogleCallback = opts.callback; },
  renderButton: function(target) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = 'Mock Google sign-in';
    b.id = 'test-google-button';
    b.addEventListener('click', function () {
      window.__testGoogleCallback({credential: 'browser-only-fake-google-token-for-tests'});
    });
    target.appendChild(b);
  },
  disableAutoSelect: function() {}
}}};
"""


class Handler(BaseHTTPRequestHandler):
    accept_operator = True
    identity_calls = 0
    research_calls = 0

    def log_message(self, *_args):
        return

    def respond(self, status, data):
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/scientific/operator":
            nonce = "test-science-page-nonce"
            body = operator_html("1234567890-webtest.apps.googleusercontent.com", nonce).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", (
                "default-src 'none'; base-uri 'none'; form-action 'none'; "
                "frame-ancestors 'none'; object-src 'none'; "
                "script-src 'nonce-" + nonce +
                "' https://accounts.google.com https://ssl.gstatic.com; "
                "style-src 'nonce-" + nonce + "' https://accounts.google.com; "
                "connect-src 'self' https://accounts.google.com; "
                "frame-src https://accounts.google.com; "
                "img-src https://accounts.google.com https://ssl.gstatic.com data:"
            ))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/scientific-assessment/operator/me":
            type(self).identity_calls += 1
            if self.headers.get("Authorization") != "Bearer " + FAKE_TOKEN:
                self.respond(401, {"detail": "Invalid identity"})
            elif not type(self).accept_operator:
                self.respond(403, {"detail": "Google account not authorized"})
            else:
                self.respond(200, {"role": "operator", "identityVerified": True,
                                   "maySignOff": False, "mayPromoteScientificScore": False})
            return
        if self.path.startswith("/api/scientific-assessment/operator/research?"):
            type(self).research_calls += 1
            if self.headers.get("Authorization") != "Bearer " + FAKE_TOKEN:
                self.respond(401, {"detail": "Not signed in"})
                return
            if not type(self).accept_operator:
                self.respond(403, {"detail": "Not authorized"})
                return
            self.respond(200, {
                "registryEvidenceStatus": "source_record_loaded",
                "investigation20": {
                    "levels": [
                        {"level": i, "title": "Stage " + str(i),
                         "status": "external_review_required",
                         "caution": "Independent verification still pending."}
                        for i in range(1, 21)
                    ],
                },
                "investigation40": {
                    "layers": [
                        {"id": "layer_" + str(i),
                         "assessments": ["assessment_" + str(j) for j in range(1, 6)]}
                        for i in range(1, 9)
                    ],
                    "verification": {"verified_assessments": 0},
                },
                "readinessGrades": {
                    "analysisReadiness": {"grade": "C"},
                    "scientificReluctance": {"grade": "F"},
                },
                "assessment": {"overall_score": None},
            })
            return
        if self.path == "/health":
            self.respond(200, {"ok": True})
            return
        self.respond(404, {"detail": "Not found"})


@contextmanager
def stub_service(*, accepted=True):
    Handler.accept_operator = accepted
    Handler.identity_calls = 0
    Handler.research_calls = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def mock_google_script(route):
    route.fulfill(status=200, content_type="application/javascript", body=GOOGLE_STUB)


def test_browser_single_operator_loads_twenty_stages_and_forty_unscored_assessments():
    with stub_service(accepted=True) as url, playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.route("https://accounts.google.com/gsi/client", mock_google_script)
            page.goto(url + "/scientific/operator")
            page.locator("#test-google-button").wait_for(timeout=10000)
            assert not page.locator("#research").is_visible()
            assert Handler.identity_calls == 0
            page.locator("#test-google-button").click()
            page.get_by_text("Signed in as the configured operator.", exact=False).wait_for(timeout=10000)
            assert page.locator("#research").is_visible()
            assert Handler.identity_calls == 1
            page.locator("#load").click()
            page.get_by_text("Read-only source inventory loaded.", exact=False).wait_for(timeout=10000)
            assert Handler.research_calls == 1
            assert page.locator("#levels details").count() == 20
            assert page.locator("#layers details").count() == 8
            assert page.get_by_text("0 / 40").count() == 1
            assert page.get_by_text("Not assigned").count() == 1
            assert page.get_by_text("C", exact=True).count() >= 1
            assert page.get_by_text("F", exact=True).count() >= 1
            page.locator("#signout").click()
            assert not page.locator("#research").is_visible()
            assert page.get_by_text("Signed out. Google identity tokens are not stored.").is_visible()
            assert page.evaluate("Object.keys(localStorage).length") == 0
            assert page.evaluate("Object.keys(sessionStorage).length") == 0
        finally:
            browser.close()


def test_browser_rejects_wrong_google_operator_without_exposing_research():
    with stub_service(accepted=False) as url, playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.route("https://accounts.google.com/gsi/client", mock_google_script)
            page.goto(url + "/scientific/operator")
            page.locator("#test-google-button").wait_for(timeout=10000)
            page.locator("#test-google-button").click()
            page.get_by_text("Account not authorized or Google session expired (403)", exact=False).wait_for(timeout=10000)
            assert not page.locator("#research").is_visible()
            assert Handler.identity_calls == 1
            assert Handler.research_calls == 0
        finally:
            browser.close()
