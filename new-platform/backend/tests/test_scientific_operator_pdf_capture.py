"""Isolated Google operator PDF capture tests; never independent scientific verification.

No public-source fetches, production writes, real Google tokens or trading actions.
"""
import base64
import gzip
import hashlib
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main, scientific_google_identity
from app.scientific_reconciliation_worklist import PROTOCOL_SAP, FDA_2016_APPROVAL
from app.scientific_source_documents import read_document_manifest

NCT = "NCT02142738"
OTHER = "NCT04280705"
TOKEN = "Bearer simulated-google-auth-token"
HEADERS = {"Authorization": TOKEN}


def sample_pdf(content=b"Archived source bytes, not independently verified"):
    return b"%PDF-1.7\n1 0 obj<</Type/Catalog>>endobj\n" + content + b"\n%%EOF\n"


def submission(raw=None, *, regulatory=False, **changes):
    raw = raw if raw is not None else sample_pdf()
    data = {
        "gateId": "official_regulatory" if regulatory else "protocol_sap",
        "sourceType": "official_agency_document" if regulatory else "protocol_sap",
        "sourceUrl": FDA_2016_APPROVAL if regulatory else PROTOCOL_SAP,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "contentBase64": base64.b64encode(raw).decode("ascii"),
    }
    data.update(changes)
    return data


