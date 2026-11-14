from datetime import date
import json
from uuid import uuid4
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.pool import StaticPool
from app import assessment_runtime as r

@pytest.fixture
def engine():
    e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    r.initialize(e);yield e;e.dispose()

def original(nct='NCT04576949',phase='PHASE3'):
    # Explicitly synthetic observations, not clinical records or probabilities.
    return {'protocolSection':{'identificationModule':{'nctId':nct},'statusModule':{'overallStatus':'COMPLETED','lastUpdatePostDateStruct':{'date':'2020-01-01'}},'designModule':{'phases':[phase],'designInfo':{'allocation':'RANDOMIZED'},'enrollmentInfo':{'count':100}},'sponsorCollaboratorsModule':{'leadSponsor':{'name':'Synthetic sponsor'}},'conditionsModule':{'conditions':['Smoking cessation']},'eligibilityModule':{'eligibilityCriteria':'Synthetic adults'},'armsInterventionsModule':{'armGroups':[{'label':'Synthetic arm'}]},'outcomesModule':{'primaryOutcomes':[{'measure':'Smoking abstinence','timeFrame':'12 weeks'}]}},'resultsSection':{'outcomeMeasuresModule':{'outcomeMeasures':[{'type':'PRIMARY','title':'Synthetic result','analyses':[{'paramValue':'2','ciLowerLimit':'1','ciUpperLimit':'3'}]}]},'adverseEventsModule':{'description':'Synthetic safety'},'participantFlowModule':{'description':'Synthetic flow'}}}

def snapshot(nct='NCT04576949',captured='2020-02-01T00:00:00+00:00',phase='PHASE3'):
    doc=r.sanitize(original(nct,phase),nct,captured)
    return {'snapshot_id':str(uuid4()),'nct_id':nct,'captured_at':captured,'published_at':'2020-01-01','source_url':'https://clinicaltrials.gov/api/v2/studies/'+nct,'raw_sha256':'a'*64,'input_sha256':r.sha(doc),'document_json':r.packed(doc)}

def request(level,mode='CURRENT_EVIDENCE',cutoff=None):
    return r.RunInput(nct='NCT04576949',level=level,mode=mode,cutoffDate=cutoff)

@pytest.mark.parametrize('level',range(1,7))
def test_each_engine_current_persistence_retrieval(engine,level,monkeypatch):
    intended=r.ENGINES[level];calls=[]
    def track(*args):calls.append(level);return intended(*args)
    monkeypatch.setitem(r.ENGINES,level,track)
    q=request(level);run=r.create(engine,q);r.execute(engine,run,lambda _:snapshot())
    saved=r.status(engine,q.nct,run);assert calls==[level] and saved['status']=='COMPLETED'
    report=saved['report'];assert report['level']==level and report['engineVersion'].endswith('/level-'+str(level))
    assert report['fdaPrediction']['outcome']=='ABSTAIN' and report['fdaPrediction']['probability'] is None
    assert report['score']['kind']=='LEVEL_SPECIFIC_EVIDENCE_COVERAGE'
    assert r.history(engine,q.nct,level)['runs'][0]==report
    assert [x['stage'] for x in saved['progress']]==['QUEUED','RETRIEVING_CURRENT_SOURCES',f'EXECUTING_LEVEL_{level}','PERSISTING_IMMUTABLE_RESULT']
    assert r.history(engine,'NCT00000001')['runs']==[]

@pytest.mark.parametrize('level',range(1,7))
def test_historical_only_reads_pre_cutoff_snapshot(engine,level):
    # Seed immutable point-in-time fixtures directly. Current PDF collection must
    # never backdate a new retrieval to a synthetic historical capture.
    for frozen in [snapshot(),snapshot(captured='2022-02-01T00:00:00+00:00',phase='PHASE1')]:
        with engine.begin() as c:
            c.execute(text('INSERT INTO assessment_v2_sources(snapshot_id,nct_id,captured_at,published_at,source_url,raw_sha256,input_sha256,document_json) VALUES(:snapshot_id,:nct_id,:captured_at,:published_at,:source_url,:raw_sha256,:input_sha256,:document_json)'),frozen)
    q=request(level,'BLIND_HISTORICAL',date(2021,1,1));run=r.create(engine,q)
    def forbidden(_):raise AssertionError('No current sources or outcome cache allowed')
    r.execute(engine,run,forbidden);report=r.status(engine,q.nct,run)['report']
    assert report['context']['phases']==['PHASE3'] and report['evidence']['captured_at'].startswith('2020-02')
    assert report['fdaPrediction']['outcome']=='ABSTAIN' and report['historicalAccuracyEligible'] is False


