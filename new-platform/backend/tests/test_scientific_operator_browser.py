"""Browser-level single-operator scientific review acceptance with stubbed Google.

This is a simulated browser interaction only. It never requests a real
Google token, credentials, OAuth consent, source verification or scoring.
"""
from __future__ import annotations

import base64
import hashlib
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
    worksheet_calls = 0
    pdf_enabled = False
    remote_pdf_enabled = False
    archive_calls = 0
    remote_fetch_calls = 0
    pdf_bytes = None

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
                                   "maySignOff": False, "mayPromoteScientificScore": False,
                                   "mayArchiveSourcePdf": type(self).pdf_enabled,
                                   "mayFetchOfficialPdf": type(self).remote_pdf_enabled})
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
                "evidenceLedger": {
                    "sourceReconciliation": {
                        "totalChecks": 8, "unresolvedChecks": 8, "verifiedChecks": 0,
                        "checks": [
                            {
                                "id": "test_question_" + str(i), "gateId": "protocol_sap",
                                "title": "Source reconciliation question " + str(i),
                                "priority": "critical", "status": "open_unadjudicated",
                                "independentlyVerified": False,
                                "question": "Reconcile original dated documents",
                                "observedDiscrepancy": "Source version needs validation" if i == 1 else None,
                                "nextAction": "Inspect original source and independent methods",
                                "sourceUrls": (["https://clinicaltrials.gov/study/NCT02142738"]
                                               if i < 8 else ["javascript:alert(1)"]),
                            }
                            for i in range(1, 9)
                        ],
                    },
                    "capturedSourceDocuments": {
                        "sourceDocumentCount": 1 if type(self).pdf_bytes is not None else 0,
                        "documents": [{
                            "documentId": "a"*32, "gateId": "protocol_sap",
                            "byteLength": len(type(self).pdf_bytes),
                            "sha256": hashlib.sha256(type(self).pdf_bytes).hexdigest(),
                            "documentContentScientificallyVerified": False,
                        }] if type(self).pdf_bytes is not None else [],
                    },
                    "verifiedGateCount": 0,
                },
                "assessment": {"overall_score": None},
            })
            return
        if self.path == "/api/scientific-assessment/operator/source-comparison/NCT02142738":
            if self.headers.get("Authorization") != "Bearer " + FAKE_TOKEN or (
                not type(self).accept_operator
            ):
                self.respond(403, {"detail": "Google operator required"})
                return
            self.respond(200, {
                "schemaVersion": "historical-pilot-preliminary-evidence-comparison-v1",
                "scientificallyVerified": False,
                "verifiedIndependentGates": 0,
                "independentlyResolvedCount": 0,
                "unresolvedCount": 8,
                "mayAssignScientificScore": False,
                "checkCount": 8,
                "archivedPdfCount": 2 if type(self).pdf_bytes is not None else 0,
                "sources": {
                    "official": {
                        "url": "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2016/125514Orig1s008,125514Orig1s012ltr.pdf",
                        "label": "Original FDA S-12 approval letter",
                        "locator": "FDA page 1 and signature page 6",
                    },
                    "protocol": {
                        "url": "https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf",
                        "label": "Japan-only December 2017 amendment",
                        "locator": "Cover and page 1",
                    },
                },
                "checks": [
                    {
                        "title": "Preliminary finding "+str(i),
                        "risk": "critical",
                        "preliminaryObservation": ("2017 Japan-only amendment does not validate a 2016 SAP"
                                                   if i == 1 else "Published observations remain preliminary"),
                        "stillMissing": "Independent historical source adjudication",
                        "sourceIds": ["official", "protocol"],
                        "independentlyResolved": False,
                        "evidenceGateApproved": False,
                    }
                    for i in range(1, 9)
                ],
            })
            return
        if self.path == "/api/scientific-assessment/operator/worksheet/NCT02142738":
            type(self).worksheet_calls += 1
            if self.headers.get("Authorization") != "Bearer " + FAKE_TOKEN:
                self.respond(401, {"detail": "Not signed in"})
                return
            self.respond(200, {
                "nctId": "NCT02142738", "scientificallyVerified": False,
                "readyForFullScientificConclusion": False,
                "scientificConclusion": None,
                "packetIntegrity": {"algorithm": "SHA-256", "digest": "a"*64},
                "reconciliation": {
                    "unresolvedCount": 8, "independentlyResolvedCount": 0,
                    "checks": [
                        {"title": "Source reconciliation question " + str(i),
                         "resolutionCriteria": [
                             "Check dated original protocol",
                             "Reconcile endpoint and analysis population",
                             "Document conflicting estimates",
                             "Obtain independent signoff",
                         ], "resolved": False}
                        for i in range(1, 9)
                    ],
                },
            })
            return
        if self.path == "/api/scientific-assessment/operator/source-documents/NCT02142738/" + "a"*32:
            if self.headers.get("Authorization") != "Bearer " + FAKE_TOKEN:
                self.respond(401, {"detail": "Unauthorized"})
                return
            if type(self).pdf_bytes is None:
                self.respond(404, {"detail": "Unknown document"})
                return
            raw = type(self).pdf_bytes
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "private, no-store")
            self.send_header("Content-Disposition", 'attachment; filename="NCT02142738_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.pdf"')
            self.send_header("X-Source-Document-SHA256", hashlib.sha256(raw).hexdigest())
            self.end_headers()
            self.wfile.write(raw)
            return
        if self.path == "/health":
            self.respond(200, {"ok": True})
            return
        self.respond(404, {"detail": "Not found"})


    def do_POST(self):
        if self.path == "/api/scientific-assessment/operator/source-documents/NCT02142738/fetch/protocol":
            type(self).remote_fetch_calls += 1
            if (self.headers.get("Authorization") != "Bearer " + FAKE_TOKEN
                    or not type(self).accept_operator or not type(self).remote_pdf_enabled):
                self.respond(403, {"detail": "Not allowed"})
                return
            raw = b"%PDF-1.7\n1 0 obj<</Type/Catalog>>endobj\nOfficial pinned test PDF\n%%EOF\n"
            type(self).pdf_bytes = raw
            self.respond(200, {
                "documentId": "a"*32, "nctId": "NCT02142738",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "byteIntegrityChecked": True, "byteLength": len(raw),
                "alreadyArchived": False, "scientificallyVerified": False,
                "independentReviewRequired": True,
                "documentContentScientificallyVerified": False,
            })
            return
        if self.path != "/api/scientific-assessment/operator/source-documents/NCT02142738":
            self.respond(404, {"detail": "Not found"})
            return
        type(self).archive_calls += 1
        if not type(self).accept_operator or not type(self).pdf_enabled or (
            self.headers.get("Authorization") != "Bearer " + FAKE_TOKEN
        ):
            self.respond(403, {"detail": "Unauthorized"})
            return
        size = int(self.headers.get("Content-Length", "0"))
        if size <= 0 or size > 5_800_000:
            self.respond(413, {"detail": "Invalid PDF upload"})
            return
        data = json.loads(self.rfile.read(size))
        raw = base64.b64decode(data["contentBase64"], validate=True)
        digest = hashlib.sha256(raw).hexdigest()
        if data["gateId"] != "protocol_sap" or data["sha256"] != digest or (
            not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-1024:]
        ):
            self.respond(422, {"detail": "PDF bytes failed validation"})
            return
        type(self).pdf_bytes = raw
        self.respond(201, {
            "documentId": "a"*32, "nctId": "NCT02142738",
            "sha256": digest, "byteLength": len(raw),
            "byteIntegrityChecked": True,
            "documentContentScientificallyVerified": False,
            "canCountTowardReadiness": False,
        })


