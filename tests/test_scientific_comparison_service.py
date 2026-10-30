"""Synthetic integration cases exercise gates, never FDA prediction accuracy."""
from copy import deepcopy
from datetime import date
from unittest.mock import patch

import pytest

from research.prediction_v1_1_authorization import ResearchPrincipal
from research.scientific_comparison_service import (
    build_candidate_research_assessment, build_registry_candidate_research_assessment,
)
from research.scientific_field_catalog import build_scientific_catalog
from research.scientific_historical_comparison import COMPARISON_FIELDS, EVENT_POLICY
from research.historical_decision_registry import build_historical_registry, DEFAULT_PROGRAM

CUTOFF = date(2025, 1, 1)


def cases():
    current = {
        'program_id': 'CURRENT_SCOPE', 'application_id': 'NDA000001',
        'review_cycle': 1, 'program_family': 'SYNTHETIC_CURRENT',
        'target_date': '2025-06-01', 'horizon_date': '2025-06-01',
        'evidence_cutoff': CUTOFF.isoformat(), 'event_policy': EVENT_POLICY,
        **{field: 'Synthetic ' + field for field in COMPARISON_FIELDS},
        'field_sources': [{
            'source_id': 'SYNTHETIC_CURRENT_SOURCE',
            'source_url': 'https://www.sec.gov/synthetic-current.htm',
            'published_on': '2024-01-01', 'available_on': '2024-01-02',
            'source_status': 'SOURCE_REPORTED', 'fields': list(COMPARISON_FIELDS),
            'conflict_fields': [],
        }],
    }
    historical = deepcopy(current)
    historical.update(program_id='HISTORICAL_SCOPE', application_id='NDA000002',
                      program_family='SYNTHETIC_HISTORY', target_date='2023-11-01',
                      horizon_date='2023-11-01', evidence_cutoff='2023-09-01')
    historical['field_sources'][0].update(source_id='SYNTHETIC_PAST_SOURCE',
                                         published_on='2023-08-01', available_on='2023-08-02')
    historical['action_events'] = [{
        'kind': 'APPROVAL', 'action_date': '2023-10-01',
        'public_available_on': '2023-10-02', 'target_date': '2023-11-01',
        'revised_target_date': None,
        'source_url': 'https://www.accessdata.fda.gov/synthetic-action.pdf',
        'decision_label': {
            'program_id': 'HISTORICAL_SCOPE', 'outcome': 'PASS',
            'decision_at': '2023-10-01T12:00:00Z',
            'source_published_at': '2023-10-02T12:00:00Z',
            'source_url': 'https://www.accessdata.fda.gov/synthetic-action.pdf',
            'source_document_sha256': 'a' * 64,
            'decision_document_id': 'SYNTHETIC_DOCUMENT_NOT_EVIDENCE',
        },
    }]
    return current, historical


def reader(*programs, authenticated=True, roles=('evidence_reader',)):
    return ResearchPrincipal('synthetic-reader', frozenset(roles), frozenset(programs), authenticated)


def run(principal, current=None, historical=None, observations=None):
    left, right = cases()
    return build_candidate_research_assessment(
        principal=principal, catalog=build_scientific_catalog(),
        current=left if current is None else current,
        historical_cases=[right] if historical is None else historical,
        observations=[] if observations is None else observations, cutoff=CUTOFF)


def test_real_catalog_and_comparison_outputs_are_separate_from_model_readiness():
    result = run(reader('CURRENT_SCOPE', 'HISTORICAL_SCOPE'))
    assert result['evidence_summary']['defined_slots'] == 650
    assert result['evidence_summary']['independently_verified_slots'] == 0
    history = result['supporting_details']['historical_comparisons']
    assert history['historical_cases_processed'] == 1
    assert history['comparisons'][0]['known_historical_outcome']['classification'] == 'PASS'
    assert result['primary_result'] == 'ABSTAIN' and result['readiness_grade'] == 'NOT_READY'
    assert result['scientific_readiness_grade'] == 'NOT_READY'
    assert result['prediction_confidence'] == 'NOT_ESTABLISHED'
    assert result['calibration_status'] == result['independent_validation_status'] == 'NOT_VALIDATED'
    assert result['regulatory_risk_assessment'] == 'NOT_INDEPENDENTLY_ASSESSED'
    assert result['probabilities'] == {'PASS': None, 'CRL': None, 'EXTENSION': None}
    assert result['last_verified_update'] is result['model_version'] is None
    assert result['trading_authorized'] is result['eligible_for_validated_accuracy'] is False


