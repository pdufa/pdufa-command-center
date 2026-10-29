"""Chronological safety tests use synthetic bytes/identities, not FDA evidence."""
from copy import deepcopy
import pytest
from research.official_history_readiness import prepare_chronological_backtest


def case():
    return {'program_id': 'synthetic-program', 'application_id': 'NDA123456',
            'review_cycle_id': 'ORIG-001', 'program_family': 'synthetic-family',
            'partition': 'TRAIN', 'evidence_cutoff': '2020-01-01T00:00:00Z',
            'prediction_inputs': [{'field_id': 'efficacy', 'value': 'synthetic',
                'source_document_sha256': 'a' * 64,
                'source_published_at': '2019-01-01T00:00:00Z',
                'public_available_at': '2019-01-01T00:00:00Z',
                'source_status': 'SOURCE AVAILABLE', 'conflict': False}],
            'outcome_label': {'program_id': 'synthetic-program', 'outcome': 'PASS',
                'application_id': 'NDA123456', 'review_cycle_id': 'ORIG-001',
                'decision_at': '2020-02-01T00:00:00Z',
                'source_published_at': '2020-02-02T00:00:00Z',
                'source_url': 'https://www.fda.gov/synthetic-test-only',
                'source_document_sha256': 'b' * 64, 'decision_document_id': 'synthetic'}}


def prepare(rows):
    return prepare_chronological_backtest(rows,
        evaluation_starts_at='2021-01-01T00:00:00Z', required_fields={'efficacy'})


def reasons(row):
    return prepare([row])['records'][0]['blocking_reasons']


def test_structural_completeness_never_certifies_science_or_outcomes():
    row = case()
    row['independently_verified'] = True
    row['outcome_label']['independently_verified'] = True
    result = prepare([row])
    assert result['records'][0]['blocking_reasons'] == [
        'INDEPENDENT_OUTCOME_AND_SCIENTIFIC_REVIEW_NOT_ESTABLISHED']
    assert result['prediction_action'] == 'ABSTAIN'
    assert result['measured_performance'] is None
    assert result['independently_verified_decisions'] == 0
    assert result['records'][0]['eligible_for_training_or_evaluation'] is False


@pytest.mark.parametrize('clock', [None, '2019-01-01', '2020-01-01T00:00:00Z', '2022-01-01T00:00:00Z'])
def test_missing_or_late_publication_prevents_backtesting(clock):
    row = case()
    row['prediction_inputs'][0]['public_available_at'] = clock
    assert any(x in reasons(row) for x in ['HISTORICAL_EVIDENCE_LEAKAGE', 'MISSING_VERIFIABLE_PUBLICATION_CLOCK'])


def test_outcome_document_not_allowed_in_inputs():
    row = case()
    row['prediction_inputs'][0]['source_document_sha256'] = 'b' * 64
    assert 'OUTCOME_DOCUMENT_IN_PREDICTION_INPUTS' in reasons(row)
    row['prediction_inputs'][0]['outcome'] = 'PASS'
    assert 'INVALID_INPUT_ENVELOPE_OR_OUTCOME_LEAKAGE' in reasons(row)


@pytest.mark.parametrize('application', ['123456', 'nda123456', 'NDA12345', 'BLA1234567', None])
def test_incorrect_application_identifiers(application):
    row = case()
    row['application_id'] = application
    assert 'INVALID_APPLICATION_ID' in reasons(row)


def test_wrong_review_cycle_rejected():
    row = case()
    row['outcome_label']['review_cycle_id'] = 'SUPPL-002'
    assert 'LABEL_APPLICATION_CYCLE_MISMATCH' in reasons(row)


def test_duplicate_and_conflicting_decisions_remain_quarantined():
    first = case()
    second = deepcopy(first)
    second['outcome_label']['outcome'] = 'CRL'
    result = prepare([first, second])
    for row in result['records']:
        assert 'DUPLICATE_APPLICATION_REVIEW_CYCLE' in row['blocking_reasons']
        assert 'CONFLICTING_REGULATORY_OUTCOMES' in row['blocking_reasons']


def test_related_applications_never_cross_partitions():
    first = case()
    second = deepcopy(first)
    second['partition'] = 'EVALUATION'
    second['review_cycle_id'] = 'SUPPL-002'
    second['evidence_cutoff'] = '2021-01-02T00:00:00Z'
    result = prepare([first, second])
    assert all('RELATED_APPLICATION_SPLIT_LEAKAGE' in r['blocking_reasons'] for r in result['records'])
    second['application_id'] = 'BLA654321'
    second['program_family'] = second['program_family'].upper()
    result = prepare([first, second])
    assert all('RELATED_PROGRAM_SPLIT_LEAKAGE' in r['blocking_reasons'] for r in result['records'])


def test_training_label_must_be_public_before_evaluation_boundary():
    row = case()
    row['outcome_label']['source_published_at'] = '2021-01-01T00:00:00Z'
    assert 'TRAINING_LABEL_NOT_KNOWN_BEFORE_EVALUATION' in reasons(row)


@pytest.mark.parametrize('status', ['ACCESS_DENIED', 'SOURCE_TEMPORARILY_UNAVAILABLE', 'SOURCE_DOCUMENT_UNVERIFIED'])
def test_unavailable_source_is_not_negative_outcome(status):
    row = case()
    row['prediction_inputs'][0]['source_status'] = status
    assert 'SOURCE_VERIFICATION_FAILED' in reasons(row)
    assert row['outcome_label']['outcome'] == 'PASS'


def test_missing_and_conflicting_evidence_abstains():
    row = case()
    row['prediction_inputs'][0]['conflict'] = True
    assert 'UNRESOLVED_SCIENTIFIC_CONFLICT' in reasons(row)
    row['prediction_inputs'] = []
    assert 'MISSING_REQUIRED_EVIDENCE' in reasons(row)


@pytest.mark.parametrize('outcome', ['PASS', 'CRL', 'EXTENSION'])
def test_three_outcomes_remain_distinct_without_claiming_verification(outcome):
    row = case()
    row['outcome_label']['outcome'] = outcome
    assert 'INVALID_OR_UNVERIFIED_OUTCOME_LABEL' not in reasons(row)
    assert row['outcome_label']['outcome'] == outcome


def test_missed_target_is_never_an_outcome():
    row = case()
    row['outcome_label']['outcome'] = 'MISSED_TARGET'
    assert 'INVALID_OR_UNVERIFIED_OUTCOME_LABEL' in reasons(row)


def test_required_protocol_and_boundary_are_explicit():
    with pytest.raises(ValueError):
        prepare_chronological_backtest([], evaluation_starts_at='2021-01-01', required_fields={'efficacy'})
    with pytest.raises(ValueError):
        prepare_chronological_backtest([], evaluation_starts_at='2021-01-01T00:00:00Z', required_fields=set())
