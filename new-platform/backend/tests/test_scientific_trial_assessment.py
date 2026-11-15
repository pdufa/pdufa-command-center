from datetime import date
from copy import deepcopy
import json
import pytest
from app import assessment_runtime as runtime
from app import scientific_trial_assessment as science
from test_assessment_runtime import snapshot,engine


def source():
    frozen=snapshot();doc=json.loads(frozen['document_json']);p=doc['protocolSection']
    p['identificationModule'].update(briefTitle='Synthetic program',orgStudyIdInfo={'id':'SYNTHETIC-001'})
    p['armsInterventionsModule']={'interventions':[{'type':'DRUG','name':'Synthetic drug'}], 'armGroups':[{'label':'Synthetic active','type':'EXPERIMENTAL'},{'label':'Placebo','type':'PLACEBO_COMPARATOR'}]}
    p['designModule']['designInfo']['maskingInfo']={'masking':'DOUBLE','whoMasked':['PARTICIPANT','INVESTIGATOR']}
    doc['documents']=[{'filename':'Prot_000.pdf','hasProtocol':True},{'filename':'SAP_001.pdf','hasSap':True}]
    doc['originalDocuments']=[]
    for kind,filename in [('hasProtocol','Prot_000.pdf'),('hasSap','SAP_001.pdf')]:
        body='SYNTHETIC-001. Study design: randomized double-blind placebo control. IWRS allocation sequence. Sample size 100 participants provides 80% power. Protocol amendment version 2. Statistical analysis plan: all randomized intent-to-treat population. Missing data imputed as smoking. Multiplicity: Hochberg family-wise testing. Database lock and unblinding dates remain to be recorded.'
        doc['originalDocuments'].append({'kind':kind,'url':'https://cdn.clinicaltrials.gov/large-docs/49/NCT04576949/'+filename,
            'registeredDocumentDate':'2019-01-01','registeredUploadDate':'2019-02-01T12:00','verification':'ORIGINAL_LINKED_PDF_RETRIEVED',
            'capturedAt':'2020-01-15T12:00:00Z','sha256':'b'*64,'extractedText':body,'pages':[{'page':1,'text':body}]})
    doc['resultsSection']['outcomeMeasuresModule']['outcomeMeasures']=[{'type':'PRIMARY','title':'Synthetic smoking abstinence',
        'timeFrame':'12 weeks','populationDescription':'All randomized','unitOfMeasure':'Percentage of participants',
        'groups':[{'id':'control','title':'Placebo'},{'id':'active','title':'Synthetic active'}],
        'denoms':[{'units':'Participants','counts':[{'groupId':'control','value':'50'},{'groupId':'active','value':'50'}]}],
        'classes':[{'categories':[{'measurements':[{'groupId':'control','value':'10'},{'groupId':'active','value':'30'}]}]}],
        'analyses':[{'paramType':'Risk Ratio','paramValue':'3','ciLowerLimit':'1.1','ciUpperLimit':'7.4','pValue':'<0.01','ciPctValue':'95','statisticalMethod':'Synthetic source method'}]}]
    frozen['document_json']=runtime.packed(doc);frozen['input_sha256']=runtime.sha(doc)
    return frozen


def request(level=3,mode='CURRENT_EVIDENCE',cutoff=None):
    return runtime.RunInput(nct='NCT04576949',level=level,mode=mode,cutoffDate=cutoff,contract='SCIENTIFIC_1_3')


def revise(frozen,edit):
    result=deepcopy(frozen);doc=json.loads(result['document_json']);edit(doc)
    result['document_json']=runtime.packed(doc);result['input_sha256']=runtime.sha(doc);return result


@pytest.mark.parametrize('level',[1,2,3])
def test_selected_scientific_engine_executes_in_order_and_persists(engine,monkeypatch,level):
    calls=[]
    for number in range(1,4):
        intended=science.ENGINES[number]
        def track(*args,n=number,fn=intended):calls.append(n);return fn(*args)
        monkeypatch.setitem(science.ENGINES,number,track)
    monkeypatch.setattr(runtime,'collect_documents',lambda value,level:value)
    q=request(level);run=runtime.create(engine,q);runtime.execute(engine,run,lambda _:source())
    saved=runtime.status(engine,q.nct,run)
    assert saved['status']=='COMPLETED'
    assert calls==list(range(1,level+1))
    report=saved['report'];assert report['kind']=='EXECUTED_SCIENTIFIC_TRIAL_ASSESSMENT'
    assert report['score']['value'] is None and report['score']['kind']=='NOT_VALIDATED'
    assert report['fdaPrediction']['outcome']=='ABSTAIN'
    assert runtime.history(engine,q.nct)['runs'][0]==report


