"""Optional inventory diagnostics never escape a default application lifespan."""
import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine

from app import main, full_trial_archive


@pytest.mark.parametrize("setting,expected", [(None, 0), ("0", 0), ("false", 0), ("1", 1), ("true", 1)])
def test_startup_inventory_requires_explicit_opt_in(monkeypatch, tmp_path, setting, expected):
    engine = create_engine("sqlite:///" + str(tmp_path / "startup.sqlite3"))
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "REQUIRE_POSTGRES", False)
    monkeypatch.setattr(main, "_DB_STATE", {"available": False, "reason": "STARTING"})
    monkeypatch.setenv("PDUFA_FULL_TRIAL_DOWNLOAD_BOOTSTRAP", "0")
    monkeypatch.setenv("PDUFA_RECONCILIATION_SELFTEST", "0")
    monkeypatch.setenv("PDUFA_MIGRATION_READ_ONLY", "1")
    monkeypatch.delenv("PDUFA_MIGRATION_COPY_ON_BOOT", raising=False)
    if setting is None:
        monkeypatch.delenv("PDUFA_STARTUP_FULL_SOURCE_VERIFY", raising=False)
    else:
        monkeypatch.setenv("PDUFA_STARTUP_FULL_SOURCE_VERIFY", setting)
    monkeypatch.setattr(full_trial_archive, "cleanup_retired_zip_exports", lambda: None)
    started = []
    def thread(*, target, daemon):
        return SimpleNamespace(start=lambda: started.append(target.__name__))
    monkeypatch.setattr(main, "threading", SimpleNamespace(Thread=thread))

    async def run():
        async with main.lifespan(main.app):
            assert main._DB_STATE["available"] is True
            assert main.health()["startup_source_verification_enabled"] is bool(expected)
    try:
        asyncio.run(run())
        assert started == ["verify_published_sources"] * expected
    finally:
        engine.dispose()
