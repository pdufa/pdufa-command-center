"""Synthetic registry safety regressions, never clinical/prediction accuracy."""
from copy import deepcopy
import json

import pytest

from research.scientific_evidence_registry import evaluate_registry

PROGRAM='SYNTHETIC|NCT00000000'
CUTOFF='2025-01-10T12:00:00Z'
DOMAINS=['BIO','MOA','TRIAL','EFFICACY','SAFETY','CMC','PRECEDENT','VALIDATION']


def catalog(count=3):
    counters={domain:0 for domain in DOMAINS}
    fields=[]
    for index in range(count):
        domain=DOMAINS[index % 8];counters[domain]+=1
        fields.append({'id':f'{domain}-{counters[domain]:03d}', 'segment':domain,
            'name':f'Synthetic variable {index}', 'definition':'Synthetic required source, not clinical evidence',
            'data_type':'text','applicability':'Synthetic trial fixture only','source':'Synthetic protocol',
            'scientific_rationale':'Synthetic rationale for a trust-boundary fixture',
            'assessment_ids':[f'S{1+index%40:02d}'], 'investigation_levels':[1+index%50],
            'required_source_types':['Synthetic source'], 'assessment_criteria':['Independent review required'],
            'uncertainty_handling':['Missing information stays unknown'], 'mandatory':index%2==0, 'critical':index%3==0})
    return {'schema_version':'scientific-field-catalog-v1','status':'DRAFT_DEFINITIONS_NOT_SCIENTIFICALLY_VALIDATED',
            'proposed_slots':count,'domains':[{'id':domain,'name':f'Synthetic {domain}'} for domain in DOMAINS], 'fields':fields}


def observation(identity='e1',field='BIO-001',**changes):
    record={'observation_id':identity,'program_id':PROGRAM,'field_id':field,
        'source_url':'https://www.sec.gov/Archives/synthetic-fixture.htm','document_id':'SYNTHETIC-DOCUMENT',
        'source_document_sha256':None,'source_role':'PREDECISION_RESEARCH',
        'published_at':'2025-01-02','observed_at':'2025-01-03T12:00:00Z',
        'value':'Synthetic finding, never independently validated', 'conflict_ids':[],
        'uncertainty':'Synthetic source has not been independently reviewed','verification_status':'UNVERIFIED'}
    record.update(changes)
    return record


def evaluate(observations=(),definition=None,cutoff=CUTOFF):
    return evaluate_registry(catalog() if definition is None else definition,
                             program_id=PROGRAM,cutoff=cutoff,observations=list(observations))


def test_all_650_addressable_slots_remain_missing_and_unvalidated_without_evidence():
    result=evaluate(definition=catalog(650))
    assert len(result['slots'])==result['summary']['defined_slots']==650
    assert result['summary']['missing_timely_evidence_slots']==650
    assert result['summary']['independently_verified_slots']==0
    assert result['summary']['independently_completed_assessments']==0
    assert result['summary']['applicability_exclusions']==0
    assert result['evidence_completeness_grade']=='NO_TIMELY_EVIDENCE'
    assert result['scientific_readiness_grade']=='NOT_READY'
    assert result['predicted_decision']=='ABSTAIN'
    assert result['probabilities']=={'PASS':None,'CRL':None,'EXTENSION':None}
    assert result['eligible_for_validated_accuracy'] is result['trading_authorized'] is False
    assert all(slot['assessment_result'] is None and slot['prediction_confidence'] is None for slot in result['slots'])


@pytest.mark.parametrize('value',[0,False,'Reported observation',{'effect':0},[False]])
def test_reported_presence_never_becomes_verification_or_readiness(value):
    result=evaluate([observation(value=value)])
    row=result['slots'][0]
    assert result['summary']['available_before_cutoff_slots']==1
    assert result['summary']['independently_verified_slots']==0
    assert row['completeness']=='POPULATED_SOURCE_REPORT_ONLY'
    assert row['quality_status']=='UNVERIFIED_SOURCE_REPORTS'
    assert row['verification_status']=='NOT_INDEPENDENTLY_VERIFIED'
    assert row['assessment_result'] is None
    assert row['observations'][0]['value']==value
    assert result['scientific_readiness_grade']=='NOT_READY'


@pytest.mark.parametrize('value',[None,'','   ',{},[]])
def test_empty_or_unknown_values_do_not_count_as_available(value):
    result=evaluate([observation(value=value)])
    assert result['summary']['available_before_cutoff_slots']==0
    assert result['summary']['missing_timely_evidence_slots']==3
    assert result['slots'][0]['assessment_result'] is None


def test_every_slot_populated_is_still_unverified_not_ready_and_uncalibrated():
    source=catalog()
    observations=[observation(f'e{i}',field['id']) for i,field in enumerate(source['fields'])]
    result=evaluate(observations,source)
    assert result['evidence_completeness_grade']=='SOURCE_REPORTED_FOR_ALL_DEFINED_SLOTS'
    assert result['source_quality_grade']=='NOT_INDEPENDENTLY_VERIFIED'
    assert result['calibration_status']==result['independent_validation_status']=='NOT_VALIDATED'
    assert result['prediction_confidence_grade']=='NOT_ESTABLISHED'
    assert result['scientific_readiness_grade']=='NOT_READY'


