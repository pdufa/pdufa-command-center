"""Synthetic presentation contracts; no prediction accuracy claims."""
from copy import deepcopy
from datetime import date

import pytest

from research.official_prediction_contract import build_prediction_output, SECTIONS
from research.prediction_v1_1_authorization import ResearchPrincipal
from research.scientific_historical_comparison import COMPARISON_FIELDS, EVENT_POLICY

CUTOFF = date(2025, 1, 1)


def current():
    return {'program_id': 'SYNTHETIC', 'application_id': 'NDA000001',
            'review_cycle': 1, 'program_family': 'SYNTHETIC_FAMILY',
            'target_date': '2025-06-01', 'horizon_date': '2025-06-01',
            'evidence_cutoff': '2025-01-01', 'event_policy': EVENT_POLICY,
            'field_sources': [], **{field: None for field in COMPARISON_FIELDS}}


def principal():
    return ResearchPrincipal('synthetic-reader', frozenset({'evidence_reader'}),
                             frozenset({'SYNTHETIC'}), True)


def observation(identity='one', value='synthetic', *, published='2024-01-01', conflicts=None):
    return {'observation_id': identity, 'program_id': 'SYNTHETIC',
            'field_id': 'SAFETY-001', 'source_url': 'https://www.fda.gov/synthetic-study',
            'document_id': 'SYNTHETIC_DOCUMENT', 'source_document_sha256': None,
            'source_role': 'PREDECISION_RESEARCH', 'published_at': published,
            'observed_at': published + 'T12:00:00Z', 'value': value,
            'conflict_ids': conflicts or [], 'uncertainty': 'Unverified synthetic fixture',
            'verification_status': 'UNVERIFIED'}


def run(observations=()):
    return build_prediction_output(principal=principal(), current=current(),
                                   historical_cases=[], observations=list(observations), cutoff=CUTOFF)


def sections(result):
    return {row['id']: row['content'] for row in result['sections']}


def test_full_architecture_and_expandable_output_remain_unvalidated():
    result = run()
    assert result['architecture']['draft_fields'] == 650
    assert result['architecture']['investigation_levels'] == 50
    assert result['architecture']['canonical_assessments'] == 40
    assert result['architecture']['historical_comparison_criteria'] == 10
    assert [(s['id'], s['title']) for s in result['sections']] == list(SECTIONS)
    assert all(s['expandable'] and not s['expanded_by_default'] for s in result['sections'])
    assert result['allowed_decisions'] == ['PASS', 'CRL', 'EXTENSION', 'ABSTAIN']
    assert result['predicted_decision'] == 'ABSTAIN'
    assert result['prediction_readiness'] == 'NOT_READY'
    assert not result['prediction_validated']
    assert result['probabilities'] == dict.fromkeys(['PASS', 'CRL', 'EXTENSION'])
    assert not result['trading_authorized'] and not result['eligible_for_validated_accuracy']


def test_readiness_is_source_availability_separate_from_confidence():
    missing, reported = run(), run([observation()])
    assert missing['evidence_readiness_grade'] == 'NO_TIMELY_EVIDENCE'
    assert reported['evidence_readiness_grade'] == 'PARTIAL_SOURCE_REPORTED'
    assert reported['prediction_confidence_grade'] == 'NOT_ESTABLISHED'
    assert reported['scientific_assessment_readiness_grade'] == 'NOT_INDEPENDENTLY_ASSESSED'
    assert reported['historical_validation_readiness_grade'] == 'NOT_VALIDATED'
    assert missing['scientific_assessment_readiness_grade'] == reported['scientific_assessment_readiness_grade']
    assert sections(reported)['confidence_uncertainty']['missing_timely_evidence_slots'] == 649
    assert sections(reported)['model_validation']['measured_performance'] is None
    assert sections(reported)['model_validation']['independently_verified_decisions'] == 0
    assert reported['scoring_architecture']['missing_data_penalty'] is None
    assert not reported['scoring_architecture']['availability_counts_are_predictive_scores']


