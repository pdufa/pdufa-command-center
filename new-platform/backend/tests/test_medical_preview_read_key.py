"""Read-only medical-preview auth is scoped to GET-only review routes."""
import pytest
from fastapi import HTTPException
from app.main import require_internal_key, require_medical_review_read_key


def test_scoped_read_key_only_grants_medical_read_not_general_internal(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "fixture-general-key")
    monkeypatch.setenv("PDUFA_MEDICAL_INTERNAL_API_KEY", "fixture-medical-worker-key")
    monkeypatch.setenv("PDUFA_MEDICAL_REVIEW_READ_KEY", "fixture-preview-read-only-key")
    assert require_medical_review_read_key("fixture-preview-read-only-key") is None
    assert require_medical_review_read_key("fixture-medical-worker-key") is None
    assert require_medical_review_read_key("fixture-general-key") is None
    with pytest.raises(HTTPException) as exc:
        require_internal_key("fixture-preview-read-only-key")
    assert exc.value.status_code == 401
    assert require_internal_key("fixture-general-key") is None
    with pytest.raises(HTTPException) as exc:
        require_medical_review_read_key("wrong-key")
    assert exc.value.status_code == 401


def test_no_key_fails_closed_and_preserves_old_clients(monkeypatch):
    monkeypatch.delenv("PDUFA_MEDICAL_REVIEW_READ_KEY", raising=False)
    monkeypatch.delenv("PDUFA_MEDICAL_INTERNAL_API_KEY", raising=False)
    monkeypatch.delenv("PDUFA_INTERNAL_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_medical_review_read_key("anything")
    assert exc.value.status_code == 503
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "old-key")
    assert require_medical_review_read_key("old-key") is None
    with pytest.raises(HTTPException) as exc:
        require_medical_review_read_key("wrong-key")
    assert exc.value.status_code == 401