@pytest.mark.parametrize('principal', [None, {'roles': ['evidence_reader']},
    reader('CURRENT_SCOPE', authenticated=False), reader('CURRENT_SCOPE', roles=()),
    reader('OTHER_SCOPE'), reader('CURRENT_SCOPE')])
def test_denial_occurs_before_any_scientific_or_historical_projection(principal):
    current, historical = cases()
    with patch('research.scientific_comparison_service.evaluate_registry') as science:
        with patch('research.scientific_comparison_service.compare_historical_cases') as history:
            with pytest.raises(PermissionError):
                build_candidate_research_assessment(
                    principal=principal, catalog={}, current=current,
                    historical_cases=[historical], observations=[], cutoff=CUTOFF)
            science.assert_not_called()
            history.assert_not_called()


def test_empty_history_is_valid_research_absence_and_cannot_become_a_negative_forecast():
    result = run(reader('CURRENT_SCOPE'), historical=[])
    assert result['supporting_details']['historical_comparisons']['historical_cases_processed'] == 0
    assert result['primary_result'] == 'ABSTAIN'


def test_cross_program_observation_rejected_even_when_reader_can_read_both_programs():
    observation = {
        'observation_id': 'synthetic-observation', 'program_id': 'HISTORICAL_SCOPE',
        'field_id': 'BIO-001', 'source_url': 'https://www.sec.gov/synthetic.htm',
        'document_id': 'SYNTHETIC', 'source_document_sha256': None,
        'source_role': 'PREDECISION_RESEARCH', 'published_at': '2024-01-01',
        'observed_at': '2024-01-02T00:00:00Z', 'value': 'Synthetic source report',
        'conflict_ids': [], 'uncertainty': 'Not independently reviewed',
        'verification_status': 'UNVERIFIED',
    }
    with pytest.raises(ValueError, match='cross-program'):
        run(reader('CURRENT_SCOPE', 'HISTORICAL_SCOPE'), observations=[observation])


def test_missing_action_provenance_is_not_repaired_by_a_close_scientific_match():
    current, historical = cases()
    historical['action_events'][0]['decision_label'] = None
    result = run(reader('CURRENT_SCOPE', 'HISTORICAL_SCOPE'), current, [historical])
    report = result['supporting_details']['historical_comparisons']['comparisons'][0]
    assert report['known_historical_outcome'] is None
    assert report['context_eligible'] is False
    assert result['primary_result'] == 'ABSTAIN'


def test_real_six_case_registry_cannot_silently_become_an_engine_ready_validation_cohort():
    current, _ = cases()
    result = build_registry_candidate_research_assessment(
        principal=reader('CURRENT_SCOPE', DEFAULT_PROGRAM), catalog=build_scientific_catalog(),
        current=current, historical_registry=build_historical_registry(),
        registry_program_id=DEFAULT_PROGRAM, observations=[], cutoff=CUTOFF)
    triage = result['historical_registry_triage']
    assert triage['records_examined'] == 6
    assert triage['engine_ready_records'] == triage['comparisons_executed'] == 0
    assert triage['outcome_values_withheld'] is True
    for row in triage['exclusions']:
        assert 'HISTORICAL_LABEL_GATE_REJECTED_SOURCE_PROVENANCE' in row['exclusion_reasons']
        assert row['eligible_for_comparison_engine'] is row['independently_validated'] is False
        assert 'reported_outcome' not in row
    assert result['primary_result'] == 'ABSTAIN'


def test_registry_scope_denied_before_reading_or_validating_the_registry():
    current, _ = cases()
    with patch('research.scientific_comparison_service.validate_registry') as validate:
        with pytest.raises(PermissionError):
            build_registry_candidate_research_assessment(
                principal=reader('CURRENT_SCOPE'), catalog={}, current=current,
                historical_registry={'private': 'OTHER_PROGRAM_SENTINEL'},
                registry_program_id=DEFAULT_PROGRAM, observations=[], cutoff=CUTOFF)
        validate.assert_not_called()
