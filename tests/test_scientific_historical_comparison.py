"""Synthetic comparator safety regressions, never measured FDA accuracy."""
from copy import deepcopy
from datetime import date

import pytest

from research.scientific_historical_comparison import (
    COMPARISON_CRITERIA, COMPARISON_FIELDS, EVENT_POLICY, classify_fda_event, compare_historical_cases,
)

CUTOFF = date(2025, 1, 1)


def event(kind='APPROVAL', *, action='2023-10-01', published='2023-10-02',
          target='2023-11-01', revised=None):
    outcome={'APPROVAL':'PASS','COMPLETE_RESPONSE':'CRL','FORMAL_TARGET_REVISION':'EXTENSION'}.get(kind)
    label=None if outcome is None or action is None or published is None else {
        'program_id':'RESEARCH', 'outcome':outcome,
        'decision_at':action+'T12:00:00Z','source_published_at':published+'T12:00:00Z',
        'source_url':'https://www.accessdata.fda.gov/synthetic-action.pdf',
        'source_document_sha256':'a'*64,'decision_document_id':'SYNTHETIC-TEST-ONLY',
    }
    return {'kind':kind, 'action_date':action, 'public_available_on':published,
            'source_url':'https://www.accessdata.fda.gov/synthetic-action.pdf',
            'target_date':target, 'revised_target_date':revised,'decision_label':label}


def fixture():
    current={'program_id':'RESEARCH','application_id':'NDA000001','review_cycle':1,'program_family':'CURRENT',
        'target_date':'2025-06-01','horizon_date':'2025-06-01','evidence_cutoff':'2025-01-01',
        'event_policy':EVENT_POLICY,
        **{field:'Synthetic '+field for field in COMPARISON_FIELDS}}
    current['field_sources']=[{'source_id':'C-1','source_url':'https://www.sec.gov/synthetic-current.htm',
        'published_on':'2024-10-01','available_on':'2024-10-02','source_status':'SOURCE_REPORTED',
        'fields':list(COMPARISON_FIELDS),'conflict_fields':[]}]
    prior=deepcopy(current)
    prior.update(application_id='NDA000002',program_family='PAST',target_date='2023-11-01',
                 horizon_date='2023-11-01',evidence_cutoff='2023-09-01',action_events=[event()])
    prior['field_sources'][0].update(source_id='P-1',source_url='https://www.sec.gov/synthetic-past.htm',
        published_on='2023-08-01',available_on='2023-08-02')
    return current,prior


def compare(current, prior):
    return compare_historical_cases(current,[prior],cutoff=CUTOFF)


def test_matched_research_context_does_not_become_validated_similarity_or_forecast():
    current,prior=fixture(); unchanged=deepcopy((current,prior))
    result=compare(current,prior); row=result['comparisons'][0]
    assert (current,prior)==unchanged
    assert row['context_eligible'] is True
    assert row['matched_criteria']==list(COMPARISON_FIELDS)
    assert row['similarity_score'] is None and row['independently_reviewed'] is False
    assert row['eligible_for_validated_accuracy'] is row['eligible_for_predictive_training'] is False
    assert result['independently_validated_comparisons']==0
    assert result['decision_contract']['predicted_decision']=='ABSTAIN'
    assert all(p is None for p in result['decision_contract']['probabilities'].values())
    assert row['known_historical_outcome']['classification']=='PASS'


@pytest.mark.parametrize('field,value',[
    ('action_date','2025-01-01'),('action_date','2025-02-01'),
    ('public_available_on','2025-01-01'),('public_available_on','2025-02-01'),
    ('public_available_on',None),
])
def test_outcomes_not_independently_public_before_current_cutoff_are_excluded(field,value):
    current,prior=fixture();prior['action_events'][0][field]=value
    if field=='action_date':
        prior['action_events'][0]['public_available_on']='2025-02-02'
    row=compare(current,prior)['comparisons'][0]
    assert row['known_historical_outcome'] is None and row['context_eligible'] is False


