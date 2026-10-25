"""Independent reviewer identity, access and source-boundary acceptance tests."""
import hashlib
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main, scientific_google_identity
from app.scientific_reviewer_accounts import reviewer_setup_summary

HEADERS={"Authorization":"Bearer simulated-google-token"}
NCT="NCT02142738"


@pytest.fixture
def env(monkeypatch):
    engine=create_engine("sqlite://",poolclass=StaticPool,connect_args={"check_same_thread":False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main,"ENGINE",engine)
    monkeypatch.setattr(main,"DATABASE_URL","postgresql+psycopg://fake/reviewer")
    monkeypatch.setattr(main,"_DB_STATE",{"available":True,"reason":"READY"})
    monkeypatch.setenv("RENDER_SERVICE_ID","srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID","test-google-client.apps.googleusercontent.com")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE","single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL","owner@example.org")
    monkeypatch.setattr(scientific_google_identity,"verified_google_identity",
                        lambda token: {"providerSubject":"reviewer-sub","verifiedEmail":"reviewer@example.org"})
    yield TestClient(main.app),engine
    engine.dispose()


def add_reviewer(engine,subject="reviewer-sub",email="reviewer@example.org",
                 role="reviewer",credentials_verified=True,enabled=True):
    with Session(engine) as session:
        session.add(main.ScientificReviewerAccount(
            google_subject=subject,verified_email=email,role=role,
            enabled=enabled,credentials_verified=credentials_verified,
            created_at=datetime(2026,10,25,tzinfo=timezone.utc)))
        session.commit()


def test_standalone_page_requires_isolated_service_and_has_secure_headers(env,monkeypatch):
    client,_=env
    res=client.get("/scientific/reviewer")
    assert res.status_code==200
    assert "Independent reviewer workspace" in res.text
    assert "/api/scientific-assessment/reviewer/onboarding-status" in res.text
    assert "/api/scientific-assessment/reviewer/submissions" in res.text
    assert "accounts.google.com/gsi/client" in res.text
    assert "owner@example.org" not in res.text
    assert res.headers["x-frame-options"]=="DENY"
    assert "no-store" in res.headers["cache-control"]
    assert "nonce-" in res.headers["content-security-policy"]
    monkeypatch.setenv("RENDER_SERVICE_ID","another-service")
    assert client.get("/scientific/reviewer").status_code==503


def test_unprovisioned_reviewer_can_only_check_status_not_read_private_documents(env):
    client,engine=env
    status=client.get("/api/scientific-assessment/reviewer/onboarding-status",headers=HEADERS)
    assert status.status_code==200
    payload=status.json()
    assert payload["identityVerified"] is True
    assert payload["registered"] is False
    assert payload["roleAuthorized"] is False
    assert payload["maySubmitAuditedStatements"] is False
    assert payload["maySignOff"] is False
    assert payload["selfRegistrationAvailable"] is False
    assert client.get("/api/scientific-assessment/reviewer/packet/"+NCT,headers=HEADERS).status_code==403
    assert client.get("/api/scientific-assessment/reviewer/source-documents/"+NCT+"/"+"a"*32,headers=HEADERS).status_code==403
    assert client.post("/api/scientific-assessment/reviewer/submissions",headers=HEADERS,json={}).status_code in (403,422)
    with Session(engine) as session:
        assert session.execute(select(main.ScientificReviewerAccount)).first() is None


def test_operator_cannot_become_independent_reviewer_even_when_allowlisted(env,monkeypatch):
    client,engine=env
    add_reviewer(engine,subject="owner-sub",email="OWNER@example.org")
    monkeypatch.setattr(scientific_google_identity,"verified_google_identity",
                        lambda token: {"providerSubject":"owner-sub","verifiedEmail":"OWNER@example.org"})
    assert client.get("/api/scientific-assessment/reviewer/onboarding-status",headers=HEADERS).status_code==403
    assert client.get("/api/scientific-assessment/reviewer/me",headers=HEADERS).status_code==403
    assert client.get("/api/scientific-assessment/reviewer/packet/"+NCT,headers=HEADERS).status_code==403
    assert client.get("/api/scientific-assessment/reviewer/source-documents/"+NCT+"/"+"a"*32,headers=HEADERS).status_code==403


def test_reviewer_email_mismatch_or_unverified_credentials_fail_closed(env,monkeypatch):
    client,engine=env
    add_reviewer(engine,email="reviewer@example.org",credentials_verified=False)
    r=client.get("/api/scientific-assessment/reviewer/onboarding-status",headers=HEADERS)
    assert r.status_code==200
    assert r.json()["registered"] is True
    assert r.json()["roleAuthorized"] is False
    assert client.get("/api/scientific-assessment/reviewer/me",headers=HEADERS).status_code==403
    with Session(engine) as session:
        row=session.get(main.ScientificReviewerAccount,"reviewer-sub")
        row.credentials_verified=True
        session.commit()
    monkeypatch.setattr(scientific_google_identity,"verified_google_identity",
                        lambda token: {"providerSubject":"reviewer-sub","verifiedEmail":"changed@example.org"})
    assert client.get("/api/scientific-assessment/reviewer/me",headers=HEADERS).status_code==403


def test_verified_reviewer_can_get_source_packet_but_not_promote_science(env,monkeypatch):
    from app import scientific_review_packet
    client,engine=env
    add_reviewer(engine)
    seen=[]
    def fake_packet(nct):
        seen.append(nct)
        return {"nctId":nct,"scientificallyVerified":False,
                "readyForFullScientificConclusion":False,
                "fdaApprovalProbability":None,
                "tradingEnabled":False,
                "reconciliation":{"unresolvedCount":8,"independentlyResolvedCount":0,
                  "checks":[{"id":"protocol_amendment_chronology","resolved":False,
                             "criteriaSatisfied":0,"resolutionCriteria":["Read the original SAP"]}]}}
    monkeypatch.setattr(scientific_review_packet,"build_review_packet",fake_packet)
    status=client.get("/api/scientific-assessment/reviewer/onboarding-status",headers=HEADERS)
    assert status.status_code==200 and status.json()["maySubmitAuditedStatements"] is True
    assert client.get("/api/scientific-assessment/reviewer/me",headers=HEADERS).json()["maySignOff"] is False
    packet=client.get("/api/scientific-assessment/reviewer/packet/"+NCT,headers=HEADERS)
    assert packet.status_code==200 and seen==[NCT]
    assert packet.json()["scientificallyVerified"] is False
    assert packet.json()["reconciliation"]["independentlyResolvedCount"]==0
    assert "no-store" in packet.headers["cache-control"]
    assert client.get("/api/scientific-assessment/reviewer/packet/INVALID",headers=HEADERS).status_code==422


def test_operator_reviewer_setup_only_aggregates_no_private_identities(env,monkeypatch):
    client,engine=env
    add_reviewer(engine,subject="reviewer-a",email="r1@example.org")
    add_reviewer(engine,subject="reviewer-b",email="r2@example.org",role="second_reviewer",
                 credentials_verified=False)
    monkeypatch.setattr(scientific_google_identity,"verified_google_identity",
                        lambda token: {"providerSubject":"owner-sub","verifiedEmail":"owner@example.org"})
    summary=client.get("/api/scientific-assessment/operator/reviewer-setup",headers=HEADERS)
    assert summary.status_code==200
    data=summary.json()
    assert data["totalProvisioningRecords"]==2
    assert data["activeCredentialVerifiedIdentities"]==1
    assert data["dualReviewIdentityCountMet"] is False
    assert data["maySignOff"] is False
    assert "reviewer-a" not in summary.text
    assert "r1@example.org" not in summary.text
    assert "no-store" in summary.headers["cache-control"]
    monkeypatch.setattr(scientific_google_identity,"verified_google_identity",
                        lambda token: {"providerSubject":"reviewer-a","verifiedEmail":"r1@example.org"})
    assert client.get("/api/scientific-assessment/operator/reviewer-setup",headers=HEADERS).status_code==403


def test_all_reviewer_routes_deny_anonymous_calls(env):
    client,_=env
    for path in [
        "/api/scientific-assessment/reviewer/onboarding-status",
        "/api/scientific-assessment/reviewer/me",
        "/api/scientific-assessment/reviewer/packet/"+NCT,
        "/api/scientific-assessment/reviewer/source-documents/"+NCT+"/"+"a"*32,
        "/api/scientific-assessment/operator/reviewer-setup",
    ]:
        assert client.get(path).status_code==401,path