@pytest.mark.parametrize('change,classification',[
    ({'published_at':'2025-01-11T00:00:00Z'},'EXCLUDED_PUBLICATION_AFTER_CUTOFF'),
    ({'source_role':'OUTCOME_ONLY'},'EXCLUDED_OUTCOME_ONLY'),
    ({'observed_at':'2025-01-11T00:00:00Z'},'EXCLUDED_OBSERVED_AFTER_CUTOFF'),
    ({'published_at':None},'QUARANTINED_UNKNOWN_PUBLICATION'),
    ({'source_url':None},'QUARANTINED_SOURCE_IDENTITY_MISSING'),
    ({'document_id':None},'QUARANTINED_SOURCE_IDENTITY_MISSING'),
    ({'observed_at':'2025-01-01T00:00:00Z'},'QUARANTINED_OBSERVATION_BEFORE_PUBLICATION'),
])
def test_ineligible_values_are_withheld_and_not_counted(change,classification):
    record=observation(value='HINDSIGHT-SENTINEL',**change)
    result=evaluate([record]);row=result['slots'][0]
    assert not row['observations']
    assert row['excluded_or_quarantined_observations'][0]['classification']==classification
    assert row['excluded_or_quarantined_observations'][0]['value_withheld'] is True
    assert 'HINDSIGHT-SENTINEL' not in json.dumps(result)
    assert result['summary']['available_before_cutoff_slots']==0


def test_publication_date_only_does_not_prove_intraday_availability():
    record=observation(published_at='2025-01-10',observed_at='2025-01-10T11:00:00Z')
    assert evaluate([record])['summary']['available_before_cutoff_slots']==0
    assert evaluate([record],cutoff='2025-01-10')['summary']['available_before_cutoff_slots']==1


def test_conflict_is_a_reported_disagreement_not_adjudicated_negative_evidence():
    first=observation(value={'effect':1});second=observation('e2',value={'effect':-1},conflict_ids=['e1'])
    result=evaluate([first,second]);row=result['slots'][0]
    assert result['summary']['conflicted_slots']==1
    assert row['quality_status']=='CONFLICT_REPORTED_UNADJUDICATED'
    assert row['conflicting_evidence']==[{'observation_ids':['e1','e2'],'status':'REPORTED_DISAGREEMENT_NOT_ADJUDICATED'}]
    assert row['assessment_result'] is None
    assert result['predicted_decision']=='ABSTAIN'


def test_late_contrary_report_cannot_poison_the_earlier_cutoff():
    first=observation(value='Earlier source report')
    second=observation('e2',value='LATER-OUTCOME-SENTINEL',observed_at='2025-01-11T00:00:00Z',conflict_ids=['e1'])
    result=evaluate([first,second]);row=result['slots'][0]
    assert not row['conflicting_evidence']
    assert result['summary']['conflicted_slots']==0
    assert 'LATER-OUTCOME-SENTINEL' not in json.dumps(result)
    assert row['unadmitted_conflict_references'][0]['status']=='NOT_ADMITTED_AS_A_TIMELY_POPULATED_CONFLICT'


def test_later_populated_fields_do_not_improve_point_in_time_completeness():
    earlier=evaluate([observation()])
    later=observation('late',field='MOA-001',value='LATER-OUTCOME-SENTINEL',
                      observed_at='2025-01-11T00:00:00Z')
    reconstructed=evaluate([observation(),later])
    for key in ('reported_populated_slots','available_before_cutoff_slots',
                'missing_timely_evidence_slots','conflicted_slots',
                'mandatory_missing_timely_evidence_slots',
                'critical_missing_timely_evidence_slots'):
        assert reconstructed['summary'][key]==earlier['summary'][key]
    assert reconstructed['evidence_completeness_grade']==earlier['evidence_completeness_grade']
    assert reconstructed['audit_diagnostics']['submitted_populated_slots']==2
    assert reconstructed['audit_diagnostics']['eligible_for_predictive_features'] is False
    assert reconstructed['slots'][1]['audit_metadata_eligible_for_predictive_features'] is False
    assert 'LATER-OUTCOME-SENTINEL' not in json.dumps(reconstructed)


def test_outcome_only_population_is_audit_inventory_without_evidence_availability():
    result=evaluate([observation(source_role='OUTCOME_ONLY')])
    assert result['summary']['reported_populated_slots']==0
    assert result['summary']['available_before_cutoff_slots']==0
    assert result['audit_diagnostics']['submitted_populated_slots']==1
    assert result['audit_diagnostics']['append_only_audit_persisted'] is False
    assert result['audit_diagnostics']['source_document_authentication_established'] is False


def test_missing_report_does_not_establish_an_opposing_finding():
    result=evaluate([observation(),observation('e2',value=None,conflict_ids=['e1'])])
    assert result['summary']['conflicted_slots']==0
    assert result['slots'][0]['assessment_result'] is None