def test_unknown_early_extension_does_not_select_later_published_approval():
    current,prior=fixture()
    prior['action_events']=[
        event('FORMAL_TARGET_REVISION',action='2023-09-15',published=None,revised='2024-02-01'),
        event(action='2023-10-15',published='2023-10-16',target='2024-02-01'),
    ]
    row=compare(current,prior)['comparisons'][0]
    assert row['known_historical_outcome'] is None
    assert row['exclusion_reasons']==['OUTCOME_PUBLIC_AVAILABILITY_UNKNOWN']


def test_formal_extension_and_later_approval_are_distinct_first_event_targets():
    current,prior=fixture()
    prior['action_events']=[
        event('FORMAL_TARGET_REVISION',action='2023-09-15',published='2023-09-16',revised='2024-02-01'),
        event(action='2023-10-15',published='2023-10-16',target='2024-02-01'),
    ]
    row=compare(current,prior)['comparisons'][0]
    assert row['known_historical_outcome']['classification']=='EXTENSION'
    assert row['known_historical_outcome']['revised_target_date']=='2024-02-01'
    assert row['known_historical_outcome']['independently_verified'] is False


@pytest.mark.parametrize('kind',['MISSED_TARGET','DELAY','UNRESOLVED','WITHDRAWN','REFUSE_TO_FILE'])
def test_late_or_unresolved_events_are_not_crl_or_extension(kind):
    e=event(kind,action=None,published=None)
    assert classify_fda_event(e)=='UNRESOLVED'
    current,prior=fixture();prior['action_events']=[e]
    row=compare(current,prior)['comparisons'][0]
    assert row['known_historical_outcome'] is None and not row['context_eligible']


@pytest.mark.parametrize('alteration',['missing_revision','earlier_revision','bad_source','alias','target_chain','same_day','second_final'])
def test_invalid_or_ambiguous_fda_action_claims_fail_closed(alteration):
    current,prior=fixture()
    if alteration=='missing_revision':prior['action_events']=[event('FORMAL_TARGET_REVISION')]
    elif alteration=='earlier_revision':prior['action_events']=[event('FORMAL_TARGET_REVISION',revised='2023-01-01')]
    elif alteration=='bad_source':prior['action_events'][0]['source_url']='https://fda.gov.evil.test/action.pdf'
    elif alteration=='alias':prior['action_events'][0]['kind']='NONAPPROVAL'
    elif alteration=='target_chain':prior['action_events'][0]['target_date']='2023-12-01'
    elif alteration=='same_day':prior['action_events'].append(event('COMPLETE_RESPONSE'))
    else:prior['action_events'].append(event('COMPLETE_RESPONSE',action='2023-10-02',published='2023-10-03'))
    with pytest.raises(ValueError):compare(current,prior)


def test_formal_event_after_prespecified_horizon_is_not_reassigned_to_missed_target():
    current,prior=fixture()
    prior['action_events']=[event(action='2023-11-02',published='2023-11-03')]
    row=compare(current,prior)['comparisons'][0]
    assert row['known_historical_outcome'] is None
    assert 'NO_FORMAL_ACTION_WITHIN_PRESPECIFIED_HORIZON' in row['exclusion_reasons']


def test_duplicate_review_cycle_goal_aliases_are_not_extra_historical_cases():
    current,prior=fixture(); alias=deepcopy(prior)
    alias['target_date']=alias['horizon_date']='2023-12-01'
    alias['action_events'][0]['target_date']='2023-12-01'
    with pytest.raises(ValueError,match='duplicate'):
        compare_historical_cases(current,[prior,alias],cutoff=CUTOFF)


