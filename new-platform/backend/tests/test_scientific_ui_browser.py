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
from app.scientific_investigation_20 import investigation_20
from app.scientific_quantitative_results import reported_quantitative_results
from app.scientific_readiness_grades import review_readiness
from app.scientific_reconciliation_worklist import reconciliation_worklist
from app.scientific_adjudication_preflight import adjudication_preflight
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
    packet_requests = 0
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
        elif parsed.path == "/api/scientific-assessment/review-packet/" + NCT:
            type(self).packet_requests += 1
            self.reply(200, {
                "packetSchemaVersion": "scientific-source-review-packet-v1",
                "nctId": NCT,
                "archive": {"nctId": NCT, "archiveIdentityAndSha256Verified": True},
                "investigation20": {"levelCount": 20},
                "reconciliation": {"unresolvedCount": 4,
                                   "independentlyResolvedCount": 0},
                "readyForFullScientificConclusion": False,
                "scientificConclusion": None,
                "fdaApprovalProbability": None,
                "packetIntegrity": {"algorithm": "SHA-256", "digest": "a"*64},
            })
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
                "investigation20": (investigation_20(NCT, {
                    "protocolSection": {
                        "identificationModule": {"nctId": NCT, "briefTitle": "Pilot trial"},
                        "statusModule": {"overallStatus": "COMPLETED"},
                        "outcomesModule": {"primaryOutcomes": [{"measure": "Endpoint"}]},
                    }
                }) if record_found else None),
                "quantitativeResults": (reported_quantitative_results(NCT, {
                    "protocolSection": {"identificationModule": {"nctId": NCT}},
                    "hasResults": True,
                    "resultsSection": {
                        "outcomeMeasuresModule": {"outcomeMeasures": [{
                            "type": "PRIMARY", "title": "Time to Recovery",
                            "paramType": "MEDIAN", "unitOfMeasure": "Days",
                            "groups": [{"id": "OG000", "title": "Placebo"},
                                       {"id": "OG001", "title": "Treatment"}],
                            "analyses": [{"groupIds": ["OG000", "OG001"],
                                          "statisticalMethod": "Log Rank",
                                          "paramType": "Cox Proportional Hazard",
                                          "paramValue": "1.29", "pValue": "<0.001",
                                          "ciPctValue": "95", "ciNumSides": "TWO_SIDED",
                                          "ciLowerLimit": "1.12", "ciUpperLimit": "1.48"}]
                        }]},
                        "adverseEventsModule": {"eventGroups": [{"id":"EG000"}],
                            "seriousEvents": [{"term": "Example serious event",
                                "stats": [{"groupId": "EG000", "numAffected": "3",
                                           "numAtRisk": "100"}]}]}
                    }
                }) if record_found else None),
                "readinessGrades": (review_readiness(NCT, {
                    "protocolSection": {
                        "identificationModule": {"nctId": NCT, "briefTitle": "Pilot trial"},
                        "designModule": {"studyType": "INTERVENTIONAL",
                                         "phases": ["PHASE3"]},
                    }
                }) if record_found else None),
                "evidenceLedgerStatus": "candidate_inventory_loaded" if record_found else "not_available",
                "evidenceLedger": ({
                    "candidateCount": 1, "entryCount": 1, "verifiedGateCount": 0,
                    "sourceReconciliation": reconciliation_worklist(NCT),
                    "adjudicationPreflight": adjudication_preflight(
                        NCT, reconciliation_worklist(NCT), {
                            "nctId": NCT, "totalStatements": 2,
                            "truncated": False, "statements": [
                                {"nctId": NCT, "questionId": "external_protocol_sap",
                                 "threadId": "thread-a", "revision": 1,
                                 "findingType": "supports",
                                 "sourceUrl": "https://clinicaltrials.gov/study/" + NCT,
                                 "reviewerLabel": "Test reviewer A",
                                 "independentlyVerified": False},
                                {"nctId": NCT, "questionId": "external_protocol_sap",
                                 "threadId": "thread-b", "revision": 1,
                                 "findingType": "contradicts",
                                 "sourceUrl": "https://clinicaltrials.gov/study/" + NCT,
                                 "reviewerLabel": "Test reviewer B",
                                 "independentlyVerified": False},
                            ],
                        },
                    ),
                    "reviewerFindings": {
                        "totalStatements": 2,
                        "questionsWithConflictingStatements": 1,
                        "independentConfirmationImplemented": False,
                        "statements": [
                            {
                                "questionId": "external_protocol_sap",
                                "findingType": "supports", "revision": 1,
                                "sourceUrl": "https://clinicaltrials.gov/study/" + NCT,
                                "sourceLocator": "Protocol page 5, section 2",
                                "assertion": "A registry field seems to support the stated eligibility criterion.",
                                "uncertainty": "The prospectively locked version has not been independently checked.",
                                "reviewerLabel": "Test reviewer A",
                                "reviewedAt": "2026-10-25T03:00:00+00:00",
                                "contentSha256": "a"*64
                            },
                            {
                                "questionId": "external_protocol_sap",
                                "findingType": "contradicts", "revision": 1,
                                "sourceUrl": "https://clinicaltrials.gov/study/" + NCT,
                                "sourceLocator": "Protocol page 8, section 4",
                                "assertion": "A different version may contain an eligibility change.",
                                "uncertainty": "We cannot reconcile the original protocol amendments yet.",
                                "reviewerLabel": "Test reviewer B",
                                "reviewedAt": "2026-10-25T03:01:00+00:00",
                                "contentSha256": "b"*64
                            },
                        ],
                    },
                    "externalGateStatuses": [
                        {"gateId": "published_results", "label": "Published results independently reviewed",
                         "independentlyVerified": False}
                    ],
                    "identifiedSourceCandidates": [
                        {"gateId": "published_results",
                         "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/27718847/",
                         "sourceType": "peer_reviewed_publication",
                         "title": "KEYNOTE-024 original published analysis",
                         "reviewStatus": "citation_identified_not_adjudicated",
                         "caution": "Protocol and statistical plan independently reviewed: NO"}
                    ],
                    "entries": [
                        {"id":"a"*32,"revision":2,"gateId":"published_results",
                         "sourceUrl":"https://pubmed.ncbi.nlm.nih.gov/27718847/",
                         "sourceType":"peer_reviewed_publication",
                         "relationship":"contradicts",
                         "reviewStatus":"pending_independent_review",
                         "recordedBy":"Review curator",
                         "recordedAt":"2026-10-25T02:02:00+00:00",
                         "claimText":"Unresolved discrepancy between trial follow-up analyses.",
                         "caution":"Check protocol and censoring differences.",
                         "contentSha256":"a"*64}
                    ],
                } if record_found else None),
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
    TestServer.packet_requests = 0
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
            # Review packet download is a deliberate authenticated action.
            # Secret remains request-header only, not in the exported JSON.
            with page.expect_download() as download_event:
                page.get_by_role("button", name="Download 20-stage review packet (JSON)").click()
            download=download_event.value
            assert download.suggested_filename == NCT+"_scientific_review_packet.json"
            with open(download.path(),encoding="utf-8") as exported:
                packet=json.load(exported)
            assert packet["nctId"]==NCT
            assert packet["investigation20"]["levelCount"]==20
            assert packet["reconciliation"]["independentlyResolvedCount"]==0
            assert packet["scientificConclusion"] is None
            assert SECRET not in json.dumps(packet)
            assert TestServer.packet_requests==1

            # Depth-20 source coverage is genuinely rendered by the browser,
            # with no invented score or FDA approval probability.
            page.get_by_role("heading", name="20-stage scientific investigation · source-coverage map").wait_for()
            assert page.locator("#investigation-20 details").count() == 20
            page.get_by_text("Scientifically verified: 0/20.", exact=False).wait_for()
            first_level = page.locator("#investigation-20 details").first
            first_level.locator("summary").click()
            first_level.get_by_text("protocolSection.identificationModule.briefTitle").wait_for()
            assert page.locator("#investigation-20").get_by_text(
                "FDA approval probability: Not calculated.", exact=False).count() == 1

            # Reported numbers are visible without converting the p-value
            # into a statistical success or approval probability.
            page.get_by_role("heading", name="Reported outcomes and safety — not independently verified").wait_for()
            assert page.locator("#quantitative-results details").count() == 2
            outcome = page.locator("#quantitative-results details").first
            outcome.locator("summary").click()
            outcome.get_by_text("Reported p-value: <0.001", exact=False).wait_for()
            outcome.get_by_text("1.12 to 1.48", exact=False).wait_for()
            page.get_by_text("No statistical-success grade", exact=False).wait_for()
            adverse = page.locator("#quantitative-results details").last
            adverse.locator("summary").click()
            adverse.get_by_text("Affected: 3 · At risk: 100", exact=False).wait_for()

            # Both evidence grades are displayed without claiming trial failure.
            page.get_by_role("heading", name="Two evidence grades — readiness and reluctance").wait_for()
            page.get_by_text("Full scientific conclusion: NOT READY", exact=False).wait_for()
            page.get_by_text("F · CRITICAL", exact=True).wait_for()
            page.get_by_text("It does NOT mean the clinical trial failed.", exact=False).wait_for()
            gates = page.locator("#readiness-grades details")
            assert gates.count() == 1
            gates.locator("summary").click()
            assert page.locator("#readiness-grades li").count() == 16
            gates.get_by_text("Original protocol and statistical analysis plan independently reconciled", exact=False).wait_for()

            page.get_by_role("heading", name="Independent source evidence ledger").wait_for()
            page.get_by_text("0/4 independently verified gates", exact=False).wait_for()
            candidate = page.locator("#evidence-ledger details").nth(1)
            candidate.locator("summary").click()
            assert candidate.get_by_role("link", name="KEYNOTE-024 original published analysis").get_attribute("href") == (
                "https://pubmed.ncbi.nlm.nih.gov/27718847/"
            )
            candidate.get_by_text("citation_identified_not_adjudicated", exact=False).wait_for()
            reconciler=page.locator("#evidence-ledger details").nth(2)
            reconciler.locator("summary").click()
            # This fixture inspects NCT04280705, not KEYNOTE-024.
            # Unresearched studies correctly receive four generic open gates.
            assert reconciler.locator(".reconciliation-questions li").count()==4
            reconciler.get_by_text("Original protocol and statistical analysis plan independently reconciled",exact=False).wait_for()
            assert reconciler.get_by_role("link",name="View source").count()==0
            trail=page.locator("#evidence-ledger details").nth(3)
            trail.locator("summary").click()
            trail.get_by_text("Version 2 · contradicts", exact=False).wait_for()
            trail.get_by_text("Unresolved discrepancy between trial follow-up analyses.").wait_for()
            statements=page.locator("#evidence-ledger details").nth(4)
            statements.locator("summary").click()
            assert "1 questions disputed" in statements.locator("summary").inner_text()
            assert statements.locator(".reviewer-statements li").count()==2
            statements.get_by_text("not independently confirmed",exact=False).first.wait_for()
            statements.get_by_text("Claim: A different version may contain an eligibility change.").wait_for()
            assert page.get_by_role("button",name="Approve evidence").count()==0
            blocker_report=page.locator("#evidence-ledger .adjudication-preflight")
            assert blocker_report.count()==1
            assert "0/4 questions ready" in blocker_report.locator("summary").inner_text()
            blocker_report.locator("summary").click()
            blocker_report.get_by_text(
                "Reviewer identities and qualifications have not been authenticated."
            ).wait_for()
            blocker_report.get_by_text(
                "Independent review and a signed second-person decision are not implemented."
            ).wait_for()
            blocker_report.get_by_text(
                "0 independently resolved.",exact=False
            ).wait_for()
            assert blocker_report.locator("li").count()>=8

            assert page.get_by_role("button", name="Mark verified").count() == 0

            # Neither address bar nor browser storage may contain the secret.
            assert SECRET not in page.url
            assert page.evaluate("Object.keys(localStorage).length") == 0
            assert page.evaluate("Object.keys(sessionStorage).length") == 0
            assert SECRET not in page.content()

            page.get_by_role("button", name="Clear key").click()
            assert page.get_by_label("Internal API key").input_value() == ""
            assert page.locator("#science-domains .science-domain").count() == 0
            assert page.locator("#investigation-20 details").count() == 0
            assert page.locator("#quantitative-results details").count() == 0
            assert page.locator("#readiness-grades .readiness-grade").count() == 0
            assert page.locator("#evidence-ledger details").count() == 0
            assert page.get_by_role("button", name="Download 20-stage review packet (JSON)").is_disabled()
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
