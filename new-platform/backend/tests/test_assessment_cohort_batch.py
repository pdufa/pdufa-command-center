"""Synthetic integration tests: these do not establish clinical assessments."""
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import assessment_runtime as runtime, assessment_cohort_batch as batch
from test_assessment_runtime import engine, snapshot
from test_scientific_trial_assessment import source


def selection(**kw):
    return batch.BatchInput(requestKey=uuid4(), population='FOCUS', scope='selected',
                            ncts=['NCT04576949'], mode='CURRENT_EVIDENCE', **kw)


def test_single_trial_persists_all_three_independent_reports_and_replays_request(engine, monkeypatch):
    monkeypatch.setattr(runtime, 'collect_documents', lambda s, l:s)
    request=selection()
    batch_id=batch.create(engine,request)
    assert batch.create(engine,request)==batch_id
    assert batch.summary(engine,batch_id)['counts']['completed']==0
    batch.execute(engine,batch_id,lambda _:source())
    result=batch.summary(engine,batch_id)
    assert result['terminal'] and result['status']=='COMPLETED'
    assert result['counts']['completed']==3 and result['counts']['scored']==0
    assert len({s['runId'] for s in result['items']})==3
    assert all(s['reportHash'] for s in result['items'])
    batch.execute(engine,batch_id,lambda _:pytest.fail('Completed reports cannot run twice'))
    assert len(runtime.history(engine,'NCT04576949')['runs'])==3
    changed=request.model_copy(update={'levels':[1]})
    with pytest.raises(ValueError,match='different assessment'):batch.create(engine,changed)
    with engine.begin() as c:
        with pytest.raises(Exception):c.execute(text('DELETE FROM assessment_cohort_batches'))


def test_entire_focus_is_frozen_and_paginates_past_fifty_without_partial_submissions(engine, monkeypatch):
    from app import focus_assessment_batch as focus
    members=[{'nct':f'NCT{i:08d}','ticker':'SYN','company':'Synthetic fixture'} for i in range(1,62)]
    saved={'members':members,'authority_status':'SYNTHETIC_FIXTURE','source_url':'https://example.test/fixture',
           'retrieved_at':'2026-11-14','roster_id':'fixture'}
    monkeypatch.setattr(focus,'roster',lambda _:saved)
    first=batch.inventory_page(engine,'FOCUS',limit=50)
    second=batch.inventory_page(engine,'FOCUS',offset=first['nextOffset'],limit=50)
    assert first['total']==61 and len(first['records'])==50 and len(second['records'])==11
    request=batch.BatchInput(requestKey=uuid4(),population='FOCUS',scope='all',mode='CURRENT_EVIDENCE',inventoryHash=first['inventoryHash'])
    bid=batch.create(engine,request)
    assert batch.summary(engine,bid)['totalItems']==183
    members.append({'nct':'NCT00000062','ticker':'SYN','company':'Synthetic fixture'})
    assert batch.summary(engine,bid)['totalTrials']==61
    with pytest.raises(ValueError,match='inventory changed'):batch.create(engine,request.model_copy(update={'requestKey':uuid4()}))


def test_past_means_actual_event_queue_not_old_completed_registry_trials(engine):
    inv=batch.inventory(engine,'HISTORICAL')
    source_file=Path(__file__).resolve().parents[2]/'frontend/data/level4BlindAssessmentQueue20261112.json'
    events=json.loads(source_file.read_text())['historical2026']
    assert {r['key'] for r in inv['records']}=={r['eventKey'] for r in events}
    assert inv['total']==len(events)==20 and inv['blocked']==20
    request=batch.BatchInput(requestKey=uuid4(),population='HISTORICAL',scope='all',mode='BLIND_HISTORICAL',inventoryHash=inv['inventoryHash'])
    bid=batch.create(engine,request)
    batch.execute(engine,bid,lambda _:pytest.fail('Unlinked past event must not retrieve current sources'))
    result=batch.summary(engine,bid)
    assert result['counts']['blocked']==60 and result['counts']['completed']==0
    assert result['terminal'] and not result['canResume']
    assert all(s['nct'] is None for s in result['items'])
    with engine.connect() as c:assert c.execute(text('SELECT COUNT(*) FROM assessment_v2_jobs')).scalar()==0


