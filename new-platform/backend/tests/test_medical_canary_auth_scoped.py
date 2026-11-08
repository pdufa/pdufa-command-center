"""Medical pilot authentication remains independent of legacy internal keys."""
import pytest
from fastapi import HTTPException
from app import main as backend


def test_medical_scoped_key_works_without_rotating_general_auth(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "existing-backend-internal-key")
    monkeypatch.setenv("PDUFA_MEDICAL_INTERNAL_API_KEY", "separate-canary-medical-key-with-adequate-entropy")
    assert backend.require_medical_internal_key(
        "separate-canary-medical-key-with-adequate-entropy"
    ) is None
    assert backend.require_medical_internal_key("existing-backend-internal-key") is None
    with pytest.raises(HTTPException) as original:
        backend.require_internal_key(
            "separate-canary-medical-key-with-adequate-entropy"
        )
    assert original.value.status_code == 401


def test_medical_scoped_key_fails_closed(monkeypatch):
    monkeypatch.setenv("PDUFA_MEDICAL_INTERNAL_API_KEY", "isolated-medical-preview-key")
    monkeypatch.delenv("PDUFA_INTERNAL_API_KEY", raising=False)
    for candidate in [None, "incorrect"]:
        with pytest.raises(HTTPException) as ex:
            backend.require_medical_internal_key(candidate)
        assert ex.value.status_code == 401
    assert backend.require_medical_internal_key("isolated-medical-preview-key") is None
    monkeypatch.delenv("PDUFA_MEDICAL_INTERNAL_API_KEY", raising=False)
    with pytest.raises(HTTPException) as not_configured:
        backend.require_medical_internal_key("anything")
    assert not_configured.value.status_code == 503


def test_canary_routes_use_medical_only_dependency():
    import inspect
    source = inspect.getsource(backend)
    assert "install_medical_continuous_routes(app, lambda: ENGINE, require_medical_internal_key" in source
    assert "install_analyze_now_routes(app, lambda: ENGINE, require_medical_internal_key" in source
    assert 'medical-canary-preflight", dependencies=[Depends(require_medical_internal_key)]' in source
