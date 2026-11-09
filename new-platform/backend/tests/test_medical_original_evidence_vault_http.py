"""Isolated opt-in encrypted evidence HTTP authorization and persistence tests."""
from __future__ import annotations

import base64
import hashlib
import os

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
import pytest

from app import medical_original_evidence_vault as core
from app import medical_original_evidence_vault_http as http

RAW = b"%PDF-1.7\n" + b"Exact trial original public analysis source data " * 10
READER = "R"*40
WRITER = "W"*40


@pytest.fixture
def isolated(monkeypatch):
    engine=create_engine("sqlite+pysqlite:///:memory:",connect_args={"check_same_thread":False},
                         poolclass=__import__("sqlalchemy").pool.StaticPool)
    core.initialize(engine,test_only=True)
    monkeypatch.setenv("PDUFA_ORIGINAL_EVIDENCE_VAULT_ENABLED","true")
    monkeypatch.setenv("PDUFA_MEDICAL_PREVIEW_ENABLED","true")
    monkeypatch.setenv("PDUFA_REQUIRE_POSTGRES","true")
    monkeypatch.setenv("RENDER_SERVICE_ID",http.ISOLATED_SERVICE)
    monkeypatch.setenv("PDUFA_EVIDENCE_VAULT_READ_KEY",READER)
    monkeypatch.setenv("PDUFA_EVIDENCE_VAULT_WRITE_KEY",WRITER)
    monkeypatch.setenv("PDUFA_EVIDENCE_ENCRYPTION_KEY_B64",base64.b64encode(b"X"*32).decode())
    monkeypatch.setattr(http,"_initialize",lambda engine,require: None)
    app=FastAPI()
    http.install_routes(app,lambda:engine,lambda:None)
    with TestClient(app) as client:
        yield client,engine
    engine.dispose()


def candidate():
    return {
      "metadata":{
        "nct":"NCT06081894","requestId":"LOCKED_PRIMARY_SAP",
        "documentType":"STATISTICAL_ANALYSIS_PLAN",
        "documentTitle":"Original trial verified source candidate",
        "documentVersion":"Draft 1.0","documentDate":"2026-11-01",
        "sourceUrl":"https://clinicaltrials.gov/study/NCT06081894",
        "claimedSha256":hashlib.sha256(RAW).hexdigest(),
        "contentType":"application/pdf"},
      "originalBytesBase64":base64.b64encode(RAW).decode(),
      "rightsAttestation":http.RIGHTS,
    }


def test_routes_not_registered_by_default_without_explicit_service_environment(monkeypatch):
    monkeypatch.delenv("PDUFA_ORIGINAL_EVIDENCE_VAULT_ENABLED",raising=False)
    app=FastAPI()
    http.install_routes(app,lambda:None,lambda:None)
    client=TestClient(app)
    assert client.get("/api/internal/medical-original-evidence-vault/NCT06081894").status_code==404
    assert client.post("/api/internal/medical-original-evidence-vault/NCT06081894").status_code==404


def test_public_browser_cannot_write_without_dedicated_secret(isolated):
    client,_=isolated
    path="/api/internal/medical-original-evidence-vault/NCT06081894"
    assert client.get(path).status_code==401
    assert client.post(path,json=candidate()).status_code==401
    assert client.post(path,json=candidate(),headers={"X-PDUFA-Evidence-Key":READER}).status_code==401
    assert client.get(path,headers={"X-PDUFA-Evidence-Key":WRITER}).status_code==401
    assert client.post(path,json=candidate(),headers={
      "X-PDUFA-Evidence-Key":WRITER,
      "X-PDUFA-Evidence-Officer":"research.intake",
      "Origin":"https://pdufa.example"
    }).status_code==403
    assert client.get(path,headers={"X-PDUFA-Evidence-Key":READER}).status_code==200
    assert client.get(path,headers={"X-PDUFA-Evidence-Key":READER}).json()["receipts"]==[]


