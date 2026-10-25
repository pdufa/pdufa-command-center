"""Strict isolated PDF capture, integrity and no-grade-promotion tests.

No live web calls and no clinical content extraction. Database is disposable.
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

from app import main
from app.scientific_evidence_ledger import read_ledger
from app.scientific_reconciliation_worklist import FDA_2016_APPROVAL, EMA_2016_ASSESSMENT
from app.scientific_source_documents import (
    MAX_PDF_BYTES, MAX_EMA_PDF_BYTES, CAPTURE_STATUS, capture_document,
    max_source_pdf_bytes,
    get_captured_document, read_document_manifest,
)

NCT = "NCT02142738"
OTHER = "NCT04280705"
INTERNAL = "pdf-capture-test-internal"
WRITE_KEY = "pdf-capture-independent-review-secret"
HEADERS = {"x-pdufa-internal-key": INTERNAL}
WRITE_HEADERS = {**HEADERS, "x-pdufa-scientific-review-key": WRITE_KEY}


def pdf_bytes(marker=b"A"):
    return b"%PDF-1.7\n1 0 obj<</Type/Catalog>>endobj\n" + marker + b"\n%%EOF\n"


def payload(pdf=None, **changes):
    data = pdf if pdf is not None else pdf_bytes()
    value = {
        "gateId": "official_regulatory",
        "sourceUrl": FDA_2016_APPROVAL,
        "sourceType": "official_agency_document",
        "sha256": hashlib.sha256(data).hexdigest(),
        "contentBase64": base64.b64encode(data).decode("ascii"),
        "capturedBy": "Source archive curator",
    }
    value.update(changes)
    return value


@pytest.fixture
def isolated(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://isolated.invalid/test")
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", INTERNAL)
    monkeypatch.setenv("PDUFA_SCIENTIFIC_REVIEW_WRITE_KEY", WRITE_KEY)
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED", "0")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_DOCUMENT_CAPTURE_ENABLED", "0")
    with Session(engine) as session:
        for identifier in [NCT, OTHER]:
            source = {"protocolSection": {"identificationModule": {"nctId": identifier}},
                      "hasResults": False}
            raw = json.dumps(source, sort_keys=True).encode()
            session.add(main.FullTrialRecord(
                nct_id=identifier, payload_gzip=gzip.compress(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                summary={"nctId": identifier}, statistics=[],
                fetched_at=datetime(2026, 10, 24, tzinfo=timezone.utc),
            ))
        session.commit()
    yield TestClient(main.app), engine
    engine.dispose()


def enable(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED", "1")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_DOCUMENT_CAPTURE_ENABLED", "1")


def test_capture_disabled_by_default_even_when_authorized(isolated, monkeypatch):
    client, engine = isolated
    url = "/api/scientific-assessment/source-documents/"+NCT
    assert client.post(url,json=payload(),headers=WRITE_HEADERS).status_code==403
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    assert client.post(url,json=payload(),headers=WRITE_HEADERS).status_code==403
    monkeypatch.setenv("PDUFA_SCIENTIFIC_DOCUMENT_CAPTURE_ENABLED","1")
    assert client.post(url,json=payload(),headers=HEADERS).status_code==401
    assert client.post(url,json=payload(),headers={
        **HEADERS,"x-pdufa-scientific-review-key":"wrong"}).status_code==401
    assert client.post(url,json=payload(),headers={
        "x-pdufa-scientific-review-key":WRITE_KEY}).status_code==401
    monkeypatch.setenv("RENDER_SERVICE_ID","production")
    assert client.post(url,json=payload(),headers=WRITE_HEADERS).status_code==403
    with Session(engine) as session:
        assert session.query(main.ScientificSourceDocument).count()==0


def test_archive_exact_bytes_readback_manifest_and_no_scientific_promotion(isolated,monkeypatch):
    client, engine = isolated
    enable(monkeypatch)
    document = pdf_bytes()
    url = "/api/scientific-assessment/source-documents/"+NCT
    response = client.post(url,json=payload(document),headers=WRITE_HEADERS)
    assert response.status_code==201,response.text
    meta = response.json()
    assert meta["nctId"]==NCT
    assert meta["gateId"]=="official_regulatory"
    assert meta["sourceUrl"]==FDA_2016_APPROVAL
    assert meta["sha256"]==hashlib.sha256(document).hexdigest()
    assert len(meta["manifestSha256"])==64
    assert meta["byteLength"]==len(document)
    assert meta["captureStatus"]==CAPTURE_STATUS
    assert meta["byteIntegrityChecked"] is True
    assert meta["sourceAuthorshipVerified"] is False
    assert meta["reviewerIdentityVerified"] is False
    assert meta["documentContentScientificallyVerified"] is False
    assert meta["canCountTowardReadiness"] is False
    assert "contentBase64" not in response.text
    assert WRITE_KEY not in response.text and INTERNAL not in response.text

    document_url=url+"/"+meta["documentId"]
    assert client.get(document_url).status_code==401
    receipt=client.get(document_url,headers=HEADERS)
    assert receipt.status_code==200
    assert receipt.content==document
    assert receipt.headers["cache-control"]=="private, no-store"
    assert receipt.headers["content-disposition"].endswith('.pdf"')
    assert receipt.headers["x-content-type-options"]=="nosniff"
    assert receipt.headers["x-source-document-sha256"]==meta["sha256"]
    assert receipt.headers["x-source-scientific-status"]=="not-independently-verified"
    assert client.get(document_url.replace(NCT,OTHER),headers=HEADERS).status_code==404

    manifest=read_document_manifest(NCT)
    assert manifest["sourceDocumentCount"]==1
    assert manifest["totalBytesStored"]==len(document)
    assert manifest["documents"][0]==meta
    assert manifest["independentSourceVerificationCompleted"] is False
    assert read_document_manifest(OTHER)["sourceDocumentCount"]==0

    ledger=read_ledger(NCT)
    assert ledger["capturedSourceDocuments"]["documents"][0]==meta
    assert ledger["verifiedGateCount"]==0
    assert ledger["adjudicationPreflight"]["questionsIndependentlyResolved"]==0
    detail=client.get("/api/scientific-assessment",
        params={"exact_id":"TRIAL|"+NCT},headers=HEADERS).json()
    assert detail["readinessGrades"]["externalEvidenceVerified"] is False
    assert detail["readinessGrades"]["scientificReluctance"]["grade"]=="F"
    assert detail["assessment"]["overall_score"] is None

    packet=client.get("/api/scientific-assessment/review-packet/"+NCT,
        headers=HEADERS)
    assert packet.status_code==200
    body=packet.json()
    assert body["independentSourceLedger"]["capturedSourceDocuments"]["sourceDocumentCount"]==1
    assert body["independentSourceLedger"]["capturedSourceDocuments"]["documents"][0]["sha256"]==meta["sha256"]
    assert "contentBase64" not in packet.text
    assert body["readyForFullScientificConclusion"] is False
    assert body["fdaApprovalProbability"] is None
    with Session(engine) as session:
        assert session.query(main.FullTrialRecord).count()==2
        assert session.query(main.ScientificBatchJob).count()==0
        assert session.query(main.ScientificReviewerFinding).count()==0


def test_wrong_digest_pdf_headers_duplicate_invalid_base64_and_bad_trial(isolated,monkeypatch):
    client, engine = isolated
    enable(monkeypatch)
    url="/api/scientific-assessment/source-documents/"+NCT
    doc=pdf_bytes()
    cases=[
        payload(doc,sha256="0"*64),
        payload(b"not a pdf but it does have enough length to be accepted"),
        payload(b"%PDF-1.7\n" + b"a"*80),
        payload(doc,contentBase64="non-base64-content~~"),
        payload(doc,sourceUrl="https://clinicaltrials.gov/study/"+OTHER),
        payload(doc,sourceUrl="https://other.example.com/wrong-document.pdf"),
        payload(doc,gateId="not_a_real_gate"),
        payload(doc,independentlyVerified=True),
    ]
    for item in cases:
        response=client.post(url,json=item,headers=WRITE_HEADERS)
        assert response.status_code==422,(response.status_code,response.text,item.get("sourceUrl"))
    first=client.post(url,json=payload(doc),headers=WRITE_HEADERS)
    assert first.status_code==201,first.text
    repeated=client.post(url,json=payload(doc),headers=WRITE_HEADERS)
    assert repeated.status_code in (409,422)
    assert read_document_manifest(NCT)["sourceDocumentCount"]==1
    with Session(engine) as session:
        assert session.query(main.ScientificSourceDocument).count()==1


def test_tampered_bytes_and_metadata_fail_closed_for_all_review_exports(isolated,monkeypatch):
    client, engine = isolated
    enable(monkeypatch)
    url="/api/scientific-assessment/source-documents/"+NCT
    response=client.post(url,json=payload(),headers=WRITE_HEADERS)
    assert response.status_code==201
    identity=response.json()["documentId"]
    with Session(engine) as session:
        row=session.get(main.ScientificSourceDocument,identity)
        row.payload=pdf_bytes(b"changed")
        session.commit()
    with pytest.raises(ValueError,match="SHA-256 mismatch|length mismatch"):
        read_document_manifest(NCT)
    assert client.get(url+"/"+identity,headers=HEADERS).status_code==409
    packet=client.get("/api/scientific-assessment/review-packet/"+NCT,headers=HEADERS)
    assert packet.status_code==409
    details=client.get("/api/scientific-assessment",
        params={"exact_id":"TRIAL|"+NCT},headers=HEADERS).json()
    assert details["evidenceLedgerStatus"]=="ledger_unavailable_or_invalid"
    with Session(engine) as session:
        row=session.get(main.ScientificSourceDocument,identity)
        row.payload=pdf_bytes()
        row.source_url="https://example.org/forged.pdf"
        session.commit()
    with pytest.raises(ValueError,match="metadata integrity mismatch"):
        read_document_manifest(NCT)
    assert client.get(url+"/"+identity,headers=HEADERS).status_code==409


def test_unknown_archive_does_not_accept_pdf_source(isolated,monkeypatch):
    client,_=isolated
    enable(monkeypatch)
    assert client.post("/api/scientific-assessment/source-documents/NCT00000000",
        json=payload(),headers=WRITE_HEADERS).status_code==422


def test_invalid_archive_checksum_prevents_pdf_capture(isolated,monkeypatch):
    client,engine=isolated
    enable(monkeypatch)
    with Session(engine) as session:
        row=session.get(main.FullTrialRecord,NCT)
        row.sha256="0"*64
        session.commit()
    assert client.post("/api/scientific-assessment/source-documents/"+NCT,
        json=payload(),headers=WRITE_HEADERS).status_code==422
    with Session(engine) as session:
        assert session.query(main.ScientificSourceDocument).count()==0


def test_capture_budget_is_bounded(isolated,monkeypatch):
    client,engine=isolated
    enable(monkeypatch)
    assert client.post("/api/scientific-assessment/source-documents/"+NCT,
        json=payload(pdf_bytes(b"z"*(MAX_PDF_BYTES + 1))),
        headers=WRITE_HEADERS).status_code==422
    with Session(engine) as session:
        assert session.query(main.ScientificSourceDocument).count()==0



def test_archival_status_and_pinned_source_labels_fit_postgres_varchars():
    """SQLite doesn't enforce VARCHAR widths; PostgreSQL does."""
    table = main.ScientificSourceDocument.__table__.columns
    assert len(CAPTURE_STATUS) <= table["capture_status"].type.length
    assert len("Verified Google operator: pinned source") <= table["captured_by"].type.length
    assert len("official_regulatory") <= table["gate_id"].type.length
    assert len("official_agency_document") <= table["source_type"].type.length
    assert len(FDA_2016_APPROVAL) <= table["source_url"].type.length
    assert len(NCT + "_" + "a"*32 + ".pdf") <= table["filename"].type.length



