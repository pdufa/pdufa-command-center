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



def test_program_checklist_distinguishes_drugs_in_active_pipeline_and_preserves_gem_archives(isolated_db):
    payload = program_registry.number_workspace(snapshot())
    one, two = [row["programId"] for row in payload["pipeline"] if row["ticker"] == "AAA"]
    first = main.save_program_checklist(
        one,"PIPELINE",main.ChecklistPayload(notes="Drug one evidence",selections={"phase3":True},version=0)
    )
    second = main.save_program_checklist(
        two,"PIPELINE",main.ChecklistPayload(notes="Different drug",selections={},version=0)
    )
    assert first["version"] == second["version"] == 1
    assert main.read_program_checklist(one,"PIPELINE")["notes"] == "Drug one evidence"
    assert main.read_program_checklist(two,"PIPELINE")["notes"] == "Different drug"
    assert main.read_program_checklist(one,"GEM_JR")["notes"] == ""
    assert main.read_program_checklist(one,"GEM")["notes"] == ""
    for stage in ("GEM_JR","GEM"):
        with pytest.raises(HTTPException) as exc:
            main.save_program_checklist(
                one,stage,main.ChecklistPayload(notes="Must not create new stage",version=0)
            )
        assert exc.value.status_code == 410


def test_program_notes_do_not_overwrite_legacy_ticker_checklist(isolated_db):
    workspace = program_registry.number_workspace(snapshot())
    number = workspace["pipeline"][0]["programId"]
    main.save_checklist("AAA","PIPELINE",main.ChecklistPayload(notes="Old ticker-level note",version=0))
    main.save_program_checklist(
        number,"PIPELINE",main.ChecklistPayload(notes="Specific program note",version=0)
    )
    assert main.read_checklist("AAA","PIPELINE")["notes"] == "Old ticker-level note"
    assert main.read_program_checklist(number,"PIPELINE")["notes"] == "Specific program note"
