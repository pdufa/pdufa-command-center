"""Permanent Program ID acceptance tests: stage parity, stability, WT isolation."""
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main, program_registry


@pytest.fixture
def isolated_db(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    main.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(program_registry, "ENGINE", engine)
    monkeypatch.delenv("PDUFA_MIGRATION_READ_ONLY", raising=False)
    yield engine
    engine.dispose()


def snapshot(reverse=False):
    pipeline = [
        {"id": "TRIAL|NCT00000001", "ticker": "AAA", "drug": "Drug 1"},
        {"id": "APPLICATION|AAA|PHASE3_DRUG_2", "ticker": "AAA", "drug": "Drug 2"},
        {"id": "TRIAL|NCT00000003", "ticker": "BBB", "drug": "Drug 3"},
    ]
    if reverse:
        pipeline.reverse()
    return {"pipeline": pipeline, "members": {
        "GEM_JR": {"rows": [pipeline[0]], "history": [
            {"id": "TRIAL|NCT00000001", "ticker": "AAA", "drug": "Drug 1", "cycle": 1}
        ]},
        "GEM": {"rows": [{"id": "TRIAL|NCT00000001", "ticker": "AAA", "drug": "Drug 1"}],
                "history": []},
    }}


def test_one_number_from_pipeline_through_gem_and_history(isolated_db):
    result = program_registry.number_workspace(snapshot())
    key = "TRIAL|NCT00000001"
    n = next(x["programId"] for x in result["pipeline"] if x["id"] == key)
    assert n.startswith("PDUFA-")
    assert result["members"]["GEM"]["rows"][0]["programId"] == n
    assert result["members"]["GEM_JR"]["history"][0]["programId"] == n
    assert len({r["programId"] for r in result["pipeline"]}) == 3


def test_reorder_refresh_and_new_program_cannot_renumber(isolated_db):
    original = program_registry.number_workspace(snapshot())
    numbers = {x["id"]: x["programId"] for x in original["pipeline"]}
    later = snapshot(reverse=True)
    later["pipeline"].append({"id": "TRIAL|NCT00000004", "ticker": "AAA", "drug": "Drug 4"})
    refreshed = program_registry.number_workspace(later)
    assert all(next(x["programId"] for x in refreshed["pipeline"] if x["id"] == k) == n
               for k, n in numbers.items())
    assert refreshed["pipeline"][-1]["programId"] not in numbers.values()
    with Session(isolated_db) as session:
        assert len(session.scalars(select(main.ProgramIdentity)).all()) == 4


def test_wt_tracks_two_programs_same_ticker_separately(isolated_db):
    workspace = program_registry.number_workspace(snapshot())
    a, b = [x["programId"] for x in workspace["pipeline"] if x["ticker"] == "AAA"]
    saved = main.put_program_watch_trade(main.ProgramWatchTradePayload(watch=[a], trade=[b], version=0))
    assert saved["watch"] == [a]
    assert saved["trade"] == [b]
    updated = main.put_program_watch_trade(main.ProgramWatchTradePayload(watch=[a,b], trade=[], version=1))
    assert updated["version"] == 2
    assert set(updated["watch"]) == {a,b}


def test_old_ticker_tags_survive_program_migration(isolated_db):
    program_registry.number_workspace(snapshot())
    now = datetime.now(timezone.utc)
    with Session(isolated_db) as session:
        session.add(main.WatchTrade(id=1, watch=["AAA"],trade=["BBB"],version=1,updated_at=now))
        session.commit()
    result = main.get_program_watch_trade()
    assert result["legacy"] == {"watch": ["AAA"], "trade": ["BBB"]}
    assert result["watch"] == []
    assert result["trade"] == []


def test_unknown_program_id_is_rejected(isolated_db):
    with pytest.raises(HTTPException) as exc:
        main.put_program_watch_trade(main.ProgramWatchTradePayload(watch=["PDUFA-999999"],trade=[],version=0))
    assert exc.value.status_code == 422


def test_cross_list_overlap_rejected():
    with pytest.raises(HTTPException):
        main.ProgramWatchTradePayload(watch=["PDUFA-000001"],trade=["PDUFA-000001"],version=0).canonical()


def test_stale_wt_version_conflicts(isolated_db):
    ids = [r["programId"] for r in program_registry.number_workspace(snapshot())["pipeline"]]
    main.put_program_watch_trade(main.ProgramWatchTradePayload(watch=[ids[0]],trade=[],version=0))
    with pytest.raises(HTTPException) as exc:
        main.put_program_watch_trade(main.ProgramWatchTradePayload(watch=[ids[1]],trade=[],version=7))
    assert exc.value.status_code == 409



def test_program_checklist_distinguishes_two_drugs_and_stages(isolated_db):
    payload = program_registry.number_workspace(snapshot())
    one, two = [row["programId"] for row in payload["pipeline"] if row["ticker"] == "AAA"]
    first = main.save_program_checklist(
        one,"GEM_JR",main.ChecklistPayload(notes="Drug one evidence",selections={"phase3":True},version=0)
    )
    second = main.save_program_checklist(
        two,"GEM_JR",main.ChecklistPayload(notes="Different drug",selections={},version=0)
    )
    assert first["version"] == second["version"] == 1
    assert main.read_program_checklist(one,"GEM_JR")["notes"] == "Drug one evidence"
    assert main.read_program_checklist(two,"GEM_JR")["notes"] == "Different drug"
    assert main.read_program_checklist(one,"GEM")["notes"] == ""


def test_program_notes_do_not_overwrite_legacy_ticker_checklist(isolated_db):
    workspace = program_registry.number_workspace(snapshot())
    number = workspace["pipeline"][0]["programId"]
    main.save_checklist("AAA","PIPELINE",main.ChecklistPayload(notes="Old ticker-level note",version=0))
    main.save_program_checklist(
        number,"PIPELINE",main.ChecklistPayload(notes="Specific program note",version=0)
    )
    assert main.read_checklist("AAA","PIPELINE")["notes"] == "Old ticker-level note"
    assert main.read_program_checklist(number,"PIPELINE")["notes"] == "Specific program note"


def test_repeated_numbering_does_not_write_or_revise_existing_identity_metadata(isolated_db):
    """Warm retrieval reads existing keys; new source descriptions do not upsert."""
    from sqlalchemy import event

    first = program_registry.number_workspace(snapshot())
    with Session(isolated_db) as session:
        before = [(row.id, row.source_key, row.ticker, row.drug, row.created_at)
                  for row in session.scalars(select(main.ProgramIdentity).order_by(main.ProgramIdentity.id))]
    changed = snapshot(reverse=True)
    changed["pipeline"][0].update(ticker="RENAMED", drug="Revised source description")
    writes = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(None, 1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "REPLACE"}:
            writes.append(statement)

    event.listen(isolated_db, "before_cursor_execute", capture)
    try:
        again = program_registry.number_workspace(changed)
    finally:
        event.remove(isolated_db, "before_cursor_execute", capture)
    assert writes == []
    assert {r["id"]: r["programId"] for r in first["pipeline"]} == {
        r["id"]: r["programId"] for r in again["pipeline"]}
    with Session(isolated_db) as session:
        assert before == [(row.id, row.source_key, row.ticker, row.drug, row.created_at)
                          for row in session.scalars(select(main.ProgramIdentity).order_by(main.ProgramIdentity.id))]


def test_missing_key_allocation_only_inserts_identity_and_preserves_other_state(isolated_db):
    """Numbering must not rewrite scientific, FS/FA, checklist or trading data."""
    from copy import deepcopy
    from sqlalchemy import event

    first = program_registry.number_workspace(snapshot())
    number = first["pipeline"][0]["programId"]
    now = datetime.now(timezone.utc)
    with Session(isolated_db) as session:
        session.add(main.ProgramChecklist(program_id=number, stage="GEM_JR",
            notes="Preserve source review", selections={"FS": True, "FA": False}, version=7, updated_at=now))
        session.add(main.ProgramWatchTrade(id=1, watch=[number], trade=[], version=3, updated_at=now))
        session.add(main.WatchTrade(id=1, watch=["AAA"], trade=["BBB"], version=4, updated_at=now))
        session.add(main.CandidateAssessmentHistory(exact_id="TRIAL|NCT00000001", program_id=number,
            model_version="SYNTHETIC_TEST", evidence_hash="a" * 64,
            summary={"independently_verified": False, "prediction": "ABSTAIN"}, assessed_at=now))
        session.commit()

    def nonidentity_tables():
        with isolated_db.connect() as connection:
            return {table.name: connection.execute(select(table)).fetchall()
                    for table in main.Base.metadata.sorted_tables if table.name != "program_identity"}

    before = nonidentity_tables()
    source = snapshot()
    source["pipeline"].append({"id": "TRIAL|NCT00000004", "ticker": "CCC", "drug": "New drug"})
    source["restrictions"] = {"PIPELINE": ["original"], "GEM_JR": {"FS": "original-FS", "FA": "original-FA"}}
    source["members"]["GEM_JR"]["presets"] = {"FS": ["source-FS"], "FA": ["source-FA"]}
    original_source = deepcopy(source)
    writes = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(None, 1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "REPLACE"}:
            writes.append(statement)

    event.listen(isolated_db, "before_cursor_execute", capture)
    try:
        result = program_registry.number_workspace(source)
    finally:
        event.remove(isolated_db, "before_cursor_execute", capture)
    assert writes and all(statement.lstrip().upper().startswith("INSERT INTO PROGRAM_IDENTITY ") for statement in writes)
    assert nonidentity_tables() == before
    assert source == original_source
    assert result["restrictions"] == original_source["restrictions"]
    assert result["members"]["GEM_JR"]["presets"] == original_source["members"]["GEM_JR"]["presets"]
    old_numbers = {r["id"]: r["programId"] for r in first["pipeline"]}
    assert all(row["programId"] == old_numbers[row["id"]]
               for row in result["pipeline"] if row["id"] in old_numbers)
    assert result["pipeline"][-1]["programId"] not in set(old_numbers.values())


def test_database_enforces_unique_source_keys_and_permanent_ids(isolated_db):
    from sqlalchemy.exc import IntegrityError

    source = snapshot()
    source["pipeline"].append(dict(source["pipeline"][0]))
    result = program_registry.number_workspace(source)
    assert result["pipeline"][0]["programId"] == result["pipeline"][-1]["programId"]
    with Session(isolated_db) as session:
        assert len(session.scalars(select(main.ProgramIdentity)).all()) == 3
        row = session.scalars(select(main.ProgramIdentity).order_by(main.ProgramIdentity.id)).first()
        original_id, original_key = row.id, row.source_key
    # Constraints protect the actual database, independently of importer logic.
    with Session(isolated_db) as session:
        session.add(main.ProgramIdentity(source_key=original_key, ticker="XXX", drug="Duplicate", created_at=datetime.now(timezone.utc)))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    with Session(isolated_db) as session:
        session.add(main.ProgramIdentity(id=original_id, source_key="TRIAL|DIFFERENT", ticker="XXX", drug="Duplicate", created_at=datetime.now(timezone.utc)))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        assert len(session.scalars(select(main.ProgramIdentity)).all()) == 3
