"""Synthetic chronology examples; no independently verified FDA decisions."""
from copy import deepcopy
import json

import pytest

from research.official_event_protocol import (
    PROTOCOL_PATH, PROTOCOL_SHA256, load_event_protocol, prepare_event_target,
)


def event(kind='FORMAL_TARGET_REVISION', *, event_id='extension', action='2020-02-01',
          target='2020-02-15', revised='2020-05-15'):
    outcome = {'APPROVAL': 'PASS', 'COMPLETE_RESPONSE': 'CRL',
               'FORMAL_TARGET_REVISION': 'EXTENSION'}.get(kind)
    return {'event_id': event_id, 'application_id': 'NDA123456', 'review_cycle_id': 'ORIG-1',
        'event': {'kind': kind, 'action_date': action, 'public_available_on': action,
            'source_url': 'https://www.fda.gov/synthetic-only/' + event_id,
            'target_date': target, 'revised_target_date': revised,
            'decision_label': None if outcome is None else {
                'program_id': 'synthetic', 'application_id': 'NDA123456', 'review_cycle_id': 'ORIG-1',
                'outcome': outcome, 'decision_at': action + 'T12:00:00Z',
                'source_published_at': action + 'T13:00:00Z',
                'source_url': 'https://www.fda.gov/synthetic-only/' + event_id,
                'source_document_sha256': 'a' * 64, 'decision_document_id': event_id}}}


def prepare(events, **kwargs):
    args = {'program_id': 'synthetic', 'application_id': 'NDA123456', 'review_cycle_id': 'ORIG-1',
        'original_target_date': '2020-02-15', 'prediction_cutoff': '2020-01-01T00:00:00Z',
        'horizon_at': '2020-06-01T00:00:00Z', 'evaluation_as_of': '2020-07-01T00:00:00Z'}
    args.update(kwargs)
    return prepare_event_target(events, **args)


def test_protocol_pin_and_explicit_horizon(tmp_path):
    protocol = load_event_protocol()
    assert protocol['classes'] == ['PASS', 'CRL', 'EXTENSION']
    assert protocol['scientific_parameters']['approved_horizon_duration'] is None
    assert protocol['operational_metrics'] is None
    assert len(PROTOCOL_SHA256) == 64
    changed = tmp_path / 'protocol.json'
    changed.write_bytes(PROTOCOL_PATH.read_bytes() + b' ')
    with pytest.raises(ValueError, match='integrity mismatch'):
        load_event_protocol(changed)


@pytest.mark.parametrize('final_kind,outcome', [('APPROVAL', 'PASS'), ('COMPLETE_RESPONSE', 'CRL')])
def test_extension_then_final_preserves_chronology_and_first_event_target(final_kind, outcome):
    extension = event()
    final = event(final_kind, event_id='final', action='2020-05-01', target='2020-05-15', revised=None)
    supplied = [final, extension]
    saved = deepcopy(supplied)
    result = prepare(supplied)
    assert [row['classification'] for row in result['chronology']] == ['EXTENSION', outcome]
    assert result['selected_first_formal_event_id'] == 'extension'
    assert result['research_target_candidate']['outcome'] == 'EXTENSION'
    assert result['blocking_reasons'] == ['AUTHENTICATED_INDEPENDENT_ADJUDICATION_NOT_ESTABLISHED']
    assert result['eligible_for_training_or_evaluation'] is False
    assert result['independently_verified_decisions'] == 0
    assert result['prediction_readiness'] == 'NOT_READY'
    assert result['prediction_action'] == 'ABSTAIN'
    assert result['operational_metrics'] is result['probabilities'] is None
    assert supplied == saved


def test_unpublished_early_extension_cannot_be_replaced_with_later_approval():
    extension = event()
    extension['event']['decision_label'] = None
    final = event('APPROVAL', event_id='final', action='2020-05-01', target='2020-05-15', revised=None)
    result = prepare([final, extension])
    assert result['selected_first_formal_event_id'] == 'extension'
    assert result['research_target_candidate'] is None
    assert 'ORIGINAL_DOCUMENT_AND_AWARE_LABEL_CLOCKS_MISSING' in result['blocking_reasons']


@pytest.mark.parametrize('kind', ['MISSED_TARGET', 'DELAY', 'UNRESOLVED', 'WITHDRAWN', 'REFUSE_TO_FILE'])
def test_unknown_and_delayed_are_not_crl_or_extension(kind):
    item = event(kind, revised=None)
    result = prepare([item])
    assert result['chronology'][0]['classification'] == 'UNRESOLVED'
    assert result['research_target_candidate'] is None
    assert result['selected_first_formal_event_id'] is None
    assert 'NO_FORMAL_ACTION_WITHIN_HORIZON' in result['blocking_reasons']


def test_undated_unresolved_event_remains_in_history():
    item = event('UNRESOLVED', event_id='unknown', revised=None, action=None)
    item['event']['public_available_on'] = None
    result = prepare([item, event()])
    assert len(result['chronology']) == 2
    assert result['chronology'][1]['event']['action_date'] is None


@pytest.mark.parametrize('field,value', [
    ('prediction_cutoff', '2020-01-01'), ('horizon_at', None),
    ('horizon_at', '2019-01-01T00:00:00Z'),
    ('evaluation_as_of', '2020-05-01T00:00:00Z'),
    ('review_cycle_id', None), ('application_id', '123456'),
])
def test_no_inferred_window_or_identity(field, value):
    with pytest.raises(ValueError):
        prepare([event()], **{field: value})