def test_no_snapshot_refuses_historical_without_live_fetch(engine):
    q=request(3,'BLIND_HISTORICAL',date(2021,1,1));run=r.create(engine,q)
    r.execute(engine,run,lambda _:pytest.fail('No current call allowed'))
    state=r.status(engine,q.nct,run)
    assert state['status']=='FAILED' and 'NO_ELIGIBLE_HISTORICAL_SNAPSHOT' in state['error']
    assert state['report'] is None and r.history(engine,q.nct)['runs']==[]


def test_future_publication_and_capture_cannot_cross_cutoff(engine):
    s=snapshot(captured='2022-01-01T00:00:00+00:00');s['published_at']='2022-01-01'
    r.source_for(engine,request(1),lambda _:s)
    q=request(1,'BLIND_HISTORICAL',date(2021,1,1))
    with pytest.raises(ValueError,match='NO_ELIGIBLE'):r.source_for(engine,q)
    with pytest.raises(ValueError,match='leakage'):r.assess(q,s)


def test_outcomes_derived_features_and_wrong_nct_excluded():
    raw=original();raw.update(actualFdaOutcome='APPROVED',cachedProbability=.99,derivedSection={'approved':True})
    raw['protocolSection']['referencesModule']={'outcome':'CRL'};raw['protocolSection']['statusModule']['actualFdaOutcome']='DELAY'
    doc=r.sanitize(raw,'NCT04576949','2020-02-01T00:00:00Z')
    assert not any(x in json.dumps(doc) for x in ['APPROVED','CRL','DELAY','cachedProbability','derivedSection'])
    with pytest.raises(ValueError,match='identity'):r.sanitize(raw,'NCT00000001','2020-02-01T00:00:00Z')


def test_sources_and_results_are_database_immutable(engine):
    q=request(1);run=r.create(engine,q);r.execute(engine,run,lambda _:snapshot())
    for table in ['assessment_v2_results','assessment_v2_sources']:
        for statement in [f'DELETE FROM {table}',f'UPDATE {table} SET nct_id=\'NCT00000001\'']:
            with pytest.raises(DatabaseError):
                with engine.begin() as c:c.execute(text(statement))


def test_phase_specific_missingness_and_statistical_conflicts():
    s=snapshot(phase='PHASE1');doc=json.loads(s['document_json']);doc['protocolSection']['statusModule']['overallStatus']='RECRUITING';doc['resultsSection']={};s['document_json']=r.packed(doc);s['input_sha256']=r.sha(doc)
    report=r.assess(request(5),s);assert all(c['state']=='NOT_YET_EXPECTED' for c in report['checks'])
    s=snapshot();doc=json.loads(s['document_json']);doc['resultsSection']['outcomeMeasuresModule']['outcomeMeasures'][0]['analyses'][0]['ciLowerLimit']='4';s['document_json']=r.packed(doc);s['input_sha256']=r.sha(doc)
    assert r.assess(request(5),s)['observations'][-1]['conflicts']


def test_auth_invalid_inputs_and_postgres_guard(engine):
    def auth():raise HTTPException(401,'Owner authentication required')
    app=FastAPI();app.include_router(r.router(lambda:engine,auth,lambda:None,lambda:None,allow_local=True));client=TestClient(app)
    assert client.post('/api/assessment-runtime/runs',json=request(1).model_dump(mode='json')).status_code==401
    assert client.get('/api/assessment-runtime/history/NCT04576949').status_code==401
    app.dependency_overrides[auth]=lambda:None
    for body in [{'nct':'wrong','level':1,'mode':'CURRENT_EVIDENCE'},{'nct':'NCT04576949','level':7,'mode':'CURRENT_EVIDENCE'},{'nct':'NCT04576949','level':1,'mode':'CURRENT_EVIDENCE','score':99}]:
        assert client.post('/api/assessment-runtime/runs',json=body).status_code==422
    assert client.post('/api/assessment-runtime/runs',json=request(1,'BLIND_HISTORICAL').model_dump(mode='json')).status_code==422
    app2=FastAPI();app2.include_router(r.router(lambda:engine,lambda:None,lambda:None,lambda:None))
    assert TestClient(app2).post('/api/assessment-runtime/runs',json=request(1).model_dump(mode='json')).status_code==503


