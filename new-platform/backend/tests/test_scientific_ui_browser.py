"""Chromium UI acceptance: real browser, mocked local API, no live credentials/trials.

Browser verifies controls, authorization feedback, responsive layouts and
evidence-gated scientific rendering. Live service HTTP E2E is tested separately.
"""
from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest

# The dedicated Chromium workflow installs Playwright. Generic backend/recovery
# test jobs intentionally do not, so browser-only tests skip collection there.
sync_playwright = pytest.importorskip(
    "playwright.sync_api", reason="Run in the scientific Chromium acceptance workflow"
).sync_playwright

from app.scientific_assessment import assess
from app.scientific_batch_ui import render_batch_panel

NCT = "NCT04280705"
SECRET = "test-browser-key"
JOB_ID = "c" * 32
DOMAINS = ("Trial design", "Efficacy", "Safety", "Biology", "Reliability", "Regulatory")


class TestServer(BaseHTTPRequestHandler):
    jobs = []
    history_requests = 0
    post_requests = 0
    science_requests = 0
    stale = False

    def log_message(self, *args):
        return

    def reply(self, status: int, body: dict | str, content_type="application/json"):
        encoded = (json.dumps(body).encode("utf-8") if isinstance(body, dict)
                   else body.encode("utf-8"))
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def authorized(self):
        if self.headers.get("x-pdufa-internal-key") != SECRET:
            self.reply(401, {"detail": "Unauthorized"})
            return False
        return True

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/scientific-assessment/batches":
            self.reply(200, render_batch_panel().body.decode(), "text/html; charset=utf-8")
            return
        if not self.authorized():
            return
        if parsed.path == "/api/scientific-assessment/batches-recovery-status":
            self.reply(200, {"potentially_interrupted": type(self).stale,
                             "manual_review_required": type(self).stale})
        elif parsed.path == "/api/scientific-assessment/batches":
            type(self).history_requests += 1
            self.reply(200, {"jobs": type(self).jobs})
        elif parsed.path == "/api/scientific-assessment/batches/" + JOB_ID:
            self.reply(200, type(self).jobs[0] if type(self).jobs else {})
        elif parsed.path == "/api/scientific-assessment":
            type(self).science_requests += 1
            exact = parse_qs(parsed.query).get("exact_id", [""])[0]
            record_found = exact == "TRIAL|" + NCT
            evidence = {
                "nctId": NCT, "verificationStatus": "source_record_only",
                "metadata": {
                    "overallStatus": "COMPLETED",
                    "enrollment": 1062,
                    "primaryOutcomes": [{"measure": "Primary endpoint"}],
                },
            } if record_found else None
            self.reply(200, {
                "exactId": exact,
                "registryEvidence": evidence,
                "registryEvidenceStatus": "source_record_loaded" if record_found else "record_not_found",
                "assessment": assess({}),
            })
        else:
            self.reply(404, {"error": "not_found"})

    def do_POST(self):
        if not self.authorized():
            return
        if urlsplit(self.path).path != "/api/scientific-assessment/batches":
            self.reply(404, {"error": "not_found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(min(length, 4096)))
        type(self).post_requests += 1
        job = {
            "id": JOB_ID, "status": "completed", "nct_ids": payload["nct_ids"],
            "total": 1, "processed": 1, "imported": 0,
            "already_exists": 1, "failed": 0,
            "created_at": "2026-10-25T00:00:00+00:00",
            "events": [{"index": 1, "nct_id": NCT, "status": "already_exists"}],
        }
        type(self).jobs = [job]
        self.reply(202, job)


@contextmanager
def local_server():
    TestServer.jobs = []
    TestServer.history_requests = 0
    TestServer.post_requests = 0
    TestServer.science_requests = 0
    TestServer.stale = False
    server = ThreadingHTTPServer(("127.0.0.1", 0), TestServer)
    runner = threading.Thread(target=server.serve_forever, daemon=True)
    runner.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        runner.join(timeout=5)
        server.server_close()


def test_chromium_scientific_batch_and_evidence_display():
    with local_server() as base_url, sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        try:
            page.goto(base_url + "/scientific-assessment/batches")
            page.get_by_role("heading", name="Scientific Assessment — Batch Imports").wait_for()
            page.get_by_role("heading", name="Scientific evidence assessment").wait_for()
            page.get_by_label("Internal API key").fill(SECRET)
            page.get_by_role("button", name="Refresh history").click()
            page.get_by_text("No batches submitted yet.").wait_for()
            assert TestServer.history_requests >= 1

            # Invalid IDs never reach the API or create a job.
            page.get_by_label("Clinical trial identifiers").fill("NOT_AN_NCT")
            page.get_by_role("button", name="Start batch import").click()
            page.get_by_text("Enter 1–25 distinct exact NCT identifiers", exact=False).wait_for()
            assert TestServer.post_requests == 0

            page.get_by_label("Clinical trial identifiers").fill(NCT)
            page.get_by_role("button", name="Start batch import").click()
            # The UI may update its notice to "History updated" immediately.
            page.get_by_text("1 / 1", exact=True).wait_for()
            page.get_by_text("already_exists", exact=False).wait_for()
            assert TestServer.post_requests == 1

            page.get_by_label("Exact ClinicalTrials.gov trial ID").fill("invalid")
            page.get_by_role("button", name="Inspect scientific evidence").click()
            page.get_by_text("Enter an exact NCT identifier", exact=False).wait_for()
            assert TestServer.science_requests == 0

            page.get_by_label("Exact ClinicalTrials.gov trial ID").fill(NCT)
            page.get_by_role("button", name="Inspect scientific evidence").click()
            page.get_by_text("archived source record, descriptive only", exact=False).wait_for()
            page.get_by_text("Overall scientific score: Not scored", exact=False).wait_for()
            page.get_by_text("Enrollment: 1062", exact=False).wait_for()
            for label in DOMAINS:
                assert page.get_by_text(label, exact=True).count() == 1
            assert page.locator("#science-domains .science-domain").count() == 6
            assert page.locator("#science-domains").get_by_text("Not scored", exact=True).count() == 6
            assert page.get_by_role("link", name="View source record on ClinicalTrials.gov").get_attribute("href") == (
                "https://clinicaltrials.gov/study/" + NCT
            )
            assert TestServer.science_requests == 1

            # Neither address bar nor browser storage may contain the secret.
            assert SECRET not in page.url
            assert page.evaluate("Object.keys(localStorage).length") == 0
            assert page.evaluate("Object.keys(sessionStorage).length") == 0
            assert SECRET not in page.content()

            page.get_by_role("button", name="Clear key").click()
            assert page.get_by_label("Internal API key").input_value() == ""
            assert page.locator("#science-domains .science-domain").count() == 0
            page.get_by_role("button", name="Refresh history").click()
            page.get_by_text("Enter the internal API key first.").wait_for()

            # Mobile viewport: domain cards stack and the page must not overflow.
            page.set_viewport_size({"width": 375, "height": 812})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
        finally:
            browser.close()


def test_chromium_warns_about_stale_job_without_unlock_control():
    with local_server() as base_url, sync_playwright() as p:
        TestServer.stale = True
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(base_url + "/scientific-assessment/batches")
            page.get_by_label("Internal API key").fill(SECRET)
            page.get_by_role("button", name="Refresh history").click()
            page.get_by_text("unfinished batch has not updated for over 60 minutes", exact=False).wait_for()
            assert page.get_by_role("button", name="Unlock batch").count() == 0
            assert TestServer.post_requests == 0
        finally:
            browser.close()
