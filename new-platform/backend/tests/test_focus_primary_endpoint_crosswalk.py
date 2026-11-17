"""Non-promoting source crosswalk regression gates with synthetic packets."""
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[3]
SPEC=importlib.util.spec_from_file_location(
    'focus_primary_crosswalk_test',ROOT/'scripts/medical/focus_primary_endpoint_crosswalk.py')
cross=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cross)
A,B='NCT00000001','NCT00000002'


def fixture(tmp_path):
    root=tmp_path/'source'
    (root/'registry-cache').mkdir(parents=True)
    state={'sources':{}}
    queue={'kind':'FOCUS_32_EXACT_NCT_SOURCE_REVIEW_QUEUE_NOT_A_PREDICTION',
           'counts':{'scientificReviewsCompleted':0,'fdaPredictionsComputed':0},
           'trials':[]}
    for nct,posted in ((A,True),(B,False)):
        regs=[{'measure':'Change from baseline','timeFrame':'week 4'},
              {'measure':'Number of treatment-emergent adverse events','timeFrame':'week 8'}] if posted else [
              {'measure':'Clinical remission','timeFrame':'week 12'}]
        pkt={'protocolSection':{'identificationModule':{'nctId':nct},
                               'outcomesModule':{'primaryOutcomes':regs}}}
        measures=[]
        if posted:
            measures=[{'type':'PRIMARY','title':'Change from baseline','timeFrame':'week 4',
                    'groups':[{'id':'OG000','title':'Drug'},{'id':'OG001','title':'Placebo'}],
                    'denoms':[{'counts':[{'groupId':'OG000','value':'10'},
                                         {'groupId':'OG001','value':'11'}]}],
                    'analyses':[{'groupIds':['OG000','OG001'],'pValue':'0.04'}]},
                    {'type':'PRIMARY','title':'Number of treatment-emergent adverse events',
                     'timeFrame':'week 8','groups':[{'id':'OG000','title':'Drug'}],
                     'denoms':[],'analyses':[]}]
            pkt['resultsSection']={'outcomeMeasuresModule':{'outcomeMeasures':measures}}
        digest=cross.canonical_sha(pkt)
        location='registry-cache/'+nct+'.json'
        (root/location).write_text(json.dumps(pkt))
        state['sources'][nct]={'versions':[{'cachePath':location,'fingerprint':digest}]}
        queue['trials'].append({'nctId':nct,'ticker':'AAA' if posted else 'BBB',
                                'registryPacketSha256':digest,
                                'registeredPrimaryOutcomeCount':len(regs),
                                'postedPrimaryOutcomeCount':len(measures)})
    (root/'ingestion-state.json').write_text(json.dumps(state))
    return root,queue


def build(tmp_path):
    root,queue=fixture(tmp_path)
    return cross.crosswalk(root,queue,expected_trials=2,expected_registered=3,
                           expected_posted=2,expected_posted_trials=1)


def test_safety_primary_and_missing_statistical_analysis_never_count_as_success(tmp_path):
    out=build(tmp_path)
    assert out['counts']['postedPrimaryMeasures']==2
    assert out['counts']['postedSafetyPrimaryMeasures']==1
    assert out['counts']['postedNonSafetyPrimaryMeasures']==1
    assert out['counts']['postedWithStatisticalComparisons']==1
    assert out['counts']['postedWithoutStatisticalComparisons']==1
    assert out['counts']['postedExactRegisteredMatch']==2
    assert out['scientificReviewsCompleted']==0
    assert out['fdaApprovalProbabilitiesComputed']==0
    safety=out['trials'][0]['postedPrimaryCrosswalk'][1]
    assert 'SAFETY_PRIMARY_DO_NOT_RECLASSIFY_AS_EFFICACY' in safety['reviewFlags']
    assert 'NO_POSTED_STATISTICAL_COMPARISON_REVIEW_SAP_AND_PUBLICATIONS' in safety['reviewFlags']
    assert all(x['scientificScore'] is None and x['fdaPrediction']=='ABSTAIN' for x in out['trials'])


def test_malformed_packet_digest_rejected(tmp_path):
    root,queue=fixture(tmp_path)
    path=root/'registry-cache'/f'{A}.json'
    pkg=json.loads(path.read_text())
    pkg['protocolSection']['identificationModule']['nctId']=B
    path.write_text(json.dumps(pkg))
    with pytest.raises(ValueError,match='packet SHA-256'):
        cross.crosswalk(root,queue,expected_trials=2,expected_registered=3,
                        expected_posted=2,expected_posted_trials=1)


def test_source_receipt_path_cannot_escape_archive(tmp_path):
    root,queue=fixture(tmp_path)
    statefile=root/'ingestion-state.json'
    s=json.loads(statefile.read_text())
    s['sources'][A]['versions'][-1]['cachePath']='registry-cache/../../escape.json'
    statefile.write_text(json.dumps(s))
    with pytest.raises(ValueError,match='Unsafe'):
        cross.crosswalk(root,queue,expected_trials=2,expected_registered=3,
                        expected_posted=2,expected_posted_trials=1)


def test_falsified_source_queue_review_claim_rejected(tmp_path):
    root,queue=fixture(tmp_path)
    queue['counts']['scientificReviewsCompleted']=1
    with pytest.raises(ValueError,match='promoted'):
        cross.crosswalk(root,queue,expected_trials=2,expected_registered=3,
                        expected_posted=2,expected_posted_trials=1)