def test_sap_text_never_substitutes_for_reported_numeric_analyses():
    s=snapshot();doc=json.loads(s['document_json']);doc['resultsSection']['outcomeMeasuresModule']={}
    doc['originalDocuments']=[{'kind':'hasSap','verification':'ORIGINAL_LINKED_PDF_RETRIEVED','extractedText':'An estimand and alpha plan'}]
    s['document_json']=r.packed(doc);s['input_sha256']=r.sha(doc)
    report=r.assess(request(5),s)
    assert next(c for c in report['checks'] if c['id']=='reported_analyses')['state']=='MISSING'
    assert next(c for c in report['checks'] if c['id']=='sap_content')['state']=='AVAILABLE'


def test_empty_posted_primary_description_is_not_quantitative_result():
    s=snapshot();report=r.assess(request(3),s)
    assert next(c for c in report['checks'] if c['id']=='primary_results')['state']=='MISSING'


def test_new_document_collection_cannot_backdate_a_printed_old_date():
    s=r.collect_documents(snapshot(),4)
    assert s['captured_at'][:10]==r.now()[:10]
    q=request(4,'BLIND_HISTORICAL',date(2021,1,1))
    with pytest.raises(ValueError,match='leakage'):r.assess(q,s)


def test_nested_cached_answers_are_excluded():
    raw=original();raw['protocolSection']['designModule']['designInfo']['cachedApprovalProbability']=.99
    raw['resultsSection']['outcomeMeasuresModule']['actualFdaOutcome']='APPROVED'
    assert 'APPROVED' not in json.dumps(r.sanitize(raw,'NCT04576949','2020-02-01T00:00:00Z'))
    assert 'cachedApprovalProbability' not in json.dumps(r.sanitize(raw,'NCT04576949','2020-02-01T00:00:00Z'))


@pytest.mark.parametrize('level',range(1,7))
def test_retained_original_stream_receipts_support_historical_without_backdating_or_overwrite(engine,level):
    raw=original();run_id=str(uuid4());raw['actualFdaOutcome']='APPROVED'
    with engine.begin() as c:
        c.execute(text('CREATE TABLE nct_stream_runs(run_id TEXT PRIMARY KEY,nct_id TEXT)'))
        c.execute(text('CREATE TABLE nct_stream_sources(run_id TEXT PRIMARY KEY,source_url TEXT,sha256 TEXT,document TEXT,canonical_sha256 TEXT,verified_at TEXT)'))
        c.execute(text('INSERT INTO nct_stream_runs VALUES(:id,:nct)'),{'id':run_id,'nct':'NCT04576949'})
        c.execute(text('INSERT INTO nct_stream_sources VALUES(:id,:url,:rawsha,:doc,:sha,:at)'),{'id':run_id,'url':'https://clinicaltrials.gov/api/v2/studies/NCT04576949','rawsha':'b'*64,'doc':r.packed(raw),'sha':r.sha(raw),'at':'2020-02-01T00:00:00+00:00'})
    q=request(level,'BLIND_HISTORICAL',date(2021,1,1));source=r.source_for(engine,q,lambda _:pytest.fail('No live source'))
    report=r.assess(q,source)
    assert source['snapshot_id']=='nct-stream:'+run_id and source['captured_at'].startswith('2020-02')
    assert report['fdaPrediction']['outcome']=='ABSTAIN' and 'APPROVED' not in source['document_json']
    with engine.connect() as c:
        assert c.execute(text('SELECT document FROM nct_stream_sources')).scalar()==r.packed(raw)
