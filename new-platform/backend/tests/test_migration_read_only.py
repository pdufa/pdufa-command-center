import pytest
from fastapi import HTTPException

from app.main import require_writes_enabled


def test_migration_write_freeze_blocks_put(monkeypatch):
    monkeypatch.setenv("PDUFA_MIGRATION_READ_ONLY", "1")
    with pytest.raises(HTTPException) as error:
        require_writes_enabled()
    assert error.value.status_code == 503


def test_migration_write_freeze_is_opt_in(monkeypatch):
    monkeypatch.delenv("PDUFA_MIGRATION_READ_ONLY", raising=False)
    assert require_writes_enabled() is None
