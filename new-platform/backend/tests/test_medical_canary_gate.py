"""Runtime safety checks for the isolated Analyze Now pilot; no real DB writes."""
import pytest
from fastapi import HTTPException
from app import main as backend


@pytest.mark.parametrize(
    "enabled,require_postgres,postgres_url,db_ready,initialized,expected_ready",
    [
        (False, True, True, True, True, False),
        (True, False, True, True, True, False),
        (True, True, False, True, True, False),
        (True, True, True, False, True, False),
        (True, True, True, True, False, False),
        (True, True, True, True, True, True),
    ],
)
def test_medical_canary_never_bypasses_all_readiness_checks(
    monkeypatch, enabled, require_postgres, postgres_url, db_ready, initialized, expected_ready
):
    monkeypatch.setenv("PDUFA_MEDICAL_PREVIEW_ENABLED", "true" if enabled else "false")
    monkeypatch.setattr(backend, "REQUIRE_POSTGRES", require_postgres)
    monkeypatch.setattr(
        backend, "DATABASE_URL",
        "postgresql+psycopg://unit-test/medical" if postgres_url else "sqlite:///unit-test",
    )
    monkeypatch.setitem(backend._DB_STATE, "available", db_ready)
    monkeypatch.setattr(backend.app.state, "medical_canary_initialized", initialized, raising=False)

    # The authenticated preflight and actual route dependency must agree.
    observed = backend.medical_canary_preflight()
    assert observed["enabled"] is enabled
    assert observed["persistentStorageReady"] is (
        require_postgres and postgres_url and db_ready
    )
    assert observed["sourceWorkerReady"] is expected_ready
    assert observed["fdaPredictionStatus"] == "ABSTAIN"
    assert observed["certaintyStatus"] == "NOT_VALIDATED"
    assert observed["numericalPredictionAvailable"] is False

    if expected_ready:
        assert backend.require_medical_pilot_storage() is None
    else:
        with pytest.raises(HTTPException) as err:
            backend.require_medical_pilot_storage()
        assert err.value.status_code == 503