@pytest.mark.parametrize('change',[
    {'verification_status':'VERIFIED'}, {'verification_status':'NOT_APPLICABLE'},
    {'independently_verified':True}, {'status':'NOT_APPLICABLE'}, {'assessment_result':'PASS'},
])
def test_self_certified_verification_and_applicability_cannot_reduce_denominator(change):
    with pytest.raises(ValueError):evaluate([observation(**change)])


def test_cross_program_unknown_field_duplicate_identity_and_bad_conflict_references_rejected():
    invalids=[
        [observation(program_id='OTHER')], [observation(field='BIO-999')],
        [observation(),observation()], [observation(conflict_ids=['missing'])],
        [observation(conflict_ids=['e1'])],
        [observation(conflict_ids=['e2']),observation('e2',field='MOA-001')],
    ]
    for observations in invalids:
        with pytest.raises(ValueError):evaluate(observations)


@pytest.mark.parametrize('changes',[
    {'observed_at':'2025-01-03'}, {'published_at':'2025-02-30'},
    {'observed_at':'2025-01-03T00:00:00'}, {'source_url':'javascript:alert(1)'},
    {'source_url':'https://alice:password@example.org/paper'}, {'value':float('nan')},
    {'source_document_sha256':'invalid'}, {'source_role':'VERIFIED'},
])
def test_malformed_dates_sources_and_nonfinite_values_rejected(changes):
    with pytest.raises(ValueError):evaluate([observation(**changes)])


def test_registry_does_not_mutate_records_and_keeps_source_identity_audit_separate():
    source=catalog();records=[observation()];source_before=deepcopy(source);records_before=deepcopy(records)
    result=evaluate(records,source)
    assert source==source_before and records==records_before
    row=result['slots'][0]
    history=row['audit_history'][0]
    assert len(history['input_record_sha256'])==64
    assert history['hash_scope']=='LOCAL_INPUT_IDENTITY_NOT_SOURCE_DOCUMENT_AUTHENTICATION'
    assert row['audit_scope']=='DERIVED_REFERENCE_HISTORY_NOT_PERSISTED_LEDGER'
    result['slots'][0]['observations'][0]['value']='edited output'
    assert records==records_before


def test_catalog_cannot_claim_650_slots_while_definitions_are_missing():
    source=catalog();source['proposed_slots']=650
    with pytest.raises(ValueError,match='denominator'):evaluate(definition=source)
    source=catalog();source['fields'].append(deepcopy(source['fields'][0]));source['proposed_slots']=4
    with pytest.raises(ValueError,match='unique'):evaluate(definition=source)
    source=catalog();source['fields'][0]['assessment_ids']=['S41']
    with pytest.raises(ValueError,match='assessment'):evaluate(definition=source)
    source=catalog();source['fields'][0]['investigation_levels']=[True]
    with pytest.raises(ValueError,match='levels'):evaluate(definition=source)


def test_source_document_hash_is_identification_not_verification():
    result=evaluate([observation(source_document_sha256='a'*64)])
    row=result['slots'][0]
    assert row['observations'][0]['source_document_sha256']=='a'*64
    assert row['verification_status']=='NOT_INDEPENDENTLY_VERIFIED'
    assert result['summary']['independently_verified_slots']==0
    assert result['scientific_readiness_grade']=='NOT_READY'


def test_input_batch_order_does_not_select_the_favorable_observation_or_change_the_registry():
    observations=[observation('later',value='Contrary source',conflict_ids=['earlier']),
                  observation('earlier',value='Supporting source')]
    assert evaluate(observations)==evaluate(list(reversed(observations)))


def test_actual_scientific_catalog_integrates_without_claiming_completed_assessments():
    from research.scientific_field_catalog import build_scientific_catalog

    definitions=build_scientific_catalog()
    result=evaluate(definition=definitions)
    assert result['summary']['defined_slots']==650
    assert result['summary']['missing_timely_evidence_slots']==650
    assert result['summary']['independently_verified_slots']==0
    assert result['summary']['independently_completed_assessments']==0
    assert {row['scientific_domain'] for row in result['slots']}==set(DOMAINS)
    assert set().union(*(set(row['assessment_ids']) for row in result['slots']))=={
        f'S{number:02d}' for number in range(1,41)
    }
    assert set().union(*(set(row['investigation_levels']) for row in result['slots']))==set(range(1,51))
    assert all(row['applicability_status']=='NOT_INDEPENDENTLY_DETERMINED' for row in result['slots'])
    assert result['predicted_decision']=='ABSTAIN'


def test_actual_catalog_source_report_still_cannot_activate_predictions():
    from research.scientific_field_catalog import build_scientific_catalog

    result=evaluate([observation(field='TRIAL-001')],definition=build_scientific_catalog())
    assert result['summary']['available_before_cutoff_slots']==1
    assert result['summary']['missing_timely_evidence_slots']==649
    assert result['summary']['independently_verified_slots']==0
    assert result['calibration_status']==result['independent_validation_status']=='NOT_VALIDATED'
    assert result['scientific_readiness_grade']=='NOT_READY'
    assert result['probabilities']=={'PASS':None,'CRL':None,'EXTENSION':None}
