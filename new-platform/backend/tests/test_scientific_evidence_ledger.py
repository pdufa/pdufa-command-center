"""Scientific evidence ledger: source candidates, append-only versioning, auth and integrity.

All tests use a disposable SQLite database and offline ClinicalTrials.gov fixtures.
The production/review source archives and external sites are never mutated.
"""
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
from app.scientific_evidence_ledger import (
    append_candidate, pilot_candidates, read_ledger, validate_public_https,
)
from app.scientific_readiness_grades import review_readiness

NCT = "NCT02142738"
INTERNAL = "test-internal-key-only"
REVIEW = "test-independent-review-write-secret"
HEADERS = {"x-pdufa-internal-key": INTERNAL}
WRITE_HEADERS = {**HEADERS, "x-pdufa-scientific-review-key": REVIEW}


def _payload():
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": NCT, "briefTitle": "Review pilot"},
            "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE3"]},
            "statusModule": {"overallStatus": "COMPLETED"},
        },
        "hasResults": False,
    }
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    return record, gzip.compress(raw), hashlib.sha256(raw).hexdigest()


def _candidate(**changes):
    data = {
        "gateId": "published_results",
        "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/27718847/",
        "sourceType": "peer_reviewed_publication",
        "sourcePublishedAt": "2016-10-08",
        "claimText": "Report describes one historically published trial analysis.",
        "relationship": "context",
        "caution": "Independent protocol and endpoint reconciliation remains pending.",
        "recordedBy": "Review curator",
    }
    data.update(changes)
    return data