def test_missing_predecision_source_blocks_single_past_and_never_uses_current_evidence(engine):
    request=batch.BatchInput(requestKey=uuid4(),population='HISTORICAL',scope='selected',ncts=['NCT04576949'],
                            mode='BLIND_HISTORICAL',cutoffDate=date(2021,1,1))
    bid=batch.create(engine,request)
    batch.execute(engine,bid,lambda _:pytest.fail('Historical run cannot retrieve current sources'))
    report=batch.summary(engine,bid)
    assert report['counts']['blocked']==3 and report['counts']['completed']==0
    assert all('NO_VERIFIED_HISTORICAL_DECISION_LINK' in s['error'] for s in report['items'])


def test_interrupted_checkpoint_recovers_original_report_and_only_unfinished_work_runs(engine,monkeypatch):
    monkeypatch.setattr(runtime,'collect_documents',lambda s,l:s)
    bid=batch.create(engine,selection())
    batch.execute(engine,bid,lambda _:source())
    saved=batch.summary(engine,bid)
    with engine.begin() as c:
        c.execute(text("UPDATE assessment_cohort_items SET state='RUNNING' WHERE batch_id=:b"),{'b':bid})
    batch.execute(engine,bid,lambda _:pytest.fail('Saved immutable reports recover without duplicate execution'))
    assert batch.summary(engine,bid)['counts']['completed']==3
    assert [s['runId'] for s in batch.summary(engine,bid)['items']]==[s['runId'] for s in saved['items']]


