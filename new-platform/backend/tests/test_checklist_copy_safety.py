"""Exercise the real copy transaction against isolated local databases only."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, insert, inspect, select, update
from sqlalchemy.engine import make_url

SCRIPT = Path(__file__).resolve().parents[2] / "migration" / "copy_checklists.py"
spec = importlib.util.spec_from_file_location("checklist_copy_safety", SCRIPT)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


@pytest.fixture
def databases(tmp_path):
    source = create_engine("sqlite:///" + str(tmp_path / "source.sqlite3"))
    target = create_engine("sqlite:///" + str(tmp_path / "target.sqlite3"))
    migration.meta.create_all(source)
    rows = [dict(ticker="TEST", stage=stage, selections=selections,
                 notes="preserve " + stage, version=7,
                 updated_at=datetime(2026, 10, 29, 12))
            for stage, selections in [
                ("GEM_JR", {"fs": ["registry", "runway"], "fa": ["efficacy"]}),
                ("GEM", {"fs": ["efficacy"], "fa": ["gem-jr-input"]}),
            ]]
    with source.begin() as conn:
        conn.execute(insert(migration.checklists), rows)
    yield source, target
    source.dispose()
    target.dispose()


def run_copy(databases, mode="--copy"):
    source, target = databases
    urls = {"MIGRATION_SOURCE_DATABASE_URL": make_url("postgresql+psycopg://source/db"),
            "MIGRATION_TARGET_DATABASE_URL": make_url("postgresql+psycopg://target/db")}
    with patch.object(migration, "url_from_env", side_effect=urls.__getitem__), \
         patch.object(migration, "create_engine", side_effect=[source, target]), \
         patch("sys.argv", [str(SCRIPT), mode]), \
         patch.dict("os.environ", {"PDUFA_WRITE_FREEZE_CONFIRMED": "yes"}):
        migration.main()


def read(engine):
    with engine.connect() as conn:
        return migration.snapshot(conn)


def test_copy_preserves_independent_stage_settings_and_is_idempotent(databases):
    source, target = databases
    before = read(source)
    run_copy(databases)
    assert read(source) == before
    assert read(target) == before
    run_copy(databases)
    assert read(target) == before
    rows, _ = read(target)
    assert rows[0]["selections"] != rows[1]["selections"]


def test_changed_source_rolls_back_target_and_withholds_cutover(databases, capsys):
    source, target = databases
    migration.meta.create_all(target)
    original = migration.snapshot
    def snapshot_with_concurrent_source_edit(conn):
        result = original(conn)
        if conn.engine is target and result[0]:
            with source.begin() as writer:
                writer.execute(update(migration.checklists).values(notes="concurrent source edit"))
        return result
    with patch.object(migration, "snapshot", side_effect=snapshot_with_concurrent_source_edit):
        with pytest.raises(RuntimeError, match="Source changed"):
            run_copy(databases)
    assert read(target)[0] == []
    assert len(read(source)[0]) == 2
    assert "ready_for_manual_cutover" not in capsys.readouterr().out


def test_check_mode_never_creates_target_schema(databases):
    source, target = databases
    before = read(source)
    run_copy(databases, "--check")
    assert not inspect(target).has_table("checklists")
    assert read(source) == before


def test_conflicting_destination_is_never_overwritten(databases):
    source, target = databases
    migration.meta.create_all(target)
    row = dict(read(source)[0][0], notes="existing destination")
    with target.begin() as conn:
        conn.execute(insert(migration.checklists), row)
    before = read(target)
    with pytest.raises(ValueError, match="Destination already contains data"):
        run_copy(databases)
    assert read(target) == before


def test_equivalent_timestamp_offsets_have_identical_checksums():
    utc = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
    offset = utc.astimezone(timezone(timedelta(hours=-7)))
    assert migration._canonical({"updated_at": utc}) == migration._canonical({"updated_at": offset})


def test_host_case_cannot_bypass_same_database_guard():
    assert migration.is_same_database(make_url("postgresql://user@DB.EXAMPLE/db"),
                                      make_url("postgresql://other@db.example:5432/db"))