def test_design_review_has_original_source_passages_and_reports_power_assumptions():
    report=runtime.assess(request(2),source());checks={x['id']:x for x in report['checks']}
    assert checks['randomization_control']['value']['allocation']=='RANDOMIZED'
    assert checks['power_rationale']['state']=='DOCUMENT_REPORTED'
    assert checks['power_rationale']['citations'][0]['raw_sha256']=='b'*64
    assert '80% power' in checks['power_rationale']['citations'][0]['excerpt']
    assert 'not evidence of adequate power' in checks['sample_size']['explanation']
    assert '1' in report['prerequisiteAssessments']


def test_real_calculation_reported_uncertainty_and_sap_methods_are_separate():
    report=runtime.assess(request(),source());obs=report['observations'][0]['endpointEvaluations'][0]
    assert obs['calculatedContrasts'][0]['absoluteDifferencePercentagePoints']==20
    assert obs['calculatedContrasts'][0]['confidenceInterval'] is None
    assert obs['statisticalAnalyses'][0]['reported']['ciLowerLimit']=='1.1'
    assert obs['statisticalAnalyses'][0]['nominalSignificance'].startswith('NOMINAL_P_BELOW')
    checks={x['id']:x for x in report['checks']}
    assert checks['multiplicity_adjustment']['state']=='DOCUMENT_REPORTED'
    assert checks['missing_data_handling']['state']=='DOCUMENT_REPORTED'
    assert report['observations'][0]['prespecification']=='UNVERIFIED'
    assert set(report['prerequisiteAssessments'])=={'1','2'}


@pytest.mark.parametrize('mutation',[
    lambda d:d['originalDocuments'][0].update(url='https://cdn.clinicaltrials.gov/large-docs/01/NCT00000001/Prot_000.pdf'),
    lambda d:d['originalDocuments'][0].update(capturedAt='2022-01-01T00:00:00Z'),
    lambda d:d['originalDocuments'][0].update(extractedText='Wrong study NCT00000001'),
    lambda d:d['originalDocuments'][0].update(registeredUploadDate='2021-01-01T00:00'),
])
def test_incorrect_or_future_protocols_are_rejected(mutation):
    frozen=revise(source(),mutation)
    report=runtime.assess(request(2,'BLIND_HISTORICAL',date(2021,1,1)),frozen)
    assert report['rejectedEvidence']
    assert not any(d['kind']=='hasProtocol' for d in report['documentEvidence'])


def test_future_snapshot_revision_and_unknown_status_fail_closed():
    with pytest.raises(ValueError,match='leakage|chronology'):
        runtime.assess(request(3,'BLIND_HISTORICAL',date(2019,1,1)),source())
    frozen=revise(source(),lambda d:d['protocolSection']['statusModule'].update(overallStatus='UNKNOWN_STATUS'))
    report=runtime.assess(request(2),frozen)
    assert report['executionStatus']=='BLOCKED_UNVERIFIED_PHASE'


def test_early_ongoing_trial_does_not_require_completed_pivotal_results_or_public_final_sap():
    def edit(d):
        d['protocolSection']['designModule']['phases']=['PHASE1']
        d['protocolSection']['statusModule']['overallStatus']='RECRUITING'
        d['resultsSection']={};d['documents']=[];d['originalDocuments']=[]
    report=runtime.assess(request(),revise(source(),edit));checks={x['id']:x for x in report['checks']}
    assert checks['primary_endpoint_results']['state']=='NOT_YET_EXPECTED'
    assert checks['statistical_analysis_plan']['state']=='NOT_YET_EXPECTED'
    assert checks['registered_endpoints']['state']=='SOURCE_VERIFIED'


