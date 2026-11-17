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

def test_stale_claim_without_run_id_is_retried(engine,monkeypatch):
    from datetime import datetime, timezone, timedelta
    monkeypatch.setattr(runtime,'collect_documents',lambda source,level:source)
    existing.import_roster(engine,roster())
    batch_id=batch456.create(engine)
    old=(datetime.now(timezone.utc)-timedelta(minutes=15)).isoformat()
    with engine.begin() as c:
        c.execute(text("""UPDATE focus_assessment_items
            SET state='RUNNING',attempts=1,run_id=NULL,updated_at=:at
            WHERE batch_id=:b AND level=4"""),{'at':old,'b':batch_id})
    result=batch456.execute(engine,batch_id,workers=1,max_items=1,collector=lambda _:snapshot())
    assert result['trials'][0]['levels']['4']['state']=='COMPLETED'
    with engine.connect() as c:
        slot=c.execute(text("""SELECT attempts,run_id FROM focus_assessment_items
            WHERE batch_id=:b AND level=4"""),{'b':batch_id}).one()
    assert slot[0]==2 and slot[1]
    assert len(runtime.history(engine,'NCT04576949',4)['runs'])==1

def test_32_trial_roster_creates_96_isolated_slots_and_bounded_six(engine,monkeypatch):
    monkeypatch.setattr(runtime,'collect_documents',lambda source,level:source)
    document=roster()
    document['members']=[
        {'nct':f'NCT{index:08d}','ticker':f'S{index}','company':f'Synthetic {index}','pdufaDate':None}
        for index in range(1,33)
    ]
    existing.import_roster(engine,document)
    batch_id=batch456.create(engine)
    with engine.connect() as c:
        assert c.execute(text('SELECT COUNT(*) FROM focus_assessment_items WHERE batch_id=:b'),
                         {'b':batch_id}).scalar()==96
    result=batch456.execute(engine,batch_id,workers=1,max_items=6,
                            collector=lambda nct:snapshot(nct=nct))
    assert result['total']==32
    assert sum(slot['state']=='COMPLETED'
               for trial in result['trials'] for slot in trial['levels'].values())==6
    with engine.connect() as c:
        assert c.execute(text("""SELECT COUNT(*) FROM focus_assessment_items
            WHERE batch_id=:b AND state='PENDING'"""),{'b':batch_id}).scalar()==90
