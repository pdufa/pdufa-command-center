"""Read-only reconciliation endpoint tests; no external secrets or writes."""
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app, ENGINE, ProgramIdentity
from app.reconciliation_review import ReviewPackage, validate_review_package

def _package(key):
    return {"schemaVersion": 1, "kind": "pdufa-reconciliation-review-export",
            "records": [{"programKey": "composite|example|drug|disease",
                         "status": "confirmed",
                         "evidenceUrl": "https://clinicaltrials.gov/study/NCT00000001",
                         "reviewedOn": "2026-10-22",
                         "exactSourceKey": key}]}

def test_endpoint_requires_auth(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-only-secret")
    with TestClient(app) as client:
        response = client.post("/api/reconciliation/validate", json=_package("TRIAL|TEST"))
        assert response.status_code == 401

def test_exact_identity_and_unmapped(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-only-secret")
    with TestClient(app) as client:
        with Session(ENGINE) as session:
            # Existing source identity is queried, never mutated by validator.
            key = session.query(ProgramIdentity.source_key).limit(1).scalar()
        response = client.post("/api/reconciliation/validate",
                               json=_package(key or "TRIAL|UNMAPPED_TEST"),
                               headers={"X-PDUFA-Internal-Key": "test-only-secret"})
        assert response.status_code == 200
        result = response.json()
        assert result["mode"] == "READ_ONLY_NO_QUALIFICATION_CHANGES"
        assert result["total"] == 1
        assert result["exactMatches"] == (1 if key else 0)
        assert result["unmapped"] == (0 if key else 1)

def test_invalid_evidence_rejected_without_writes():
    p = ReviewPackage.model_validate(_package("TRIAL|MISSING"))
    p.records[0].evidenceUrl = "http://insecure.example"
    result = validate_review_package(p, ENGINE, ProgramIdentity)
    assert result["invalid"] == 1


def test_malformed_ipv6_evidence_is_invalid_not_server_error():
    p = ReviewPackage.model_validate(_package("TRIAL|MISSING"))
    p.records[0].evidenceUrl = "https://[invalid-ipv6"
    result = validate_review_package(p, ENGINE, ProgramIdentity)
    assert result["invalid"] == 1
    assert result["records"][0]["outcome"] == "INVALID_EVIDENCE"