@contextmanager
def stub_service(*, accepted=True, pdf_enabled=False, remote_pdf_enabled=False):
    Handler.accept_operator = accepted
    Handler.identity_calls = 0
    Handler.research_calls = 0
    Handler.worksheet_calls = 0
    Handler.pdf_enabled = pdf_enabled
    Handler.remote_pdf_enabled = remote_pdf_enabled
    Handler.archive_calls = 0
    Handler.remote_fetch_calls = 0
    Handler.pdf_bytes = None
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
            # The exact archived pilot loads automatically after authorized sign-in.
            page.get_by_text("Read-only source inventory loaded.", exact=False).wait_for(timeout=10000)
            assert Handler.research_calls == 1
            assert page.locator("#levels details").count() == 20
            assert page.locator("#layers details").count() == 8
            assert page.locator("#evidence-questions details").count() == 8
            page.get_by_text("Preliminary evidence comparison ready: 8 questions still open", exact=False).wait_for(timeout=15000)
            assert page.locator("#source-comparison details").count() == 8
            page.locator("#source-comparison details").first.locator("summary").click()
            assert page.get_by_text("2017 Japan-only amendment does not validate a 2016 SAP").is_visible()
            assert page.locator("#source-comparison a").count() == 16
            assert page.locator("#source-comparison a[href^='javascript:']").count() == 0
            assert page.get_by_text("Source reconciliation question 1", exact=False).count() >= 1
            page.locator("#evidence-questions details").first.locator("summary").click()
            assert page.locator("#evidence-questions a[href='https://clinicaltrials.gov/study/NCT02142738']").count() == 7
            assert page.locator("#evidence-questions a[href^='javascript:']").count() == 0
            page.locator("#worksheet").click()
            page.get_by_text("8 review questions loaded.", exact=False).wait_for(timeout=10000)
            assert Handler.worksheet_calls == 1
            assert page.locator("#worksheet-criteria details").count() == 8
            assert page.locator("#worksheet-criteria details").first.locator("li").count() == 4
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



