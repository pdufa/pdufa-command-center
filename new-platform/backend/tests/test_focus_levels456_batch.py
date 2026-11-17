"""Synthetic isolated L4–L6 FOCUS batch regressions; no real trial claims."""
import pytest
from sqlalchemy import text
from app import assessment_runtime as runtime
from app import focus_assessment_batch as existing
from app import focus_levels456_batch as batch456
from test_assessment_runtime import engine, snapshot
from test_focus_assessment_batch import roster

def test_no_roster_is_blocked(engine):
    assert batch456.summary(engine)['total'] is None
    with pytest.raises(ValueError,match='NO_RECONCILED'):
        batch456.create(engine)

def test_isolated_three_level_execution_and_idempotency(engine,monkeypatch):
    monkeypatch.setattr(runtime,'collect_documents',lambda source,level:source)
    existing.import_roster(engine,roster())
    old_id=existing.create(engine)
    new_id=batch456.create(engine)
    assert new_id!=old_id
    assert batch456.create(engine)==new_id
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM focus_assessment_items WHERE batch_id=:b"),{'b':old_id}).scalar()==3
        assert c.execute(text("SELECT COUNT(*) FROM focus_assessment_items WHERE batch_id=:b"),{'b':new_id}).scalar()==3
    result=batch456.execute(engine,new_id,workers=1,max_items=3,collector=lambda _:snapshot())
    assert result['total']==1
    slots=result['trials'][0]['levels']
    assert set(slots)=={'4','5','6'}
    assert all(slots[str(level)]['state']=='COMPLETED' for level in (4,5,6))
    assert len({slots[str(level)]['runId'] for level in (4,5,6)})==3
    for level in (4,5,6):
        report=slots[str(level)]['report']
        assert report['fdaPrediction']['outcome']=='ABSTAIN'
        assert report['fdaPrediction']['probability'] is None
        assert report['score']['kind']=='LEVEL_SPECIFIC_EVIDENCE_COVERAGE'
    batch456.execute(engine,new_id,workers=1,max_items=3,
                     collector=lambda _:pytest.fail('Completed slot must never rerun'))
    assert len(runtime.history(engine,'NCT04576949')['runs'])==3
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM focus_assessment_items WHERE batch_id=:b AND state='PENDING'"),{'b':old_id}).scalar()==3

def test_wrong_batch_identity_rejected(engine):
    existing.import_roster(engine,roster())
    old_id=existing.create(engine)
    with pytest.raises(ValueError,match='isolated'):
        batch456.execute(engine,old_id,workers=1,max_items=1,collector=lambda _:snapshot())