@pytest.fixture
def isolated(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://isolated.invalid/pilot")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.delenv("PDUFA_SCIENTIFIC_OPERATOR_PDF_CAPTURE_ENABLED", raising=False)
    monkeypatch.setenv("PDUFA_SCIENTIFIC_DOCUMENT_CAPTURE_ENABLED", "0")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED", "0")
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda _: {"providerSubject": "a-google-subject",
                                   "verifiedEmail": "owner@example.org"})
    for identifier in [NCT, OTHER]:
        record = {"protocolSection": {"identificationModule": {"nctId": identifier}},
                  "hasResults": False}
        raw = json.dumps(record, sort_keys=True).encode("utf-8")
        with Session(engine) as session:
            session.add(main.FullTrialRecord(
                nct_id=identifier, payload_gzip=gzip.compress(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                summary={"nctId": identifier}, statistics=[],
                fetched_at=datetime(2026, 10, 25, tzinfo=timezone.utc),
            ))
            session.commit()
    yield TestClient(main.app), engine
    engine.dispose()


def enabled(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_OPERATOR_PDF_CAPTURE_ENABLED", "1")


def test_operator_document_archive_disabled_by_default(isolated):
    client, engine = isolated
    r = client.post("/api/scientific-assessment/operator/source-documents/"+NCT,
                    headers=HEADERS, json=submission())
    assert r.status_code == 403
    assert client.get("/api/scientific-assessment/operator/me", headers=HEADERS
                      ).json()["mayArchiveSourcePdf"] is False
    with Session(engine) as session:
        assert session.query(main.ScientificSourceDocument).count() == 0


def test_no_google_identity_or_wrong_user_can_archive(isolated, monkeypatch):
    client, engine = isolated
    enabled(monkeypatch)
    path="/api/scientific-assessment/operator/source-documents/"+NCT
    assert client.post(path, json=submission()).status_code == 401
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda _: {"verifiedEmail": "other-person@example.org"})
    assert client.post(path, headers=HEADERS, json=submission()).status_code == 403
    with Session(engine) as session:
        assert session.query(main.ScientificSourceDocument).count() == 0


def test_operator_capture_requires_isolated_postgres_and_service(isolated, monkeypatch):
    client, engine = isolated
    enabled(monkeypatch)
    path="/api/scientific-assessment/operator/source-documents/"+NCT
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-production")
    assert client.post(path, headers=HEADERS, json=submission()).status_code == 403
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.setattr(main, "DATABASE_URL", "sqlite:///not-isolated.db")
    assert client.post(path, headers=HEADERS, json=submission()).status_code == 403
    with Session(engine) as session:
        assert session.query(main.ScientificSourceDocument).count() == 0


def test_capture_exact_pdf_bytes_with_google_only_no_review_key(isolated, monkeypatch):
    client, engine = isolated
    enabled(monkeypatch)
    raw = sample_pdf()
    path="/api/scientific-assessment/operator/source-documents/"+NCT
    r=client.post(path, headers=HEADERS, json=submission(raw))
    assert r.status_code == 201, r.text
    body=r.json()
    assert body["sha256"] == hashlib.sha256(raw).hexdigest()
    assert body["byteLength"] == len(raw)
    assert body["capturedBy"] == "Verified Google operator"
    assert body["byteIntegrityChecked"] is True
    assert body["sourceAuthorshipVerified"] is False
    assert body["documentContentScientificallyVerified"] is False
    assert body["canCountTowardReadiness"] is False
    assert body["gateId"] == "protocol_sap"
    assert "contentBase64" not in r.text

    download=path+"/"+body["documentId"]
    assert client.get(download).status_code == 401
    r2=client.get(download, headers=HEADERS)
    assert r2.status_code == 200
    assert r2.content == raw
    assert r2.headers["x-source-document-sha256"] == body["sha256"]
    assert r2.headers["x-source-scientific-status"] == "not-independently-verified"
    assert "no-store" in r2.headers["cache-control"]
    assert client.get(download.replace(NCT, OTHER), headers=HEADERS).status_code == 404

    manifest=read_document_manifest(NCT)
    assert manifest["sourceDocumentCount"] == 1
    assert manifest["documents"][0] == body
    from app.scientific_review_packet import build_review_packet
    packet = build_review_packet(NCT)
    assert packet["scientificallyVerified"] is False
    assert packet["readyForFullScientificConclusion"] is False
    assert packet["independentSourceLedger"]["verifiedGateCount"] == 0
    assert packet["independentSourceLedger"]["capturedSourceDocuments"]["sourceDocumentCount"] == 1
    assert packet["scientificConclusion"] is None
    assert packet["fdaApprovalProbability"] is None
    with Session(engine) as session:
        assert session.query(main.ScientificReviewerAccount).count() == 0
        assert session.query(main.ScientificReviewSubmission).count() == 0
        assert session.query(main.ScientificReviewerFinding).count() == 0


def test_reject_wrong_source_gate_digest_forged_claims_and_duplicate(isolated, monkeypatch):
    client, engine = isolated
    enabled(monkeypatch)
    path="/api/scientific-assessment/operator/source-documents/"+NCT
    invalid=[
        submission(sourceUrl="https://example.com/research.pdf"),
        submission(gateId="official_regulatory"),
        submission(sourceType="official_agency_document"),
        submission(sha256="0"*64),
        submission(raw=b"not a PDF file, too invalid for this capture"),
        submission(capturedBy="forged independent reviewer"),
        submission(independentlyVerified=True),
    ]
    for value in invalid:
        r=client.post(path,headers=HEADERS,json=value)
        assert r.status_code == 422, (r.status_code, r.text)
    assert client.post(path,headers=HEADERS,json=submission(),).status_code == 201
    assert client.post(path,headers=HEADERS,json=submission(),).status_code in (409,422)
    assert client.post(path.replace(NCT, OTHER),headers=HEADERS,json=submission()).status_code == 403
    with Session(engine) as session:
        assert session.query(main.ScientificSourceDocument).count() == 1


def test_capture_rejects_corrupt_pilot_record_without_mutation(isolated, monkeypatch):
    client, engine = isolated
    enabled(monkeypatch)
    with Session(engine) as session:
        archived = session.get(main.FullTrialRecord,NCT)
        archived.sha256 = "0"*64
        session.commit()
    path="/api/scientific-assessment/operator/source-documents/"+NCT
    r=client.post(path,headers=HEADERS,json=submission())
    assert r.status_code == 422
    with Session(engine) as session:
        assert session.query(main.ScientificSourceDocument).count() == 0


def test_tampered_pdf_fails_closed_after_google_upload(isolated, monkeypatch):
    client, engine = isolated
    enabled(monkeypatch)
    path="/api/scientific-assessment/operator/source-documents/"+NCT
    r=client.post(path,headers=HEADERS,json=submission())
    assert r.status_code == 201
    doc=r.json()["documentId"]
    with Session(engine) as session:
        row=session.get(main.ScientificSourceDocument,doc)
        row.payload=sample_pdf(b"incorrect modified bytes")
        session.commit()
    read=client.get(path+"/"+doc,headers=HEADERS)
    assert read.status_code == 409
    with pytest.raises(ValueError,match="mismatch"):
        read_document_manifest(NCT)