def test_browser_google_operator_archives_original_pdf_bytes_without_scientific_verification():
    raw = b"%PDF-1.7\n1 0 obj<</Type/Catalog>>endobj\nOriginal-source-test-bytes\n%%EOF\n"
    with stub_service(accepted=True, pdf_enabled=True) as url, playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 850}, accept_downloads=True)
            page.route("https://accounts.google.com/gsi/client", mock_google_script)
            page.goto(url + "/scientific/operator")
            page.locator("#test-google-button").wait_for(timeout=10000)
            assert not page.locator("#pdf-capture").is_visible()
            page.locator("#test-google-button").click()
            page.get_by_text("Read-only source inventory loaded.", exact=False).wait_for(timeout=10000)
            assert page.locator("#pdf-capture").is_visible()
            assert Handler.archive_calls == 0
            page.locator("#source-pdf-kind").select_option("protocol")
            page.locator("#source-pdf-file").set_input_files({
                "name": "Protocol.pdf", "mimeType": "application/pdf", "buffer": raw
            })
            page.locator("#archive-pdf").click()
            page.get_by_text("PDF saved with SHA-256 byte check.", exact=False).wait_for(timeout=10000)
            assert Handler.archive_calls == 1
            assert Handler.pdf_bytes == raw
            page.get_by_text("Read-only source inventory loaded.", exact=False).wait_for(timeout=10000)
            page.get_by_text("1", exact=True).first.wait_for(timeout=10000)
            assert page.locator("#captured-pdfs button").count() == 1
            with page.expect_download() as result:
                page.locator("#captured-pdfs button").click()
            download=result.value
            assert download.suggested_filename.endswith(".pdf")
            assert page.get_by_text("Scientific score", exact=True).is_visible()
            assert page.get_by_text("Not assigned", exact=True).is_visible()
            assert page.get_by_text("0 / 40", exact=True).is_visible()
        finally:
            browser.close()


def test_browser_pdf_capture_stays_hidden_for_unauthorized_operator():
    with stub_service(accepted=False, pdf_enabled=True) as url, playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            page=browser.new_page()
            page.route("https://accounts.google.com/gsi/client", mock_google_script)
            page.goto(url + "/scientific/operator")
            page.locator("#test-google-button").wait_for(timeout=10000)
            page.locator("#test-google-button").click()
            page.get_by_text("Account not authorized or Google session expired (403)", exact=False).wait_for(timeout=10000)
            assert not page.locator("#pdf-capture").is_visible()
            assert Handler.archive_calls == 0
        finally:
            browser.close()



def test_browser_fetches_official_pdf_without_local_upload_or_science_signoff():
    with stub_service(accepted=True, pdf_enabled=True, remote_pdf_enabled=True) as url, playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={"width": 1200, "height": 800})
            page.route("https://accounts.google.com/gsi/client", mock_google_script)
            page.goto(url + "/scientific/operator")
            page.locator("#test-google-button").wait_for(timeout=10000)
            assert not page.locator("#fetch-official-pdf").is_visible()
            page.locator("#test-google-button").click()
            page.get_by_text("Read-only source inventory loaded.", exact=False).wait_for(timeout=10000)
            assert page.locator("#fetch-official-pdf").is_visible()
            assert Handler.remote_fetch_calls == 0
            assert page.locator("#source-pdf-file").input_value() == ""
            page.locator("#source-pdf-kind").select_option("csr")
            assert "P024-03" in page.locator("#official-source-note").inner_text()
            assert page.locator("#source-pdf-link").get_attribute("href") == (
                "https://portal.dimdi.de/data/ctr/O-2145_01-2-0-CE336C-20220110151635.pdf")
            page.locator("#source-pdf-kind").select_option("protocol")
            assert "2017" in page.locator("#official-source-note").inner_text()
            page.locator("#fetch-official-pdf").click()
            page.get_by_text("Official PDF archived with its SHA-256 byte checksum.", exact=False).wait_for(timeout=10000)
            assert Handler.remote_fetch_calls == 1
            assert Handler.archive_calls == 0
            assert Handler.pdf_bytes.startswith(b"%PDF-")
            assert page.locator("#captured-pdfs button").count() == 1
            assert page.get_by_text("0 / 40", exact=True).is_visible()
            assert page.get_by_text("Not assigned", exact=True).is_visible()
        finally:
            browser.close()


def test_browser_hides_remote_fetch_when_explicitly_disabled():
    with stub_service(accepted=True, pdf_enabled=True, remote_pdf_enabled=False) as url, playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            page=browser.new_page()
            page.route("https://accounts.google.com/gsi/client", mock_google_script)
            page.goto(url + "/scientific/operator")
            page.locator("#test-google-button").wait_for(timeout=10000)
            page.locator("#test-google-button").click()
            page.get_by_text("Read-only source inventory loaded.", exact=False).wait_for(timeout=10000)
            assert page.locator("#pdf-capture").is_visible()
            assert not page.locator("#fetch-official-pdf").is_visible()
            assert Handler.remote_fetch_calls == 0
        finally:
            browser.close()