@pytest.mark.parametrize('kind',['same_application','same_family','wrong_indication'])
def test_same_program_and_different_indication_are_excluded_from_matching_context(kind):
    current,prior=fixture()
    if kind=='same_application':prior['application_id']=current['application_id']
    elif kind=='same_family':prior['program_family']='current'
    else:prior['indication']='Different synthetic indication'
    row=compare(current,prior)['comparisons'][0]
    assert not row['context_eligible']
    assert row['exclusion_reasons']
    if kind=='wrong_indication':assert 'indication' in row['mismatched_criteria']


@pytest.mark.parametrize('alteration',['late_source','late_available','unknown_date','quarantine','rejected','missing_source'])
def test_missing_or_unavailable_features_are_unknown_not_evidence_of_difference(alteration):
    current,prior=fixture();source=prior['field_sources'][0]
    if alteration=='late_source':source.update(published_on='2023-09-02',available_on='2023-09-03')
    elif alteration=='late_available':source['available_on']='2023-09-02'
    elif alteration=='unknown_date':source['published_on']=None
    elif alteration=='quarantine':source['source_status']='QUARANTINED'
    elif alteration=='rejected':source['source_status']='REJECTED'
    else:prior['field_sources']=[]
    row=compare(current,prior)['comparisons'][0]
    assert not row['context_eligible']
    assert row['unknown_criteria']==list(COMPARISON_FIELDS)
    assert row['mismatched_criteria']==[]
    assert all(criterion['historical_value'] is None for criterion in row['criteria'])


def test_historical_features_cannot_extend_to_actual_action_day():
    current,prior=fixture();prior['action_events'][0].update(action_date='2023-08-20',public_available_on='2023-08-21')
    row=compare(current,prior)['comparisons'][0]
    assert row['known_historical_outcome'] is None
    assert 'HISTORICAL_FEATURES_NOT_PREDECISION' in row['exclusion_reasons']


def test_missing_secondary_safety_and_cmc_evidence_remains_explicit_unknown():
    current,prior=fixture()
    for field in ('secondary_endpoints','safety_findings','manufacturing_issues'):
        prior[field]=None
    row=compare(current,prior)['comparisons'][0]
    assert row['context_eligible'] is True
    assert set(row['unknown_criteria'])=={'secondary_endpoints','safety_findings','manufacturing_issues'}
    assert row['eligible_for_predictive_training'] is False


@pytest.mark.parametrize('alteration',['current_outcome','claimed_certification','cycle_bool','bad_date','unsafe_url','duplicate_source','future_feature_cutoff','unknown_field','duplicate_field','self_verified'])
def test_malformed_or_promoted_comparison_payload_is_rejected(alteration):
    current,prior=fixture()
    if alteration=='current_outcome':current['known_outcome']='APPROVAL'
    elif alteration=='claimed_certification':prior['independently_reviewed']=True
    elif alteration=='cycle_bool':prior['review_cycle']=True
    elif alteration=='bad_date':prior['target_date']='2023-02-30'
    elif alteration=='unsafe_url':prior['field_sources'][0]['source_url']='javascript:alert(1)'
    elif alteration=='duplicate_source':prior['field_sources'].append(deepcopy(prior['field_sources'][0]))
    elif alteration=='future_feature_cutoff':prior['evidence_cutoff']='2023-11-01'
    elif alteration=='unknown_field':prior['field_sources'][0]['fields']=['outcome']
    elif alteration=='duplicate_field':prior['field_sources'][0]['fields']=['indication','indication']
    else:prior['field_sources'][0]['source_status']='VERIFIED'
    with pytest.raises(ValueError):compare(current,prior)


def test_current_postcutoff_fields_do_not_leak_through_comparison_values():
    current,prior=fixture();current['field_sources'][0].update(published_on='2025-01-02',available_on='2025-01-02')
    row=compare(current,prior)['comparisons'][0]
    assert row['unknown_criteria']==list(COMPARISON_FIELDS)
    assert all(item['current_value'] is None for item in row['criteria'])