def test_future_values_withheld_in_all_sections_and_original_inputs_preserved():
    observations = [observation(value='FUTURE_SECRET_VALUE', published='2025-02-01')]
    before = deepcopy(observations)
    result = run(observations)
    assert observations == before
    assert 'FUTURE_SECRET_VALUE' not in str(result)
    docs = sections(result)['source_documentation']
    assert docs['scientific_observations'][0]['value_withheld']
    assert not docs['original_document_authentication_established']
    assert result['evidence_readiness_grade'] == 'NO_TIMELY_EVIDENCE'


def test_conflicts_are_exposed_without_choosing_a_scientific_answer():
    result = run([observation('one', 'finding one', conflicts=['two']),
                  observation('two', 'finding two', conflicts=['one'])])
    uncertainty = sections(result)['confidence_uncertainty']
    assert uncertainty['conflicted_slots'] == 1
    safety = sections(result)['safety']
    slot = next(s for s in safety['slots'] if s['field_id'] == 'SAFETY-001')
    assert slot['conflicting_evidence']
    assert slot['assessment_result'] is None
    assert safety['risk_score'] is None
    assert result['predicted_decision'] == 'ABSTAIN'


def test_provenance_preserved_without_claiming_authentication():
    result = run([observation()])
    doc = sections(result)['source_documentation']['scientific_observations'][0]
    assert doc['source_url'] == 'https://www.fda.gov/synthetic-study'
    assert doc['source_document_sha256'] is None
    assert doc['verification_status'] == 'UNVERIFIED'


@pytest.mark.parametrize('reader', [None, {'authenticated': True},
    ResearchPrincipal('synthetic-reader', frozenset({'evidence_reader'}), frozenset({'OTHER'}), True)])
def test_authorization_preserved(reader):
    with pytest.raises(PermissionError):
        build_prediction_output(principal=reader, current=current(), historical_cases=[],
                                observations=[], cutoff=CUTOFF)


def test_self_certified_models_are_not_an_accepted_argument():
    with pytest.raises(TypeError):
        build_prediction_output(principal=principal(), current=current(), historical_cases=[],
                                observations=[], cutoff=CUTOFF, model_validated=True)


def test_source_bound_designations_and_grouped_pathway_are_displayed():
    candidate = current()
    candidate.update(regulatory_designations=['Fast Track'], regulatory_pathway='NDA')
    candidate['field_sources'] = [{
        'source_id': 'synthetic-source', 'source_url': 'https://www.fda.gov/synthetic',
        'published_on': '2024-01-01', 'available_on': '2024-01-02',
        'source_status': 'SOURCE_REPORTED',
        'fields': ['regulatory_designations', 'regulatory_pathway'], 'conflict_fields': []}]
    historical = deepcopy(candidate)
    historical.update(application_id='NDA000002', program_family='SYNTHETIC_HISTORY',
                      evidence_cutoff='2023-01-01', target_date='2023-06-01',
                      horizon_date='2023-06-01', action_events=[])
    historical['field_sources'][0].update(published_on='2022-01-01', available_on='2022-01-02')
    output = build_prediction_output(principal=principal(), current=candidate,
        historical_cases=[historical], observations=[], cutoff=CUTOFF)
    designations = sections(output)['fda_designations']
    assert len(designations['comparison_fields']) == 1
    assert designations['comparison_fields'][0]['current_value'] == ['Fast Track']
    assert designations['comparison_fields'][0]['historical_value'] == ['Fast Track']
    assert designations['grouped_comparison_criteria'][0]['criterion'] == 'regulatory_pathway'
    assert not designations['designation_implies_approval']
    assert output['predicted_decision'] == 'ABSTAIN'


def test_disease_biology_preserves_existing_bio_domain_without_similarity_claims():
    evidence = observation()
    evidence['field_id'] = 'BIO-001'
    output = run([evidence])
    biology = sections(output)['scientific_evidence']['disease_biology']
    assert len(biology['slots']) == 70
    assert all(row['field_id'].startswith('BIO-') for row in biology['slots'])
    assert biology['slots'][0]['observations'][0]['value'] == 'synthetic'
    assert biology['biological_similarity_score'] is None
    assert not biology['biological_similarity_validated']
    assert output['architecture']['historical_comparison_criteria'] == 10
