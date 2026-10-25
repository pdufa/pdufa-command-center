"""Offline end-to-end source-review packet: integrity, isolation and no self-verification."""
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
from app.scientific_review_packet import (
    PACKET_SCHEMA_VERSION, build_review_packet, canonical_bytes,
    check_packet_integrity,
)

NCT = "NCT02142738"
OTHER = "NCT04280705"
KEY = "private-review-test-header"


def _record(nct_id):
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": "Phase 3 review pilot"},
            "designModule": {
                "studyType": "INTERVENTIONAL", "phases": ["PHASE3"],
                "enrollmentInfo": {"count": 300},
            },
            "conditionsModule": {"conditions": ["Lung cancer"]},
            "outcomesModule": {"primaryOutcomes": [{"measure": "PFS"}]},
            "statusModule": {"overallStatus": "COMPLETED"},
        },
        "hasResults": False,
    }


@pytest.fixture
def storage(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://isolated.invalid/db")
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", KEY)
    for identifier in [NCT, OTHER]:
        raw = json.dumps(_record(identifier), sort_keys=True).encode("utf-8")
        with Session(engine) as session:
            session.add(main.FullTrialRecord(
                nct_id=identifier,
                payload_gzip=gzip.compress(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                summary={"nctId": identifier}, statistics=[],
                fetched_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            ))
            session.commit()
    yield TestClient(main.app), engine
    engine.dispose()


def test_pilot_packet_has_all_review_layers_and_unresolved_acceptance_criteria(storage):
    client, engine = storage
    url = "/api/scientific-assessment/review-packet/" + NCT
    assert client.get(url).status_code == 401
    response = client.get(url, headers={"x-pdufa-internal-key": KEY})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert NCT + "_scientific_review_packet.json" in response.headers["content-disposition"]
    data = response.json()
    assert data["packetSchemaVersion"] == PACKET_SCHEMA_VERSION
    assert data["archive"]["archiveIdentityAndSha256Verified"] is True
    assert data["nctId"] == NCT
    assert data["investigation20"]["levelCount"] == 20
    assert data["assessmentStageCrosswalk"]["stageCount"] == 20
    assert data["assessmentStageCrosswalk"]["assessmentCount"] == 40
    assert data["assessmentStageCrosswalk"]["stagesWithLinkedAssessments"] == 20
    assert data["assessmentStageCrosswalk"]["independentlyVerifiedAssessments"] == 0
    assert data["assessmentStageCrosswalk"]["approvalProbability"] is None
    assert len(data["evidenceInputGrades"]["requirements"]) == 16
    assert data["evidenceInputGrades"]["analysisReadiness"]["verdict"] == "NOT_READY"
    assert data["evidenceInputGrades"]["scientificReluctance"]["grade"] == "F"
    assert data["independentSourceLedger"]["candidateCount"] == 7
    assert data["independentSourceLedger"]["entryCount"] == 0
    assert data["reconciliation"]["scope"] == "historical_pilot"
    assert data["reconciliation"]["unresolvedCount"] == 8
    assert data["reconciliation"]["independentlyResolvedCount"] == 0
    assert all(len(q["resolutionCriteria"]) >= 4 for q in data["reconciliation"]["checks"])
    assert all(not q["resolved"] and q["criteriaSatisfied"] == 0
               and q["reviewerAttestation"] is None
               for q in data["reconciliation"]["checks"])
    assert data["scientificConclusion"] is None
    assert data["scientificallyVerified"] is False
    assert data["fdaApprovalProbability"] is None
    assert data["tradingEnabled"] is False
    assert check_packet_integrity(data) is True
    assert response.headers["x-packet-sha256"] == data["packetIntegrity"]["digest"]
    assert KEY not in response.text
    with Session(engine) as session:
        assert len(session.query(main.FullTrialRecord).all()) == 2
        assert session.query(main.ScientificBatchJob).count() == 0
        assert session.query(main.ScientificEvidenceLedgerEntry).count() == 0


def test_unknown_trial_packet_has_four_generic_independent_review_gates(storage):
    client, _ = storage
    body = client.get(
        "/api/scientific-assessment/review-packet/" + OTHER,
        headers={"x-pdufa-internal-key": KEY},
    ).json()
    assert body["nctId"] == OTHER
    assert body["independentSourceLedger"]["candidateCount"] == 0
    assert body["reconciliation"]["scope"] == "unreviewed_trial"
    assert body["reconciliation"]["unresolvedCount"] == 4
    assert body["assessmentStageCrosswalk"]["stageCount"] == 20
    assert all(len(item["resolutionCriteria"]) == 3
               for item in body["reconciliation"]["checks"])
    assert body["scientificConclusion"] is None
    assert check_packet_integrity(body)


def test_packet_determinism_and_detected_payload_edits(storage):
    timestamp = datetime(2026, 10, 25, 8, 10, tzinfo=timezone.utc)
    a = build_review_packet(NCT, generated_at=timestamp)
    b = build_review_packet(NCT, generated_at=timestamp)
    assert canonical_bytes(a) == canonical_bytes(b)
    assert check_packet_integrity(a)
    a["reconciliation"]["checks"][0]["resolved"] = True
    # A misleading edited crosswalk must also invalidate the signed-contents
    # checksum, even when the registry fields themselves remain unchanged.
    a["assessmentStageCrosswalk"]["stages"][0]["independentlyVerifiedAssessments"] = 1
    assert check_packet_integrity(a) is False
    a["assessmentStageCrosswalk"]["stages"][0]["independentlyVerifiedAssessments"] = 0
    assert check_packet_integrity(a) is False
    b["packetIntegrity"]["digest"] = "0" * 64
    assert check_packet_integrity(b) is False


def test_packet_export_fails_closed_for_missing_corrupt_and_mismatched_trials(storage):
    client, engine = storage
    headers = {"x-pdufa-internal-key": KEY}
    assert client.get("/api/scientific-assessment/review-packet/NCT00000000",
                      headers=headers).status_code == 404
    with Session(engine) as session:
        row = session.get(main.FullTrialRecord, NCT)
        row.sha256 = "0" * 64
        session.commit()
    assert client.get("/api/scientific-assessment/review-packet/" + NCT,
                      headers=headers).status_code == 409
    with Session(engine) as session:
        row = session.get(main.FullTrialRecord, NCT)
        raw = json.dumps(_record(OTHER), sort_keys=True).encode()
        row.payload_gzip = gzip.compress(raw)
        row.sha256 = hashlib.sha256(raw).hexdigest()
        session.commit()
    assert client.get("/api/scientific-assessment/review-packet/" + NCT,
                      headers=headers).status_code == 409


def test_packet_fail_closed_if_source_ledger_tampered(storage, monkeypatch):
    client, engine = storage
    from app.scientific_evidence_ledger import append_candidate
    with Session(engine) as session:
        pass
    result = append_candidate(NCT, {
        "gateId": "protocol_sap",
        "sourceUrl": "https://clinicaltrials.gov/study/NCT02142738",
        "sourceType": "protocol_sap",
        "sourcePublishedAt": "2017-12-20",
        "claimText": "Source document requires formal original SAP reconciliation.",
        "relationship": "context",
        "caution": "Potential retrospective amendment timing requires independent review.",
        "recordedBy": "Offline test curator",
        "supersedesId": None,
    })
    assert result["independentlyVerified"] is False
    with Session(engine) as session:
        entry = session.get(main.ScientificEvidenceLedgerEntry, result["id"])
        entry.relationship = "supports"
        session.commit()
    response = client.get("/api/scientific-assessment/review-packet/" + NCT,
                          headers={"x-pdufa-internal-key": KEY})
    assert response.status_code == 409
    assert response.json()["detail"] == "Trial archive or source ledger failed integrity verification"


def test_strict_exact_identity(storage):
    client, _ = storage
    for invalid in ("NCT1234", "NCT042807050", "trial", "NCT00000000extra"):
        response = client.get(
            "/api/scientific-assessment/review-packet/" + invalid,
            headers={"x-pdufa-internal-key": KEY},
        )
        assert response.status_code in (404, 409, 422)
        assert "packetIntegrity" not in response.text


def test_generated_at_cannot_be_timezone_naive(storage):
    with pytest.raises(ValueError, match="timezone"):
        build_review_packet(NCT, generated_at=datetime(2026, 10, 25))