def test_case_insensitive_exact_values_and_order_independent_lists_are_descriptive_only():
    current,prior=fixture()
    current['secondary_endpoints']=['Synthetic A','Synthetic B']
    prior['secondary_endpoints']=['synthetic b','synthetic a']
    prior['clinical_phase']=prior['clinical_phase'].upper()
    row=compare(current,prior)['comparisons'][0]
    assert 'secondary_endpoints' in row['matched_criteria']
    assert 'clinical_phase' in row['matched_criteria']
    assert row['similarity_score'] is None


def test_excluded_case_cannot_expose_postdecision_values_under_a_false_feature_cutoff():
    current,prior=fixture()
    prior['action_events'][0].update(action_date='2023-08-20',public_available_on='2023-08-21')
    prior['field_sources'][0].update(published_on='2023-08-21',available_on='2023-08-21')
    row=compare(current,prior)['comparisons'][0]
    assert not row['context_eligible']
    assert all(item['historical_value'] is None for item in row['criteria'])
    assert row['excluded_sources'][0]['reason']=='AFTER_EVIDENCE_CUTOFF'


def test_excluded_future_case_cannot_expose_features_after_current_cutoff():
    current,prior=fixture()
    prior.update(evidence_cutoff='2025-03-01',target_date='2025-06-01',horizon_date='2025-06-01')
    prior['action_events']=[event(action='2025-05-01',published='2025-05-02',target='2025-06-01')]
    prior['field_sources'][0].update(published_on='2025-02-01',available_on='2025-02-01')
    row=compare(current,prior)['comparisons'][0]
    assert not row['context_eligible']
    assert all(item['historical_value'] is None for item in row['criteria'])


@pytest.mark.parametrize('url',['https://127.0.0.1/private','https://source.local/evidence','https://source.internal/evidence'])
def test_local_source_addresses_are_not_accepted_as_scientific_citations(url):
    current,prior=fixture();prior['field_sources'][0]['source_url']=url
    with pytest.raises(ValueError,match='HTTPS'):compare(current,prior)


def test_ten_transparent_criteria_and_descriptive_denominators_are_not_probabilities():
    current,prior=fixture()
    row=compare(current,prior)['comparisons'][0]
    assert len(COMPARISON_CRITERIA)==10
    assert len(row['comparison_criteria'])==10
    assert row['descriptive_agreement']['matched_criteria']==10
    assert row['descriptive_agreement']['comparable_criteria']==10
    assert row['descriptive_agreement']['matched_fraction']==1.0
    assert row['descriptive_agreement']['coverage_fraction']==1.0
    assert row['descriptive_agreement']['approval_probability'] is None
    assert row['descriptive_agreement']['clinical_similarity_validated'] is False
    assert len(row['selection_reasons'])==10
    assert all(group['scientific_equivalence_established'] is False for group in row['comparison_criteria'])


def test_missingness_does_not_create_a_mismatch_and_known_denominator_is_explicit():
    current,prior=fixture()
    for field in COMPARISON_FIELDS:
        prior[field]=None
    row=compare(current,prior)['comparisons'][0]
    agreement=row['descriptive_agreement']
    assert agreement['matched_criteria']==agreement['comparable_criteria']==0
    assert agreement['matched_fraction'] is None
    assert agreement['coverage_fraction']==0
    assert row['mismatched_criteria']==[]
    assert row['selection_status']=='EXCLUDED_PENDING_ADJUDICATION'


def test_partial_group_cannot_be_counted_as_a_fully_comparable_match():
    current,prior=fixture();prior['secondary_endpoints']=None
    row=compare(current,prior)['comparisons'][0]
    endpoints=next(group for group in row['comparison_criteria'] if group['criterion']=='endpoints')
    assert endpoints['status']=='PARTIAL_EVIDENCE'
    assert row['descriptive_agreement']['comparable_criteria']==9
    assert row['descriptive_agreement']['matched_criteria']==9
    assert row['descriptive_agreement']['matched_fraction']==1
    assert row['descriptive_agreement']['coverage_fraction']==0.9