def test_only_exact_pinned_ema_pdf_gets_larger_archival_byte_limit(isolated):
    _,engine=isolated
    assert MAX_PDF_BYTES == 4*1024*1024
    assert MAX_EMA_PDF_BYTES == 16*1024*1024
    for variation in (
        (OTHER,"protocol_sap",EMA_2016_ASSESSMENT,"official_agency_document"),
        (NCT,"official_regulatory",EMA_2016_ASSESSMENT,"official_agency_document"),
        (NCT,"protocol_sap",FDA_2016_APPROVAL,"official_agency_document"),
        (NCT,"protocol_sap",EMA_2016_ASSESSMENT,"protocol_sap"),
    ):
        assert max_source_pdf_bytes(*variation) == MAX_PDF_BYTES
    assert max_source_pdf_bytes(
        NCT,"protocol_sap",EMA_2016_ASSESSMENT,"official_agency_document"
    ) == MAX_EMA_PDF_BYTES

    # Slightly over the default limit: valid ONLY for this regulator source;
    # the immutable SHA/manifest and scientific non-verification are retained.
    raw=pdf_bytes(b"Z"*(MAX_PDF_BYTES+128))
    body=payload(raw,gateId="protocol_sap",
                 sourceType="official_agency_document",
                 sourceUrl=EMA_2016_ASSESSMENT)
    receipt=capture_document(NCT,body)
    assert receipt["sha256"]==hashlib.sha256(raw).hexdigest()
    assert receipt["byteLength"]==len(raw)
    assert receipt["documentContentScientificallyVerified"] is False
    assert receipt["canCountTowardReadiness"] is False
    assert receipt["sourceAuthorshipVerified"] is False
    assert read_document_manifest(NCT)["sourceDocumentCount"]==1
    with pytest.raises(ValueError,match="size"):
        capture_document(NCT,payload(raw))
    with Session(engine) as session:
        assert session.query(main.ScientificReviewerFinding).count()==0


def test_default_cap_never_increases_for_non_ema_sources():
    assert max_source_pdf_bytes(
        NCT,"official_regulatory",FDA_2016_APPROVAL,"official_agency_document"
    ) == MAX_PDF_BYTES
