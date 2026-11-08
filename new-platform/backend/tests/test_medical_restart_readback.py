"""Verify restart readback only reads the saved medical canary history."""
import inspect
from app import main as backend


def test_restart_readback_is_attached_to_durable_canary_initialization():
    source = inspect.getsource(backend.lifespan)
    assert "PDUFA_MEDICAL_RESTART_READBACK status=%s" in source
    assert "read_medical_latest(ENGINE, pilot_nct)" in source
    assert "read_medical_history(ENGINE, pilot_nct)" in source
    assert 'saved.get("status") == "COMPLETE"' in source
    assert 'saved.get("completedStages") == 12' in source
    assert 'and row.get("revision") == saved.get("revision")' in source
    assert "PDUFA_MEDICAL_RESTART_READBACK status=NO_SAVED_RUN" in source
    assert "PDUFA_MEDICAL_RESTART_READBACK status=ERROR" in source

    readback = source[source.index("# Read-only, restart-time proof"):
                     source.index("except Exception as read_exc:")]
    # No additional run is created just to test persistence.
    assert "start_now(" not in readback
    assert "create_job(" not in readback
    assert "INSERT INTO" not in readback
    assert "UPDATE medical_" not in readback