def test_ambiguous_control_or_nonpercentage_data_never_generate_fake_effects():
    for edit in [lambda e:e['groups'][0].update(title='Comparator unknown'),lambda e:e.update(unitOfMeasure='arbitrary scale')]:
        def mutate(d):edit(d['resultsSection']['outcomeMeasuresModule']['outcomeMeasures'][0])
        report=runtime.assess(request(),revise(source(),mutate))
        assert report['observations'][0]['endpointEvaluations'][0]['calculatedContrasts']==[]


def test_outcomes_and_derived_feature_injections_cannot_change_scientific_findings():
    before=source();after=revise(before,lambda d:d.update(actualFdaOutcome='KNOWN_OUTCOME_SENTINEL',cachedProbability=.99,derivedSection={'actualOutcome':'KNOWN_OUTCOME_SENTINEL'}))
    a=runtime.assess(request(),before);b=runtime.assess(request(),after)
    assert a['checks']==b['checks'] and a['observations']==b['observations']
    assert 'KNOWN_OUTCOME_SENTINEL' not in json.dumps(b)


def test_invalid_contract_and_unicode_identity_are_not_executable():
    from fastapi import HTTPException
    with pytest.raises(HTTPException):request(4).checked()
    with pytest.raises(ValueError):runtime.RunInput(nct='NCT０４５７６９４９',level=1,mode='CURRENT_EVIDENCE')


def test_mixed_active_plus_placebo_group_is_not_a_placebo_control():
    def mutate(d):
        e=d['resultsSection']['outcomeMeasuresModule']['outcomeMeasures'][0]
        e['groups'][1]['title']='6 weeks active plus 6 weeks placebo'
    report=runtime.assess(request(),revise(source(),mutate))
    assert report['observations'][0]['endpointEvaluations'][0]['calculatedContrasts'][0]['absoluteDifferencePercentagePoints']==20
    def active_only(d):
        e=d['resultsSection']['outcomeMeasuresModule']['outcomeMeasures'][0]
        e['groups'][0]['title']='6 weeks active plus 6 weeks placebo'
    assert runtime.assess(request(),revise(source(),active_only))['observations'][0]['endpointEvaluations'][0]['calculatedContrasts']==[]


def test_past_api_requires_verified_exact_decision_link_without_reading_outcome(engine):
    from sqlalchemy import text
    q=request(3,'BLIND_HISTORICAL',date(2021,1,1))
    with pytest.raises(ValueError,match='NO_VERIFIED_HISTORICAL_DECISION_LINK'):runtime.source_for(engine,q)
    with engine.begin() as c:
        c.execute(text('CREATE TABLE phase3_trial_applications(nct_id TEXT,application_id TEXT,verification_status TEXT)'))
        c.execute(text('CREATE TABLE phase3_fda_decisions(application_id TEXT,decision_date TEXT,verification_status TEXT,decision TEXT)'))
        c.execute(text("INSERT INTO phase3_trial_applications VALUES ('NCT04576949','TEST-SYNTHETIC','VERIFIED')"))
        c.execute(text("INSERT INTO phase3_fda_decisions VALUES ('TEST-SYNTHETIC','2021-02-01','VERIFIED','OUTCOME_SENTINEL_MUST_NOT_BE_READ')"))
        frozen=source()
        c.execute(text('INSERT INTO assessment_v2_sources(snapshot_id,nct_id,captured_at,published_at,source_url,raw_sha256,input_sha256,document_json) VALUES(:snapshot_id,:nct_id,:captured_at,:published_at,:source_url,:raw_sha256,:input_sha256,:document_json)'),frozen)
    selected=runtime.source_for(engine,q,lambda _:pytest.fail('Never fetch current sources for PAST'))
    assert selected['historicalTarget']['decision_date']=='2021-02-01'
    report=runtime.assess(q,selected)
    assert 'OUTCOME_SENTINEL_MUST_NOT_BE_READ' not in json.dumps(report)
    with pytest.raises(ValueError,match='NOT_PREDECISION'):runtime.source_for(engine,request(3,'BLIND_HISTORICAL',date(2021,3,1)))
    with engine.begin() as c:c.execute(text("INSERT INTO phase3_fda_decisions VALUES ('TEST-SYNTHETIC','2021-04-01','VERIFIED','SECOND_SENTINEL')"))
    with pytest.raises(ValueError,match='AMBIGUOUS_HISTORICAL_APPLICATION'):runtime.source_for(engine,q)
