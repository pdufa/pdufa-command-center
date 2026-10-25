"""Chromium acceptance of a distinct Google reviewer portal (simulated login).

No real Google credential, clinical claim, user account, reviewer provision, or
scientific score is created. Browser tests verify front-end policy only.
"""
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

import pytest

playwright=pytest.importorskip("playwright.sync_api").sync_playwright
from app.scientific_reviewer_ui import reviewer_html

TOKEN="stubbed-reviewer-google-token"
GOOGLE_JS=r"""
window.google={accounts:{id:{
  initialize:function(o){window.__googleTestCallback=o.callback;},
  renderButton:function(target){
    var b=document.createElement("button");
    b.textContent="Simulated reviewer Google login";
    b.id="google-test-login";
    b.addEventListener("click",function(){
      window.__googleTestCallback({credential:"stubbed-reviewer-google-token"});
    });
    target.appendChild(b);
  },
  disableAutoSelect:function(){}
}}};
"""


class Server(BaseHTTPRequestHandler):
    approved=False
    operator=False
    packet_calls=0
    document_calls=0
    submissions=[]

    def log_message(self,*_args): pass

    def json_response(self,status,data):
        payload=json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Cache-Control","private, no-store")
        self.send_header("Content-Length",str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path=="/scientific/reviewer":
            nonce="fake-nonce-123"
            html=reviewer_html("test-web-client.apps.googleusercontent.com",nonce).encode()
            self.send_response(200)
            self.send_header("Content-Type","text/html")
            self.send_header("Content-Length",str(len(html)))
            self.send_header("Content-Security-Policy",
                "default-src 'none';script-src 'nonce-"+nonce+
                "' https://accounts.google.com; style-src 'nonce-"+nonce+
                "';connect-src 'self' https://accounts.google.com;frame-src https://accounts.google.com")
            self.end_headers()
            self.wfile.write(html)
            return
        valid=self.headers.get("Authorization")=="Bearer "+TOKEN
        if not valid:
            self.json_response(401,{"detail":"Google token missing"});return
        if type(self).operator:
            self.json_response(403,{"detail":"Operator identity cannot review"});return
        if self.path=="/api/scientific-assessment/reviewer/onboarding-status":
            self.json_response(200,{
                "identityVerified":True,"separateGoogleIdentity":True,
                "roleAuthorized":type(self).approved,
                "credentialsVerified":type(self).approved,
                "maySignOff":False,
                "independentScientificAdjudicationImplemented":False,
                "selfRegistrationAvailable":False,
            });return
        if not type(self).approved:
            self.json_response(403,{"detail":"Reviewer not provisioned"});return
        if self.path=="/api/scientific-assessment/reviewer/me":
            self.json_response(200,{"roleAuthorized":True,
                                    "credentialsVerified":True,"maySignOff":False});return
        if self.path=="/api/scientific-assessment/reviewer/packet/NCT02142738":
            type(self).packet_calls+=1
            self.json_response(200,{
                "nctId":"NCT02142738","scientificallyVerified":False,
                "readyForFullScientificConclusion":False,
                "fdaApprovalProbability":None,"tradingEnabled":False,
                "reconciliation":{"unresolvedCount":8,"independentlyResolvedCount":0,
                "checks":[
                    {
                        "id":"protocol_amendment_chronology",
                        "title":"Protocol/SAP chronology",
                        "question":"Is January 2016 amendment prospectively locked?",
                        "resolved":False,"criteriaSatisfied":0,
                        "sourceUrls":["https://clinicaltrials.gov/study/NCT02142738"],
                        "resolutionCriteria":[
                          "Inspect signed original SAP",
                          "Verify alpha spend and analysis lock",
                        ],
                    }
                ]},
                "independentSourceLedger":{"capturedSourceDocuments":{
                    "sourceDocumentCount":1,
                    "documents":[{
                        "documentId":"a"*32,
                        "gateId":"protocol_sap",
                        "sourceType":"protocol_sap",
                        "sourceUrl":"https://clinicaltrials.gov/study/NCT02142738",
                        "sha256":"b"*64,"byteLength":195,
                        "documentContentScientificallyVerified":False,
                    }],
                }},
            });return
        self.json_response(404,{"detail":"Unknown request"})

    def do_POST(self):
        if self.path!="/api/scientific-assessment/reviewer/submissions":
            self.json_response(404,{"detail":"Unknown write"});return
        if not type(self).approved or type(self).operator:
            self.json_response(403,{"detail":"Not provisioned"});return
        if self.headers.get("Authorization")!="Bearer "+TOKEN:
            self.json_response(401,{"detail":"Google identity required"});return
        length=int(self.headers.get("Content-Length","0"))
        data=json.loads(self.rfile.read(length))
        if not data.get("uncertaintyDisclosed") or not data.get("sourceLocator"):
            self.json_response(422,{"detail":"Uncertainty required"});return
        type(self).submissions.append(data)
        self.json_response(201,{
            "auditRecorded":True,"adjudicated":False,
            "sourceContentIndependentlyVerified":False,
            "mayPromoteReadiness":False,"scientificScore":None,
        })


@contextmanager
def mock_portal(*,approved=False,operator=False):
    Server.approved=approved
    Server.operator=operator
    Server.packet_calls=0
    Server.document_calls=0
    Server.submissions=[]
    host=ThreadingHTTPServer(("127.0.0.1",0),Server)
    thread=threading.Thread(target=host.serve_forever,daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:"+str(host.server_port)
    finally:
        host.shutdown();host.server_close();thread.join(timeout=4)


def google_script(route):
    route.fulfill(status=200,content_type="application/javascript",body=GOOGLE_JS)


def test_unprovisioned_google_reviewer_cannot_open_scientific_dossier():
    with mock_portal(approved=False) as url,playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            page=browser.new_page()
            page.route("https://accounts.google.com/gsi/client",google_script)
            page.goto(url+"/scientific/reviewer")
            assert not page.locator("#review").is_visible()
            page.locator("#google-test-login").click()
            page.get_by_text("reviewer access has NOT been provisioned",exact=False).wait_for(timeout=10000)
            assert not page.locator("#review").is_visible()
            assert Server.packet_calls==0
            assert not Server.submissions
        finally:
            browser.close()


def test_operator_identity_is_not_independent_reviewer():
    with mock_portal(approved=True,operator=True) as url,playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            page=browser.new_page()
            page.route("https://accounts.google.com/gsi/client",google_script)
            page.goto(url+"/scientific/reviewer")
            page.locator("#google-test-login").click()
            page.get_by_text("Google reviewer identity is unapproved",exact=False).wait_for(timeout=10000)
            assert not page.locator("#review").is_visible()
            assert Server.packet_calls==0
            assert not Server.submissions
        finally:
            browser.close()


def test_approved_reviewer_reads_sources_and_records_only_uncertainty_disclosed_statement():
    with mock_portal(approved=True) as url,playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={"width":1200,"height":900})
            page.route("https://accounts.google.com/gsi/client",google_script)
            page.goto(url+"/scientific/reviewer")
            assert not page.locator("#review").is_visible()
            page.locator("#google-test-login").click()
            page.get_by_text("audited observations enabled",exact=False).wait_for(timeout=10000)
            page.get_by_text("1 evidence questions open",exact=False).wait_for(timeout=10000)
            assert page.locator("#questions details").count()==1
            assert page.locator("#documents button").count()==1
            assert Server.packet_calls==1
            assert page.locator("#source option").count()==1
            page.locator("#locator").fill("Page 29, Table 3")
            page.locator("#review-note").fill("The alpha-spending sequence remains unconfirmed against a signed SAP.")
            page.locator("#submit-observation").click()
            page.get_by_text("Acknowledge uncertainty",exact=False).wait_for(timeout=10000)
            assert not Server.submissions
            page.locator("#uncertainty").check()
            page.locator("#submit-observation").click()
            page.get_by_text("Audited source-review statement recorded",exact=False).wait_for(timeout=10000)
            assert len(Server.submissions)==1
            row=Server.submissions[0]
            assert row["nctId"]=="NCT02142738"
            assert row["sourceSha256"]=="b"*64
            assert row["questionId"]=="protocol_amendment_chronology"
            assert row["decision"]=="requires_review"
            assert row["uncertaintyDisclosed"] is True
            assert not page.get_by_text("scientific adjudication complete",exact=True).count()
        finally:
            browser.close()
