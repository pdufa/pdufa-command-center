"""Synthetic authorization boundaries; no live source or clinical writes."""
from __future__ import annotations

import json
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import medical_reviewer_submission as intake
from app.main import require_medical_reviewer_writes


ISOLATED_SERVICE = "srv-dbntrkpsrm7s73aec3lg"
PHASE_HEADERS = {
    "X-PDUFA-Reviewer-Id": "synthetic-phase-reviewer",
    "X-PDUFA-Reviewer-Key": "P" * 40,
}
PHASE_REQUEST = {
    "sourceRunId": "11111111-1111-1111-1111-111111111111",
    "verifiedPhase": "PHASE3",
    "verifiedAt": "2026-11-08T00:00:00Z",
    "attestation": intake.PHASE_ATTESTATION,
}


@pytest.fixture
def configured_reviewers(monkeypatch):
    settings = {
        "phase": {"synthetic-phase-reviewer": "P" * 40},
        "method": {"synthetic-method-reviewer": "M" * 40},
    }
    monkeypatch.setenv("PDUFA_MEDICAL_REVIEW_WRITES_ENABLED", "true")
    monkeypatch.setenv("PDUFA_MEDICAL_REVIEWER_CREDENTIALS_JSON", json.dumps(settings))
    monkeypatch.delenv("PDUFA_MIGRATION_READ_ONLY", raising=False)
    return settings


def isolated_intake_client(monkeypatch):
    recorded = Mock()
    monkeypatch.setattr(intake.ledger, "record_verified_phase", recorded)
    app = FastAPI()
    # The production dependency has no database/test bypass. This standalone
    # fixture replaces storage only so rejected calls cannot touch a database.
    intake.install_routes(app, lambda: None, lambda: None, require_medical_reviewer_writes)
    return TestClient(app), recorded


@pytest.mark.parametrize("service_id", [None, "srv-production-test", "srv-other-preview-test"])
def test_other_services_cannot_write_even_with_reviewer_flags_and_keys(
    monkeypatch, configured_reviewers, service_id,
):
    if service_id is None:
        monkeypatch.delenv("RENDER_SERVICE_ID", raising=False)
    else:
        monkeypatch.setenv("RENDER_SERVICE_ID", service_id)
    monkeypatch.setenv("APP_ENV", "test")  # No environment-name override.
    monkeypatch.setenv("PDUFA_MEDICAL_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("PDUFA_MEDICAL_ASSESSMENT_LEDGER_ENABLED", "true")
    client, recorded = isolated_intake_client(monkeypatch)
    response = client.post(
        f"/api/internal/medical-reviewer-intake/{intake.CANARY}/phase",
        headers=PHASE_HEADERS, json=PHASE_REQUEST,
    )
    assert response.status_code == 503
    assert "isolated medical preview service" in response.json()["detail"]
    recorded.assert_not_called()


def test_correct_service_still_respects_migration_freeze(monkeypatch, configured_reviewers):
    monkeypatch.setenv("RENDER_SERVICE_ID", ISOLATED_SERVICE)
    monkeypatch.setenv("PDUFA_MIGRATION_READ_ONLY", "true")
    client, recorded = isolated_intake_client(monkeypatch)
    response = client.post(
        f"/api/internal/medical-reviewer-intake/{intake.CANARY}/phase",
        headers=PHASE_HEADERS, json=PHASE_REQUEST,
    )
    assert response.status_code == 503
    assert "migration" in response.json()["detail"]
    recorded.assert_not_called()


def test_correct_service_does_not_grant_reviewer_authority_to_read_keys(
    monkeypatch, configured_reviewers,
):
    monkeypatch.setenv("RENDER_SERVICE_ID", ISOLATED_SERVICE)
    require_medical_reviewer_writes()  # Passes only this independent service gate.
    client, recorded = isolated_intake_client(monkeypatch)
    response = client.post(
        f"/api/internal/medical-reviewer-intake/{intake.CANARY}/phase",
        headers={"X-PDUFA-Internal-Key": "synthetic-read-key"}, json=PHASE_REQUEST,
    )
    assert response.status_code == 401
    recorded.assert_not_called()


@pytest.mark.parametrize("role", intake.ROLES)
def test_non_ascii_config_is_rejected_without_digest_exception(
    monkeypatch, configured_reviewers, role,
):
    identity = next(iter(configured_reviewers[role]))
    configured_reviewers[role][identity] = "é" * 40
    monkeypatch.setenv("PDUFA_MEDICAL_REVIEWER_CREDENTIALS_JSON", json.dumps(configured_reviewers))
    with pytest.raises(HTTPException) as exc:
        intake._authenticate(identity, "synthetic-presented-key", role)
    assert exc.value.status_code == 503
    assert "é" not in exc.value.detail


@pytest.mark.parametrize("role", intake.ROLES)
def test_non_ascii_presented_key_is_unauthorized(monkeypatch, configured_reviewers, role):
    identity = next(iter(configured_reviewers[role]))
    with pytest.raises(HTTPException) as exc:
        intake._authenticate(identity, "é" * 40, role)
    assert exc.value.status_code == 401
    assert "é" not in exc.value.detail