def test_authorized_original_document_is_really_encrypted_and_receipt_only(isolated):
    client,engine=isolated
    path="/api/internal/medical-original-evidence-vault/NCT06081894"
    h={"X-PDUFA-Evidence-Key":WRITER,"X-PDUFA-Evidence-Officer":"research.intake"}
    created=client.post(path,json=candidate(),headers=h)
    assert created.status_code==201,created.text
    doc=created.json()
    assert doc["encrypted"] is True
    assert doc["sourceHashComputedFromOriginalBytes"] is True
    assert doc["issuerAndClinicalContentIndependentlyVerified"] is False
    assert doc["medicalGradesWritten"]==0
    assert doc["fdaPrediction"]=="ABSTAIN"
    assert "originalBytesBase64" not in created.text
    assert base64.b64encode(RAW).decode() not in created.text
    rows=client.get(path,headers={"X-PDUFA-Evidence-Key":READER})
    assert rows.status_code==200
    assert len(rows.json()["receipts"])==1
    assert rows.json()["clinicalGradeEventsWritten"]==0
    assert rows.json()["originalBytesExposed"] is False
    assert base64.b64encode(RAW).decode() not in rows.text
    assert core.verify_at_rest(engine,receipt_id=doc["receiptId"],
                               encryption_key=b"X"*32)["sha256Verified"] is True


def test_rights_wrong_hash_unknown_nct_and_tampered_media_never_archived(isolated):
    client,_=isolated
    path="/api/internal/medical-original-evidence-vault/NCT06081894"
    h={"X-PDUFA-Evidence-Key":WRITER,"X-PDUFA-Evidence-Officer":"research.intake"}
    samples=[
      {"rightsAttestation":"I_OBTAINED_NO_RIGHTS"},
      {"metadata":{**candidate()["metadata"],"nct":"NCT00000000"}},
      {"metadata":{**candidate()["metadata"],"claimedSha256":"0"*64}},
      {"metadata":{**candidate()["metadata"],"sourceUrl":"https://127.0.0.1/private"}},
      {"metadata":{**candidate()["metadata"],"contentType":"application/octet-stream"}},
    ]
    for update in samples:
        data=candidate();data.update(update)
        r=client.post(path,json=data,headers=h)
        assert r.status_code==422,r.text
    assert client.get(path,headers={"X-PDUFA-Evidence-Key":READER}).json()["receipts"]==[]


def test_no_storage_if_wrong_feature_scope_or_role_credentials(isolated,monkeypatch):
    client,_=isolated
    path="/api/internal/medical-original-evidence-vault/NCT06081894"
    h={"X-PDUFA-Evidence-Key":WRITER,"X-PDUFA-Evidence-Officer":"research.intake"}
    monkeypatch.setenv("RENDER_SERVICE_ID","srv-production-other")
    assert client.post(path,json=candidate(),headers=h).status_code==503
    monkeypatch.setenv("RENDER_SERVICE_ID",http.ISOLATED_SERVICE)
    monkeypatch.setenv("PDUFA_EVIDENCE_VAULT_READ_KEY",WRITER)
    assert client.post(path,json=candidate(),headers=h).status_code==503
    assert client.get(path,headers={"X-PDUFA-Evidence-Key":READER}).status_code==503


def test_rejects_malformed_base64_and_large_bodies_before_storage(isolated):
    client,_=isolated
    path="/api/internal/medical-original-evidence-vault/NCT06081894"
    h={"X-PDUFA-Evidence-Key":WRITER,"X-PDUFA-Evidence-Officer":"research.intake"}
    altered=candidate();altered["originalBytesBase64"]="not valid"
    assert client.post(path,json=altered,headers=h).status_code==422
    altered=candidate();altered["originalBytesBase64"]=base64.b64encode(b"%PDF-1.7\n"+b"A"*(core.MAX_DOCUMENT_BYTES+1)).decode()
    assert client.post(path,json=altered,headers=h).status_code in (413,422)
    assert client.get(path,headers={"X-PDUFA-Evidence-Key":READER}).json()["receipts"]==[]