@pytest.fixture
def isolated(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://review.invalid/db")
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", INTERNAL)
    monkeypatch.setenv("PDUFA_SCIENTIFIC_REVIEW_WRITE_KEY", REVIEW)
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED", "0")
    record, archive, checksum = _payload()
    with Session(engine) as session:
        session.add(main.FullTrialRecord(
            nct_id=NCT, payload_gzip=archive, sha256=checksum,
            summary={"nctId": NCT}, statistics=[],
            fetched_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        ))
        session.commit()
    yield TestClient(main.app), engine, record
    engine.dispose()


def test_unverified_keynote_pilot_citations_are_not_verified_evidence(isolated):
    client, _, record = isolated
    candidates = pilot_candidates(NCT)
    assert len(candidates) == 7
    assert {item["sourceType"] for item in candidates} == {
        "peer_reviewed_publication", "institutional_summary",
        "protocol_sap", "official_agency_document"}
    assert all(item["independentlyVerified"] is False for item in candidates)
    assert all(item["canCountTowardReadiness"] is False for item in candidates)
    assert sum(item["reviewStatus"] == "citation_identified_not_adjudicated"
               for item in candidates) == 5
    assert sum(item["reviewStatus"] == "document_locator_identified_not_adjudicated"
               for item in candidates) == 2
    assert pilot_candidates("NCT04280705") == []
    assert review_readiness(NCT, record)["externalEvidenceVerified"] is False
    assert review_readiness(NCT, record)["scientificScore"] is None
    unauth = client.get("/api/scientific-assessment", params={"exact_id":"TRIAL|"+NCT})
    assert unauth.status_code == 401
    resp = client.get("/api/scientific-assessment",
                      params={"exact_id":"TRIAL|"+NCT}, headers=HEADERS)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["evidenceLedgerStatus"] == "candidate_inventory_loaded"
    ledger = payload["evidenceLedger"]
    assert ledger["candidateCount"] == 7
    assert ledger["entryCount"] == 0
    assert ledger["verifiedGateCount"] == 0
    assert len(ledger["externalGateStatuses"]) == 4
    assert all(not item["independentlyVerified"]
               for item in ledger["externalGateStatuses"])
    assert payload["readinessGrades"]["scientificReluctance"]["grade"] == "F"
    worklist=ledger["sourceReconciliation"]
    assert worklist["totalChecks"] == worklist["unresolvedChecks"] == 8
    assert worklist["verifiedChecks"] == 0
    assert worklist["approvalProbability"] is None
    assert all(item["status"]=="open_unadjudicated" and not item["independentlyVerified"]
               for item in worklist["checks"])
    doc_urls={item["sourceUrl"]:item for item in candidates}
    protocol="https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf"
    fda="https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2016/125514Orig1s008,125514Orig1s012ltr.pdf"
    assert doc_urls[protocol]["gateId"]=="protocol_sap"
    assert doc_urls[protocol]["reviewStatus"]=="document_locator_identified_not_adjudicated"
    assert doc_urls[fda]["sourceType"]=="official_agency_document"
    assert doc_urls[fda]["independentlyVerified"] is False
    assert "S-8" in doc_urls[fda]["caution"] and "S-12" in doc_urls[fda]["caution"]
    ids={item["id"]:item for item in worklist["checks"]}
    assert "2017" in ids["protocol_amendment_chronology"]["observedDiscrepancy"]
    assert "2015" in ids["2015_vs_2016_fda_actions"]["title"]
    assert ids["safety_endpoint_taxonomy"]["priority"]=="critical"
    assert ids["pfs_initial_vs_followup"]["status"]=="open_unadjudicated"


def test_other_trial_gets_generic_unverified_checklist():
    from app.scientific_reconciliation_worklist import reconciliation_worklist
    generic=reconciliation_worklist("NCT04280705")
    assert generic["scope"]=="unreviewed_trial"
    assert generic["totalChecks"]==4
    assert generic["verifiedChecks"]==0
    assert all(item["sourceUrls"] == [] for item in generic["checks"])
    assert all(item["scientificScore"] is None for item in generic["checks"])


def test_default_review_write_disabled_even_with_both_credentials(isolated):
    client, _, _ = isolated
    url="/api/scientific-assessment/evidence-ledger/"+NCT
    assert client.post(url,json=_candidate(),headers=WRITE_HEADERS).status_code == 403
    assert read_ledger(NCT)["entryCount"] == 0


def test_write_requires_independent_secret_and_exact_review_service(isolated,monkeypatch):
    client, _, _ = isolated
    url="/api/scientific-assessment/evidence-ledger/"+NCT
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    assert client.post(url,json=_candidate(),headers=HEADERS).status_code == 401
    assert client.post(url,json=_candidate(),headers={
        **HEADERS, "x-pdufa-scientific-review-key":"wrong"}).status_code == 401
    assert client.post(url,json=_candidate(),headers={
        "x-pdufa-scientific-review-key": REVIEW}).status_code == 401
    monkeypatch.setenv("RENDER_SERVICE_ID","production-service")
    assert client.post(url,json=_candidate(),headers=WRITE_HEADERS).status_code == 403
    monkeypatch.setenv("RENDER_SERVICE_ID","srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_REVIEW_WRITE_KEY",INTERNAL)
    assert client.post(url,json=_candidate(),headers={
        **HEADERS, "x-pdufa-scientific-review-key":INTERNAL}).status_code == 503
    assert read_ledger(NCT)["entryCount"] == 0


def test_append_and_supersede_are_versioned_and_never_automatically_verified(isolated,monkeypatch):
    client, engine, record = isolated
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    url="/api/scientific-assessment/evidence-ledger/"+NCT
    first=client.post(url, json=_candidate(), headers=WRITE_HEADERS)
    assert first.status_code == 201, first.text
    a=first.json()
    assert a["revision"]==1 and a["threadId"]==a["id"]
    assert a["reviewStatus"]=="pending_independent_review"
    assert a["independentlyVerified"] is False
    assert a["canCountTowardReadiness"] is False
    assert len(a["contentSha256"])==64

    second=client.post(url,json=_candidate(
        supersedesId=a["id"], relationship="contradicts",
        claimText="Later review raises a discrepancy with the originally listed conclusion.",
    ),headers=WRITE_HEADERS)
    assert second.status_code == 201, second.text
    b=second.json()
    assert b["revision"]==2 and b["threadId"]==a["id"]
    assert b["supersedesId"]==a["id"] and b["relationship"]=="contradicts"
    assert b["contentSha256"]!=a["contentSha256"]
    history=read_ledger(NCT)
    assert history["entryCount"]==2
    assert {e["revision"] for e in history["entries"]}=={1,2}
    assert all(not e["canCountTowardReadiness"] for e in history["entries"])
    assert client.post(url,json=_candidate(supersedesId=a["id"]),
                       headers=WRITE_HEADERS).status_code==422
    body=client.get("/api/scientific-assessment",
                    params={"exact_id":"TRIAL|"+NCT},headers=HEADERS).json()
    assert body["evidenceLedger"]["entryCount"]==2
    assert body["readinessGrades"]["externalEvidenceVerified"] is False
    assert body["readinessGrades"]["scientificReluctance"]["grade"]=="F"
    assert body["assessment"]["overall_score"] is None
    with Session(engine) as session:
        assert session.get(main.FullTrialRecord,NCT).nct_id==NCT


@pytest.mark.parametrize("url",[
    "http://pubmed.ncbi.nlm.nih.gov/27718847/",
    "https://localhost/path",
    "https://127.0.0.1/private",
    "https://[::1]/metadata",
    "https://metadata.google.internal/",
    "https://reviewer:password@pubmed.ncbi.nlm.nih.gov/x",
    "https://example.org/page#inject",
    "https://example.invalid/document",
    "file:///etc/passwd",
])
def test_reject_unsafe_citation_urls(url):
    with pytest.raises(ValueError):
        validate_public_https(url)


def test_unrecognized_fields_cannot_self_certify_or_skip_adjudication(isolated,monkeypatch):
    client, _, _ = isolated
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    url="/api/scientific-assessment/evidence-ledger/"+NCT
    for override in (
        {"reviewStatus":"verified"},
        {"independentlyVerified":True},
        {"gateId":"approval_probability"},
        {"relationship":"proven"},
        {"sourcePublishedAt":"2026-99-99"},
        {"sourceUrl":"http://example.org"},
    ):
        response=client.post(url,json=_candidate(**override),headers=WRITE_HEADERS)
        assert response.status_code==422, (override,response.status_code,response.text)
    assert read_ledger(NCT)["entryCount"]==0


def test_wrong_trial_and_bad_archive_rejected_with_no_ledger_write(isolated,monkeypatch):
    client,engine,_=isolated
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    assert client.post("/api/scientific-assessment/evidence-ledger/NCT00000000",
                       json=_candidate(),headers=WRITE_HEADERS).status_code==422
    with Session(engine) as session:
        row=session.get(main.FullTrialRecord,NCT)
        row.sha256="0"*64
        session.commit()
    resp=client.post("/api/scientific-assessment/evidence-ledger/"+NCT,
                     json=_candidate(),headers=WRITE_HEADERS)
    assert resp.status_code==422
    body=client.get("/api/scientific-assessment",
                    params={"exact_id":"TRIAL|"+NCT},headers=HEADERS).json()
    assert body["evidenceLedger"] is None
    assert body["registryEvidenceStatus"]=="record_unavailable_or_invalid"


def test_detect_manual_tampering_without_affecting_unrelated_science_response(isolated,monkeypatch):
    client,engine,_=isolated
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    response=client.post("/api/scientific-assessment/evidence-ledger/"+NCT,
                         json=_candidate(),headers=WRITE_HEADERS)
    assert response.status_code==201
    with Session(engine) as session:
        row=session.get(main.ScientificEvidenceLedgerEntry,response.json()["id"])
        row.claim_text="A changed citation assertion that lacks a revised content checksum."
        session.commit()
    with pytest.raises(ValueError,match="integrity mismatch"):
        read_ledger(NCT)
    resp=client.get("/api/scientific-assessment",
                    params={"exact_id":"TRIAL|"+NCT},headers=HEADERS)
    assert resp.status_code==200
    data=resp.json()
    assert data["evidenceLedger"] is None
    assert data["evidenceLedgerStatus"]=="ledger_unavailable_or_invalid"
    assert data["registryEvidenceStatus"]=="source_record_loaded"
    assert data["readinessGrades"]["scientificReluctance"]["grade"]=="F"