def test_an_active_lease_rejects_simultaneous_resume_and_failed_retries_are_bounded(engine,monkeypatch):
    bid=batch.create(engine,selection())
    with engine.begin() as c:
        c.execute(text('UPDATE assessment_cohort_workers SET lease_id=:l,lease_until=:until WHERE batch_id=:b'),
                  {'b':bid,'l':str(uuid4()),'until':(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()})
    batch.execute(engine,bid,lambda _:pytest.fail('Second worker cannot claim an active lease'))
    assert batch.summary(engine,bid)['counts']['pending']==3
    with engine.begin() as c:c.execute(text('UPDATE assessment_cohort_workers SET lease_until=NULL'))
    def missing(_):raise ValueError('Synthetic source unavailable')
    batch.execute(engine,bid,missing)
    assert batch.summary(engine,bid)['counts']['failed']==3
    batch.execute(engine,bid,missing)
    result=batch.summary(engine,bid)
    assert result['terminal'] and all(i['attempts']==2 for i in result['items'])
    batch.execute(engine,bid,lambda _:pytest.fail('Attempts exhausted'))


def test_whole_focus_results_share_existing_focus_summary_without_changing_membership(engine,monkeypatch):
    from app.focus_assessment_batch import summary
    inv=batch.inventory(engine,'FOCUS')
    request=batch.BatchInput(requestKey=uuid4(),population='FOCUS',scope='all',mode='CURRENT_EVIDENCE',levels=[1],inventoryHash=inv['inventoryHash'])
    bid=batch.create(engine,request)
    assert summary(engine)['total']==32
    assert summary(engine)['source']['authority_status']=='DATED_PACKAGED_OWNER_INVENTORY_NOT_LIVE_SHEET_RECONCILIATION'
    assert len(batch.summary(engine,bid)['items'])==32
    with engine.connect() as c:assert not __import__('sqlalchemy').inspect(c).has_table('focus_assessment_rosters')


def test_corrupt_checkpoint_or_saved_report_is_never_counted_completed(engine,monkeypatch):
    bid=batch.create(engine,selection())
    with engine.begin() as c:c.execute(text("UPDATE assessment_cohort_items SET nct_id='NCT00000001' WHERE level=1"))
    with pytest.raises(HTTPException,match='identity mismatch'):batch.summary(engine,bid)


def test_a_completed_checkpoint_without_a_persisted_report_never_counts_as_completion(engine):
    bid=batch.create(engine,selection())
    with engine.begin() as c:c.execute(text("UPDATE assessment_cohort_items SET state='COMPLETED' WHERE level=1"))
    result=batch.summary(engine,bid)
    assert result['counts']['completed']==0 and result['counts']['failed']==1
    assert result['items'][0]['reportHash'] is None


def test_batch_routes_require_owner_storage_and_write_authorization(engine,monkeypatch):
    def denied():raise HTTPException(401,'Owner required')
    def ok():pass
    app=FastAPI();app.include_router(runtime.router(lambda:engine,denied,ok,ok,allow_local=True))
    client=TestClient(app)
    assert client.get('/api/assessment-runtime/cohort-inventory').status_code==401
    assert client.post('/api/assessment-runtime/batches',json=selection().model_dump(mode='json')).status_code==401
    app.dependency_overrides[denied]=ok
    assert client.get('/api/assessment-runtime/cohort-inventory?population=FOCUS').json()['total']==32
    assert client.get('/api/assessment-runtime/batches').json()['batches']==[]
    assert client.post('/api/assessment-runtime/batches',json={**selection().model_dump(mode='json'),'score':100}).status_code==422
    monkeypatch.setattr(runtime,'collect_registry',lambda _:source())
    monkeypatch.setattr(batch,'execute',lambda *a:None)
    created=client.post('/api/assessment-runtime/batches',json=selection().model_dump(mode='json'))
    assert created.status_code==202
    bid=created.json()['batchId']
    assert client.get('/api/assessment-runtime/batches/'+bid).json()['totalItems']==3
    assert client.post('/api/assessment-runtime/batches/'+bid+'/resume').status_code==202
    app.dependency_overrides.clear()
    assert client.post('/api/assessment-runtime/batches/'+bid+'/resume').status_code==401


def test_eligible_whole_past_executes_each_level_from_original_snapshots_without_reading_answers(engine,monkeypatch,tmp_path):
    event='SYN|2021-02-01|synthetic'
    (tmp_path/'assessment_past_inventory.json').write_text(json.dumps({'asOf':'2021-02-02','source':'SYNTHETIC_TEST_ONLY',
        'events':[{'eventKey':event,'ticker':'SYN','queueDate':'2021-02-01'}]}))
    monkeypatch.setattr(batch,'DATA',tmp_path)
    batch.initialize(engine)
    with engine.begin() as c:
        c.execute(text('CREATE TABLE phase3_evidence(evidence_id TEXT,url TEXT,sha256 TEXT,verification_status TEXT)'))
        c.execute(text('CREATE TABLE phase3_trial_applications(nct_id TEXT,application_id TEXT,evidence_id TEXT,verification_status TEXT)'))
        c.execute(text('CREATE TABLE phase3_fda_decisions(application_id TEXT,decision_date TEXT,verification_status TEXT,decision TEXT)'))
        c.execute(text("INSERT INTO phase3_evidence VALUES('SYNTHETIC','https://example.test/fixture',:hash,'VERIFIED')"),{'hash':'a'*64})
        c.execute(text("INSERT INTO phase3_trial_applications VALUES('NCT04576949','SYNTHETIC','SYNTHETIC','VERIFIED')"))
        c.execute(text("INSERT INTO phase3_fda_decisions VALUES('SYNTHETIC','2021-02-01','VERIFIED','ANSWER_SENTINEL_NEVER_AN_INPUT')"))
        c.execute(text('INSERT INTO assessment_past_event_links VALUES(:event,\'NCT04576949\',\'SYNTHETIC\',\'https://example.test/fixture\',:hash,\'2021-02-02\')'),{'event':event,'hash':'a'*64})
        c.execute(text('INSERT INTO assessment_v2_sources VALUES(:snapshot_id,:nct_id,:captured_at,:published_at,:source_url,:raw_sha256,:input_sha256,:document_json)'),source())
    inv=batch.inventory(engine,'HISTORICAL')
    assert inv['blocked']==0 and inv['records'][0]['cutoffDate']=='2021-01-02'
    bid=batch.create(engine,batch.BatchInput(requestKey=uuid4(),population='HISTORICAL',scope='all',mode='BLIND_HISTORICAL',inventoryHash=inv['inventoryHash']))
    batch.execute(engine,bid,lambda _:pytest.fail('Historical whole list never fetches current sources'))
    result=batch.summary(engine,bid)
    assert result['counts']['completed']==3 and result['counts']['scored']==0
    assert 'ANSWER_SENTINEL' not in json.dumps(result)
    assert all(r['mode']=='BLIND_HISTORICAL' and r['cutoffDate']=='2021-01-02' for r in runtime.history(engine,'NCT04576949')['runs'])