@pytest.mark.parametrize('field,value', [('application_id', 'BLA654321'), ('review_cycle_id', 'ORIG-2')])
def test_events_from_other_application_or_cycle_rejected(field, value):
    item = event()
    item[field] = value
    with pytest.raises(ValueError, match='identity mismatch'):
        prepare([item])


def test_duplicate_event_ids_rejected():
    with pytest.raises(ValueError, match='duplicate event'):
        prepare([event(), event()])


def test_original_target_unknown_not_inferred_from_extension_claim():
    result = prepare([event()], original_target_date=None)
    assert result['original_target_date'] is None
    assert 'ORIGINAL_PDUFA_TARGET_UNKNOWN' in result['blocking_reasons']
    assert result['research_target_candidate'] is None


def test_action_outside_horizon_not_converted_into_extension_or_failure():
    result = prepare([event()], horizon_at='2020-01-31T23:59:59Z')
    assert 'NO_FORMAL_ACTION_WITHIN_HORIZON' in result['blocking_reasons']
    assert result['research_target_candidate'] is None


def test_exact_horizon_inclusion_and_strict_publication_boundary():
    result = prepare([event()], horizon_at='2020-02-01T12:00:00Z',
        evaluation_as_of='2020-02-01T13:00:01Z')
    assert result['research_target_candidate']['outcome'] == 'EXTENSION'
    result = prepare([event()], horizon_at='2020-02-01T12:00:00Z',
        evaluation_as_of='2020-02-01T13:00:00Z')
    assert 'LABEL_NOT_PUBLIC_BEFORE_EVALUATION_AS_OF' in result['blocking_reasons']
    assert result['research_target_candidate'] is None


def test_cutoff_after_first_action_does_not_select_later_approval():
    final = event('APPROVAL', event_id='final', action='2020-05-01', target='2020-05-15', revised=None)
    result = prepare([event(), final], prediction_cutoff='2020-03-01T00:00:00Z')
    assert result['selected_first_formal_event_id'] == 'extension'
    assert result['research_target_candidate'] is None
    assert 'FIRST_FORMAL_ACTION_PRECEDES_PREDICTION_CUTOFF' in result['blocking_reasons']


@pytest.mark.parametrize('field,value,reason', [
    ('source_document_sha256', None, 'HISTORICAL_LABEL_PROVENANCE_INVALID'),
    ('decision_at', '2020-02-01', 'HISTORICAL_LABEL_PROVENANCE_INVALID'),
    ('decision_at', '2020-02-02T12:00:00Z', 'ACTION_DATE_CLOCK_MISMATCH'),
    ('source_published_at', '2020-02-02T13:00:00Z', 'PUBLICATION_DATE_CLOCK_MISMATCH'),
    ('application_id', 'NDA654321', 'LABEL_EXACT_IDENTITY_MISMATCH'),
    ('review_cycle_id', 'ORIG-2', 'LABEL_EXACT_IDENTITY_MISMATCH'),
    ('outcome', 'PASS', 'LABEL_EVENT_SOURCE_OR_OUTCOME_MISMATCH'),
    ('source_url', 'https://www.fda.gov/unrelated', 'LABEL_EVENT_SOURCE_OR_OUTCOME_MISMATCH'),
])
def test_label_identity_document_and_clock_binding(field, value, reason):
    item = event()
    item['event']['decision_label'][field] = value
    result = prepare([item])
    assert reason in result['blocking_reasons']
    assert result['research_target_candidate'] is None


def test_false_independent_flags_do_not_certify():
    item = event()
    item['event']['decision_label']['independently_verified'] = True
    result = prepare([item])
    assert not result['eligible_for_training_or_evaluation']
    assert result['research_target_candidate']['independently_verified'] is False


def test_same_day_competing_formal_actions_require_review():
    final = event('APPROVAL', event_id='final', target='2020-05-15', revised=None)
    result = prepare([event(), final])
    assert 'AMBIGUOUS_SAME_DAY_FORMAL_EVENTS' in result['blocking_reasons']
    assert result['research_target_candidate'] is None


def test_target_chain_and_terminal_cycle_conflicts_are_not_silently_collapsed():
    final = event('APPROVAL', event_id='final', action='2020-05-01', target='2020-02-15', revised=None)
    later = event('COMPLETE_RESPONSE', event_id='later', action='2020-05-02', target='2020-02-15', revised=None)
    result = prepare([event(), final, later])
    assert 'BROKEN_TARGET_REVISION_CHAIN' in result['blocking_reasons']
    assert 'FORMAL_EVENT_AFTER_TERMINAL_ACTION_IN_SAME_CYCLE' in result['blocking_reasons']
    assert len(result['chronology']) == 3
    assert result['research_target_candidate'] is None


def test_snapshot_reproducible_and_sensitive_to_explicit_horizon():
    first = prepare([event()])
    assert first == prepare([event()])
    changed = prepare([event()], horizon_at='2020-06-02T00:00:00Z')
    assert first['input_snapshot_sha256'] != changed['input_snapshot_sha256']
    json.dumps(first, allow_nan=False)
