import json
from datetime import datetime,timezone,timedelta
import pytest
from sqlalchemy import text
from app import focus_assessment_batch as batch,assessment_runtime as runtime
from test_assessment_runtime import engine
from test_scientific_trial_assessment import source


def roster():
    return {'sourceUrl':'https://docs.google.com/spreadsheets/d/1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU/edit#gid=202611061',
      'retrievedAt':'2026-11-15T00:00:00Z','members':[{'nct':'NCT04576949','company':'Synthetic owner fixture','ticker':'SYN','pdufaDate':None}]}


def test_empty_database_is_unknown_roster_not_zero_active_trials(engine):
    assert batch.summary(engine)['total'] is None
    with pytest.raises(ValueError,match='NO_RECONCILED'):batch.create(engine)


@pytest.mark.parametrize('mutation',[lambda x:x['members'].append(x['members'][0]),lambda x:x['members'][0].update(nct='NCT０４５７６９４９'),lambda x:x.update(sourceUrl='https://evil.test')])
def test_roster_rejects_duplicate_unicode_and_wrong_source(engine,mutation):
    doc=roster();mutation(doc)
    with pytest.raises(ValueError):batch.import_roster(engine,doc)


def test_batch_persists_three_independent_versions_and_idempotently_resumes(engine,monkeypatch):
    monkeypatch.setattr(runtime,'collect_documents',lambda s,l:s)
    digest=batch.import_roster(engine,roster());assert batch.import_roster(engine,roster())==digest
    id=batch.create(engine);assert batch.create(engine)==id
    report=batch.execute(engine,id,workers=1,max_items=3,collector=lambda _:source())
    assert report['fullyProcessed']==1 and report['total']==1
    assert all(report['counts'][str(l)]['processed']==1 and report['counts'][str(l)]['scored']==0 for l in (1,2,3))
    slots=report['trials'][0]['levels'];assert all(s['report']['mode']=='CURRENT_EVIDENCE' for s in slots.values());assert len({s['report']['runId'] for s in slots.values()})==3
    assert all(s['report']['score']['value'] is None and s['report']['fdaPrediction']['outcome']=='ABSTAIN' for s in slots.values())
    # Descriptive per-level source check counts, never a substitute score.
    for level,slot in slots.items():
        checks=runtime.history(engine,'NCT04576949',int(level))['runs'][0]['checks']
        metrics=slot['evidenceChecks']
        assert metrics['total']==len(checks) and metrics['total']>0
        assert metrics['sourceVerified']==sum(c['state']=='SOURCE_VERIFIED' for c in checks)
        assert metrics['unresolved']==len(slot['missingEvidence'])
        assert slot['report']['score']['kind']=='NOT_VALIDATED'
    repeated=batch.execute(engine,id,workers=1,max_items=3,collector=lambda _:pytest.fail('Completed slots must not run twice'))
    assert repeated['fullyProcessed']==1
    assert len(runtime.history(engine,'NCT04576949')['runs'])==3
    original=runtime.history(engine,'NCT04576949')['runs'][0];assert original['trialIdentity']['ticker']=='SYN'
    assert original['ownerRoster']['rosterId']==digest
    with engine.begin() as c:
        with pytest.raises(Exception):c.execute(text("UPDATE focus_assessment_rosters SET retrieved_at='2020-01-01'"))


def test_one_failed_level_does_not_prevent_others_and_retries_are_bounded(engine,monkeypatch):
    monkeypatch.setattr(runtime,'collect_documents',lambda s,l:s)
    batch.import_roster(engine,roster());id=batch.create(engine)
    count=0
    def collect(_):
        nonlocal count
        count+=1
        if count in (1,4):raise ValueError('Verified original unavailable')
        return source()
    first=batch.execute(engine,id,workers=1,max_items=3,collector=collect)
    assert first['counts']['1']['failed']==1 and first['counts']['2']['processed']==1 and first['counts']['3']['processed']==1
    second=batch.execute(engine,id,workers=1,max_items=3,collector=collect)
    third=batch.execute(engine,id,workers=1,max_items=3,collector=lambda _:pytest.fail('Retries exhausted'))
    assert second['trials'][0]['levels']['1']['attempts']==2 and third['fullyProcessed']==0
    assert len(runtime.history(engine,'NCT04576949')['runs'])==2


def test_save_checkpoint_gap_recovers_without_duplicate_result(engine,monkeypatch):
    monkeypatch.setattr(runtime,'collect_documents',lambda s,l:s)
    batch.import_roster(engine,roster());id=batch.create(engine)
    batch.execute(engine,id,workers=1,max_items=1,collector=lambda _:source())
    with engine.begin() as c:c.execute(text("UPDATE focus_assessment_items SET state='RUNNING' WHERE level=1"))
    batch.execute(engine,id,workers=1,max_items=1,collector=lambda _:source())
    with engine.connect() as c:assert c.execute(text('SELECT COUNT(*) FROM assessment_v2_results WHERE level=1')).scalar()==1


def test_batch_route_requires_owner_and_missing_roster_is_visible(engine):
    from fastapi import FastAPI,HTTPException
    from fastapi.testclient import TestClient
    def denied():raise HTTPException(401,'Owner required')
    def ok():return None
    app=FastAPI();app.include_router(runtime.router(lambda:engine,denied,ok,ok,allow_local=True))
    client=TestClient(app)
    assert client.get('/api/assessment-runtime/focus').status_code==401
    assert client.post('/api/assessment-runtime/focus/batch').status_code==401
    app.dependency_overrides[denied]=ok
    assert client.get('/api/assessment-runtime/focus').json()['total'] is None
    assert client.post('/api/assessment-runtime/focus/batch').status_code==409


def test_individual_reassessment_refreshes_shared_selection_and_preserves_batch_version(engine,monkeypatch):
    from test_scientific_trial_assessment import request
    monkeypatch.setattr(runtime,'collect_documents',lambda s,l:s)
    batch.import_roster(engine,roster());id=batch.create(engine)
    before=batch.execute(engine,id,workers=1,max_items=3,collector=lambda _:source())
    original=before['trials'][0]['levels']['3']['runId']
    new=runtime.create(engine,request(3));runtime.execute(engine,new,lambda _:source())
    updated=batch.summary(engine)['trials'][0]['levels']['3']
    assert updated['runId']==new and updated['report']['runId']==new
    assert len(runtime.history(engine,'NCT04576949')['runs'])==4
    with engine.connect() as c:assert c.execute(text('SELECT run_id FROM focus_assessment_items WHERE level=3')).scalar()==original