def test_mismatched_efficacy_limits_relevance_without_inventing_equivalent_effects():
    current,prior=fixture();prior['efficacy_findings']='Different synthetic effect and uncertainty'
    row=compare(current,prior)['comparisons'][0]
    assert row['descriptive_agreement']['matched_criteria']==9
    assert row['descriptive_agreement']['comparable_criteria']==10
    assert row['descriptive_agreement']['matched_fraction']==0.9
    assert 'REPORTED_VALUES_DIFFER: efficacy_findings' in row['relevance_limitations']
    assert row['similarity_score'] is None


@pytest.mark.parametrize('side',['current','historical'])
def test_timely_contradictions_are_withheld_and_block_research_selection(side):
    current,prior=fixture()
    record=current if side=='current' else prior
    record['field_sources'][0]['conflict_fields']=['efficacy_findings']
    row=compare(current,prior)['comparisons'][0]
    assert not row['context_eligible']
    assert row['conflicted_criteria']==['efficacy_findings']
    criterion=next(item for item in row['criteria'] if item['criterion']=='efficacy_findings')
    assert criterion['status']=='CONFLICTED_EVIDENCE'
    assert criterion['current_value' if side=='current' else 'historical_value'] is None
    assert row['descriptive_agreement']['comparable_criteria']==9
    assert 'EVIDENCE_CONFLICTED: efficacy_findings' in row['relevance_limitations']


def test_future_conflict_claim_does_not_poison_timely_evidence():
    current,prior=fixture()
    future=deepcopy(prior['field_sources'][0])
    future.update(source_id='FUTURE',published_on='2023-09-02',available_on='2023-09-03',
                  conflict_fields=['efficacy_findings'])
    prior['field_sources'].append(future)
    row=compare(current,prior)['comparisons'][0]
    assert row['context_eligible']
    assert row['conflicted_criteria']==[]
    assert row['descriptive_agreement']['comparable_criteria']==10
    assert row['excluded_sources']==[{'source_id':'FUTURE','reason':'AFTER_EVIDENCE_CUTOFF'}]


@pytest.mark.parametrize('conflicts',[None,'efficacy_findings',['unknown_field'],['efficacy_findings','efficacy_findings']])
def test_malformed_or_unbound_conflict_claims_fail_closed(conflicts):
    current,prior=fixture();prior['field_sources'][0]['conflict_fields']=conflicts
    with pytest.raises(ValueError,match='source-bound'):compare(current,prior)


def test_cross_program_data_is_not_compared_under_default_scope():
    current,prior=fixture();prior['program_id']='OTHER'
    prior['action_events'][0]['decision_label']['program_id']='OTHER'
    with pytest.raises(PermissionError,match='program access denied'):compare(current,prior)


def test_server_resolved_scopes_allow_distinct_drug_programs_without_implicit_grants():
    current,prior=fixture();prior['program_id']='OTHER'
    prior['action_events'][0]['decision_label']['program_id']='OTHER'
    result=compare_historical_cases(current,[prior],cutoff=CUTOFF,
                                    authorized_program_ids=frozenset({'RESEARCH','OTHER'}))
    assert result['comparisons'][0]['context_eligible']
    assert result['comparisons'][0]['program_id']=='OTHER'
    assert result['current_program_id']=='RESEARCH'
    assert result['decision_contract']['predicted_decision']=='ABSTAIN'


@pytest.mark.parametrize('scopes',[set(['RESEARCH']),['RESEARCH'],frozenset(),frozenset({'*'}),frozenset({'OTHER'})])
def test_missing_or_mutable_scope_grants_are_rejected(scopes):
    current,prior=fixture()
    with pytest.raises((ValueError,PermissionError)):
        compare_historical_cases(current,[prior],cutoff=CUTOFF,authorized_program_ids=scopes)


