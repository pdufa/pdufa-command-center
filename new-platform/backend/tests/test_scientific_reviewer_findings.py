"""Offline audit tests for guarded source-specific scientific reviewer statements."""
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
from app.scientific_reviewer_findings import (
    append_reviewer_statement, read_reviewer_statements,
)
from app.scientific_reconciliation_worklist import PROTOCOL_SAP, FDA_2016_APPROVAL

NCT = "NCT02142738"
OTHER = "NCT04280705"
INTERNAL = "test-internal-header"
REVIEW = "test-independent-review-secret"
HEADERS = {"x-pdufa-internal-key": INTERNAL}
WRITE_HEADERS = {**HEADERS, "x-pdufa-scientific-review-key": REVIEW}


def _payload(nct_id):
    return {
        "questionId": "protocol_amendment_chronology",
        "sourceUrl": PROTOCOL_SAP,
        "sourceLocator": "PDF protocol section 6, pages 25-27",
        "findingType": "uncertain",
        "assertion": "The protocol revision history needs reconciliation against the initial interim analysis cutoff.",
        "uncertainty": "The posted protocol may contain amendments after the original 2016 cutoff.",
        "reviewerLabel": "Pilot reviewer A",
        "reviewerAttestsReadSource": True,
    }


@pytest.fixture
def review(monkeypatch):
    engine = create_engine(
        "sqlite://", poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://review.invalid/db")
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", INTERNAL)
    monkeypatch.setenv("PDUFA_SCIENTIFIC_REVIEW_WRITE_KEY", REVIEW)
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED", "0")
    with Session(engine) as session:
        for nct in (NCT, OTHER):
            source = {"protocolSection":{"identificationModule":{"nctId":nct}},
                      "hasResults": False}
            raw = json.dumps(source, sort_keys=True).encode()
            session.add(main.FullTrialRecord(
                nct_id=nct, payload_gzip=gzip.compress(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                summary={"nctId": nct}, statistics=[],
                fetched_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            ))
        session.commit()
    yield TestClient(main.app), engine
    engine.dispose()


def test_zero_reviewer_statements_and_existing_grade_still_unscored(review):
    client, engine = review
    ledger = read_ledger(NCT)
    assert ledger["reviewerFindings"]["totalStatements"] == 0
    assert ledger["sourceReconciliation"]["reviewerStatementCount"] == 0
    assert ledger["sourceReconciliation"]["verifiedChecks"] == 0
    assert ledger["reviewerFindings"]["independentConfirmationImplemented"] is False
    assert len(ledger["reviewerFindings"]["questionSummaries"]) == 8
    assert all(not item["resolved"] for item in ledger["reviewerFindings"]["questionSummaries"])
    assert client.post("/api/scientific-assessment/reviewer-statements/" + NCT,
                       json=_payload(NCT), headers=WRITE_HEADERS).status_code == 403
    with Session(engine) as session:
        assert session.query(main.ScientificReviewerFinding).count() == 0


def test_separate_writer_key_and_exact_service_gate(review,monkeypatch):
    client, _ = review
    url="/api/scientific-assessment/reviewer-statements/" + NCT
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    assert client.post(url,json=_payload(NCT),headers=HEADERS).status_code == 401
    assert client.post(url,json=_payload(NCT),headers={
        **HEADERS, "x-pdufa-scientific-review-key": "not-valid"}).status_code == 401
    assert client.post(url,json=_payload(NCT),headers={
        "x-pdufa-scientific-review-key": REVIEW}).status_code == 401
    monkeypatch.setenv("RENDER_SERVICE_ID","srv-other-service")
    assert client.post(url,json=_payload(NCT),headers=WRITE_HEADERS).status_code == 403
    monkeypatch.setenv("RENDER_SERVICE_ID","srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_REVIEW_WRITE_KEY",INTERNAL)
    assert client.post(url,json=_payload(NCT),headers={
        **HEADERS,"x-pdufa-scientific-review-key":INTERNAL}).status_code == 503
    assert read_reviewer_statements(NCT)["totalStatements"] == 0


def test_unverified_statements_conflicts_revisions_and_packet_are_consistent(review,monkeypatch):
    client, engine = review
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    url="/api/scientific-assessment/reviewer-statements/" + NCT
    first=client.post(url,json={
        **_payload(NCT),
        "findingType":"supports",
        "assertion":"The protocol version appears to preserve the interim PFS analysis definition, pending reviewer cross-check.",
    },headers=WRITE_HEADERS)
    assert first.status_code == 201,first.text
    a=first.json()
    assert a["reviewStatus"]=="reviewer_statement_pending_independent_confirmation"
    assert a["revision"]==1 and a["threadId"]==a["id"]
    assert a["independentlyVerified"] is False
    assert a["reviewerIdentityVerified"] is False
    assert a["canResolveQuestion"] is False
    assert a["canCountTowardReadiness"] is False
    assert len(a["contentSha256"])==64

    second=client.post(url,json={
        **_payload(NCT),
        "findingType":"contradicts",
        "assertion":"A different protocol amendment could change the prospective alpha spending rule, requiring reconciliation.",
        "reviewerLabel":"Pilot reviewer B",
    },headers=WRITE_HEADERS)
    assert second.status_code==201,second.text
    b=second.json()
    assert b["threadId"]!=a["threadId"]

    findings=read_reviewer_statements(NCT)
    assert findings["totalStatements"]==2
    assert findings["questionsWithConflictingStatements"]==1
    first_q={x["questionId"]:x for x in findings["questionSummaries"]}
    assert first_q["protocol_amendment_chronology"]["conflictingReviewerStatements"] is True
    assert first_q["protocol_amendment_chronology"]["resolved"] is False
    assert findings["questionsIndependentlyResolved"]==0

    revised=client.post(url,json={
        **_payload(NCT), "supersedesId":b["id"],
        "findingType":"uncertain",
        "reviewerLabel":"Pilot reviewer B",
        "assertion":"I withdraw the prior contradiction pending independent review of the 2016 statistical analysis plan.",
    },headers=WRITE_HEADERS)
    assert revised.status_code==201,revised.text
    c=revised.json()
    assert c["revision"]==2 and c["threadId"]==b["threadId"]
    assert c["supersedesId"]==b["id"]
    assert read_reviewer_statements(NCT)["questionsWithConflictingStatements"]==0
    assert client.post(url,json={**_payload(NCT),"supersedesId":b["id"]},
                       headers=WRITE_HEADERS).status_code==422

    ledger=read_ledger(NCT)
    assert ledger["reviewerFindings"]["totalStatements"]==3
    assert ledger["sourceReconciliation"]["reviewerStatementCount"]==3
    assert ledger["verifiedGateCount"]==0
    assert ledger["sourceReconciliation"]["unresolvedChecks"]==8
    response=client.get("/api/scientific-assessment",
                        params={"exact_id":"TRIAL|"+NCT},headers=HEADERS).json()
    assert response["readinessGrades"]["scientificReluctance"]["grade"]=="F"
    assert response["readinessGrades"]["externalEvidenceVerified"] is False
    assert response["assessment"]["overall_score"] is None

    exported=client.get("/api/scientific-assessment/review-packet/"+NCT,
                        headers=HEADERS)
    assert exported.status_code==200
    pkt=exported.json()
    assert pkt["independentSourceLedger"]["reviewerFindings"]["totalStatements"]==3
    assert pkt["reconciliation"]["unresolvedCount"]==8
    assert pkt["reconciliation"]["independentlyResolvedCount"]==0
    question={item["id"]:item for item in pkt["reconciliation"]["checks"]}
    assert question["protocol_amendment_chronology"]["reviewerStatementCount"]==3
    assert question["protocol_amendment_chronology"]["conflictingReviewerStatements"] is False
    assert all(not q["resolved"] for q in pkt["reconciliation"]["checks"])
    assert pkt["scientificConclusion"] is None
    assert REVIEW not in exported.text and INTERNAL not in exported.text
    with Session(engine) as session:
        assert session.query(main.ScientificEvidenceLedgerEntry).count()==0
        assert session.query(main.ScientificReviewerFinding).count()==3


@pytest.mark.parametrize("changes",[
    {"reviewerAttestsReadSource":False},
    {"reviewStatus":"verified"},
    {"independentlyVerified":True},
    {"resolved":True},
    {"fdaApprovalProbability":0.99},
    {"questionId":"fake_question"},
    {"sourceUrl":"https://other.example.org/random"},
    {"sourceUrl":FDA_2016_APPROVAL},
    {"sourceLocator":"a"},
    {"assertion":"too short"},
    {"uncertainty":"insufficient"},
    {"findingType":"success"},
])
def test_invalid_or_self_verified_claims_fail_closed(review,monkeypatch,changes):
    client,_=review
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    response=client.post(
        "/api/scientific-assessment/reviewer-statements/"+NCT,
        json={**_payload(NCT),**changes},headers=WRITE_HEADERS,
    )
    assert response.status_code==422,(changes,response.status_code,response.text)
    assert read_reviewer_statements(NCT)["totalStatements"]==0


def test_generic_trial_requires_prior_source_ledger_candidate(review,monkeypatch):
    client,_=review
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    url="/api/scientific-assessment/reviewer-statements/"+OTHER
    own_registry="https://clinicaltrials.gov/study/"+OTHER
    assert client.post(url,json={
        **_payload(OTHER), "sourceUrl":own_registry,
        "questionId":"external_protocol_sap",
    },headers=WRITE_HEADERS).status_code==422
    candidate=client.post("/api/scientific-assessment/evidence-ledger/"+OTHER,json={
        "gateId":"protocol_sap","sourceUrl":own_registry,
        "sourceType":"protocol_sap",
        "claimText":"Document locator found for review, not independently validated.",
        "relationship":"context",
        "caution":"Trial identities must be independently matched before interpretation.",
        "recordedBy":"Offline reviewer",
    },headers=WRITE_HEADERS)
    assert candidate.status_code==201,candidate.text
    result=client.post(url,json={
        **_payload(OTHER), "sourceUrl":own_registry,
        "questionId":"external_protocol_sap",
    },headers=WRITE_HEADERS)
    assert result.status_code==201,result.text
    assert result.json()["independentlyVerified"] is False
    assert read_reviewer_statements(OTHER)["questionsIndependentlyResolved"]==0
    assert read_reviewer_statements(NCT)["totalStatements"]==0


def test_wrong_registry_nct_url_cannot_be_submitted_for_another_trial(review,monkeypatch):
    client,_=review
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    other_url="https://clinicaltrials.gov/study/"+OTHER
    assert client.post("/api/scientific-assessment/evidence-ledger/"+NCT,json={
        "gateId":"protocol_sap","sourceUrl":other_url,
        "sourceType":"protocol_sap",
        "claimText":"Cross-trial archive link should not qualify for this study.",
        "relationship":"context",
        "caution":"A cited trial ID differs from this original study identifier.",
        "recordedBy":"Offline reviewer",
    },headers=WRITE_HEADERS).status_code==422
    assert client.post("/api/scientific-assessment/reviewer-statements/"+NCT,
        json={**_payload(NCT),"sourceUrl":other_url},
        headers=WRITE_HEADERS).status_code==422
    assert client.post("/api/scientific-assessment/evidence-ledger/"+NCT,json={
        "gateId":"protocol_sap","sourceUrl":"https://clinicaltrials.gov/search",
        "sourceType":"protocol_sap",
        "claimText":"Unscoped search page should not count as an exact trial source.",
        "relationship":"context",
        "caution":"A broad search is not exact trial evidence or a primary protocol.",
        "recordedBy":"Offline reviewer",
    },headers=WRITE_HEADERS).status_code==422
    assert read_reviewer_statements(NCT)["totalStatements"]==0


def test_cross_trial_supersession_refused_and_archive_tamper_fails_closed(review,monkeypatch):
    client, engine=review
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    url="/api/scientific-assessment/reviewer-statements/"+NCT
    first=client.post(url,json=_payload(NCT),headers=WRITE_HEADERS)
    assert first.status_code==201
    prior=first.json()["id"]
    other=client.post("/api/scientific-assessment/reviewer-statements/"+OTHER,
                      json={**_payload(OTHER), "questionId":"external_protocol_sap",
                            "supersedesId":prior},headers=WRITE_HEADERS)
    assert other.status_code==422
    with Session(engine) as session:
        row=session.get(main.FullTrialRecord,NCT)
        row.sha256="0"*64
        session.commit()
    assert client.post(url,json=_payload(NCT),headers=WRITE_HEADERS).status_code==422


def test_manually_tampered_reviewer_statement_blocks_packet_and_ledger(review,monkeypatch):
    client,engine=review
    monkeypatch.setenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED","1")
    result=client.post(
        "/api/scientific-assessment/reviewer-statements/"+NCT,
        json=_payload(NCT),headers=WRITE_HEADERS,
    )
    assert result.status_code==201
    with Session(engine) as session:
        item=session.get(main.ScientificReviewerFinding,result.json()["id"])
        item.assertion="Somebody altered the reviewer statement without a new revision."
        session.commit()
    with pytest.raises(ValueError,match="integrity mismatch"):
        read_reviewer_statements(NCT)
    inspection=client.get("/api/scientific-assessment",
                          params={"exact_id":"TRIAL|"+NCT},headers=HEADERS).json()
    assert inspection["evidenceLedgerStatus"]=="ledger_unavailable_or_invalid"
    assert inspection["registryEvidenceStatus"]=="source_record_loaded"
    assert inspection["readinessGrades"]["scientificReluctance"]["grade"]=="F"
    assert client.get("/api/scientific-assessment/review-packet/"+NCT,
                      headers=HEADERS).status_code==409