def test_date_only_event_metadata_cannot_bypass_the_new_historical_label_gate():
    current,prior=fixture();prior['action_events'][0]['decision_label']=None
    assert classify_fda_event(prior['action_events'][0])=='PASS'
    row=compare(current,prior)['comparisons'][0]
    assert row['known_historical_outcome'] is None and not row['context_eligible']
    assert any(reason.startswith('HISTORICAL_LABEL_GATE:') for reason in row['exclusion_reasons'])


@pytest.mark.parametrize('alteration',[
    'date_only_decision','date_only_publication','no_hash','bad_hash','missing_document',
    'wrong_scope','wrong_outcome','wrong_source','wrong_action_day','wrong_publication_day',
    'publication_precedes_action','self_certification','malformed_outcome',
])
def test_label_provenance_or_cross_program_mismatches_block_outcome_reuse(alteration):
    current,prior=fixture();label=prior['action_events'][0]['decision_label']
    if alteration=='date_only_decision':label['decision_at']='2023-10-01'
    elif alteration=='date_only_publication':label['source_published_at']='2023-10-02'
    elif alteration=='no_hash':label['source_document_sha256']=None
    elif alteration=='bad_hash':label['source_document_sha256']='g'*64
    elif alteration=='missing_document':label['decision_document_id']=''
    elif alteration=='wrong_scope':label['program_id']='OTHER'
    elif alteration=='wrong_outcome':label['outcome']='CRL'
    elif alteration=='wrong_source':label['source_url']='https://www.accessdata.fda.gov/other.pdf'
    elif alteration=='wrong_action_day':label['decision_at']='2023-10-03T00:00:00Z'
    elif alteration=='wrong_publication_day':label['source_published_at']='2023-10-03T00:00:00Z'
    elif alteration=='publication_precedes_action':label['source_published_at']='2023-09-30T00:00:00Z'
    elif alteration=='self_certification':label['independently_verified']=True
    else:label['outcome']=[]
    row=compare(current,prior)['comparisons'][0]
    assert row['known_historical_outcome'] is None and not row['context_eligible']
    assert any(reason.startswith('HISTORICAL_LABEL_GATE:') for reason in row['exclusion_reasons'])


def test_unknown_first_event_provenance_cannot_be_replaced_with_a_later_approval():
    current,prior=fixture()
    first=event('FORMAL_TARGET_REVISION',action='2023-09-15',published='2023-09-16',revised='2024-02-01')
    first['decision_label']=None
    prior['action_events']=[first,event(action='2023-10-15',published='2023-10-16',target='2024-02-01')]
    row=compare(current,prior)['comparisons'][0]
    assert row['known_historical_outcome'] is None
    assert any(reason.startswith('HISTORICAL_LABEL_GATE:') for reason in row['exclusion_reasons'])


def test_aware_source_timestamps_are_normalized_to_utc_before_matching_event_days():
    current,prior=fixture();label=prior['action_events'][0]['decision_label']
    label['decision_at']='2023-09-30T20:00:00-04:00'  # UTC October 1.
    label['source_published_at']='2023-10-01T20:00:00-04:00'  # UTC October 2.
    row=compare(current,prior)['comparisons'][0]
    assert row['context_eligible']


def test_offset_cannot_hide_an_action_on_a_different_utc_day():
    current,prior=fixture()
    prior['action_events'][0]['decision_label']['decision_at']='2023-10-01T23:30:00-04:00'
    row=compare(current,prior)['comparisons'][0]
    assert row['known_historical_outcome'] is None
    assert any('disagrees with action_date' in reason for reason in row['exclusion_reasons'])


def test_offset_cannot_hide_publication_on_or_after_the_current_utc_cutoff():
    current,prior=fixture();prior['action_events'][0]['public_available_on']='2024-12-31'
    prior['action_events'][0]['decision_label']['source_published_at']='2024-12-31T23:30:00-04:00'
    row=compare(current,prior)['comparisons'][0]
    assert row['known_historical_outcome'] is None
    assert any('not public before current UTC cutoff' in reason for reason in row['exclusion_reasons'])
