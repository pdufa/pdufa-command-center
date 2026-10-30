"""Synthetic cohort proposals only; no actual FDA forecasts are evaluated."""
from copy import deepcopy
import json
import pytest

from research.official_evaluation_manifest import build_evaluation_manifest, main

PROPOSAL = {'calibration_starts_at': '2020-01-01T00:00:00Z',
            'evaluation_starts_at': '2021-01-01T00:00:00Z',
            'required_fields': ['efficacy']}


def records():
    rows = []
    for i, (partition, year) in enumerate([('TRAIN', 2019), ('CALIBRATION', 2020), ('EVALUATION', 2021)]):
        rows.append({'application_id': f'NDA{i + 1:06d}', 'review_cycle_id': 'ORIG-001',
            'program_id': 'SYNTHETIC', 'program_family': f'SYNTHETIC_{i}',
            'partition': partition, 'therapeutic_area': 'SYNTHETIC_AREA',
            'evidence_cutoff': f'{year}-02-01T00:00:00Z',
            'prediction_inputs': [{'field_id': 'efficacy', 'value': 'SYNTHETIC_VALUE',
                'source_document_sha256': 'a' * 64,
                'source_published_at': f'{year}-01-01T00:00:00Z',
                'public_available_at': f'{year}-01-01T00:00:00Z',
                'source_status': 'SOURCE AVAILABLE', 'conflict': False}],
            'outcome_label': {'program_id': 'SYNTHETIC', 'outcome': 'PASS',
                'application_id': f'NDA{i + 1:06d}', 'review_cycle_id': 'ORIG-001',
                'decision_at': f'{year}-03-01T00:00:00Z',
                'source_published_at': f'{year}-03-02T00:00:00Z',
                'source_url': 'https://www.fda.gov/synthetic-fixture',
                'source_document_sha256': 'b' * 64, 'decision_document_id': 'SYNTHETIC'}})
    return rows


def run(rows=None, **updates):
    return build_evaluation_manifest(records() if rows is None else rows, **(PROPOSAL | updates))


def reasons(report, index):
    return report['records'][index]['blocking_reasons']


def test_reproducible_manifest_retains_all_rows_and_withholds_metrics():
    rows = records()
    saved = deepcopy(rows)
    report = run(rows)
    assert report == run(rows)
    assert rows == saved
    assert report['record_count'] == report['blocked_record_count'] == 3
    assert report['preparation_abstention_count'] == 3
    assert report['partition_counts'] == {'TRAIN': 1, 'CALIBRATION': 1, 'EVALUATION': 1, 'UNASSIGNED': 0}
    assert all(reasons(report, i) == [
        'INDEPENDENT_OUTCOME_AND_SCIENTIFIC_REVIEW_NOT_ESTABLISHED',
        'PREDICTION_TARGET_AND_HORIZON_NOT_ESTABLISHED'] for i in range(3))
    assert report['operational_metrics'] is report['probabilities'] is None
    assert report['evaluated_predictions'] == report['independently_verified_decisions'] == 0
    assert report['prediction_readiness'] == 'NOT_READY'
    assert report['prediction_action'] == 'ABSTAIN'
    assert 'SYNTHETIC_VALUE' not in json.dumps(report)


def test_hashes_bind_both_data_and_proposal_without_promoting_flags():
    first = run()
    rows = records()
    rows[0]['prediction_inputs'][0]['value'] = 'ALTERED'
    assert run(rows)['input_snapshot_sha256'] != first['input_snapshot_sha256']
    assert run(rows)['manifest_sha256'] != first['manifest_sha256']
    assert run(evaluation_starts_at='2021-01-02T00:00:00Z')['proposal_sha256'] != first['proposal_sha256']
    for row in rows:
        row.update(independently_verified=True, model_validated=True)
    assert run(rows)['evaluated_predictions'] == 0
    assert all(not row['eligible_for_training_or_evaluation'] for row in run(rows)['records'])


@pytest.mark.parametrize('field,value,reason', [
    ('evidence_cutoff', '2019-12-31T23:59:59Z', 'CALIBRATION_CUTOFF_OUTSIDE_PRESPECIFIED_WINDOW'),
    ('evidence_cutoff', '2021-01-01T00:00:00Z', 'CALIBRATION_CUTOFF_OUTSIDE_PRESPECIFIED_WINDOW'),
])
def test_calibration_cutoffs_are_explicit_half_open_window(field, value, reason):
    rows = records()
    rows[1][field] = value
    assert reason in reasons(run(rows), 1)


def test_training_and_calibration_labels_cannot_leak_into_next_stage():
    rows = records()
    rows[0]['outcome_label']['source_published_at'] = PROPOSAL['calibration_starts_at']
    rows[1]['outcome_label']['source_published_at'] = PROPOSAL['evaluation_starts_at']
    report = run(rows)
    assert 'TRAINING_LABEL_NOT_KNOWN_BEFORE_EVALUATION' in reasons(report, 0)
    assert 'CALIBRATION_LABEL_NOT_KNOWN_BEFORE_EVALUATION' in reasons(report, 1)


def test_final_evaluation_does_not_start_at_calibration_boundary():
    rows = records()
    rows[2]['evidence_cutoff'] = PROPOSAL['calibration_starts_at']
    assert 'EVALUATION_CUTOFF_BEFORE_FINAL_BOUNDARY' in reasons(run(rows), 2)


@pytest.mark.parametrize('indices', [(0, 1), (0, 2), (1, 2)])
def test_all_partition_pairs_isolate_applications_and_program_families(indices):
    rows = records()
    left, right = indices
    rows[right]['application_id'] = rows[left]['application_id']
    rows[right]['program_family'] = rows[left]['program_family'].lower()
    report = run(rows)
    for index in indices:
        assert 'APPLICATION_CROSSES_PARTITIONS' in reasons(report, index)
        assert 'PROGRAM_FAMILY_CROSSES_PARTITIONS' in reasons(report, index)


def test_invalid_conflicting_rows_remain_in_denominators_and_isolation_checks():
    rows = records()
    other = deepcopy(rows[1])
    other['partition'] = 'EVALUATION'
    other['prediction_inputs'] = []
    other['outcome_label'] = None
    rows.append(other)
    report = run(rows)
    assert report['record_count'] == 4
    assert report['partition_counts']['EVALUATION'] == 2
    assert 'DUPLICATE_APPLICATION_REVIEW_CYCLE' in reasons(report, 1)
    assert 'DUPLICATE_APPLICATION_REVIEW_CYCLE' in reasons(report, 3)
    assert 'APPLICATION_CROSSES_PARTITIONS' in reasons(report, 1)
    assert 'MISSING_REQUIRED_EVIDENCE' in reasons(report, 3)


def test_missing_data_and_unknown_partitions_are_not_dropped_or_imputed():
    rows = records()
    rows[0]['prediction_inputs'][0]['value'] = None
    rows[1]['therapeutic_area'] = None
    rows[2]['partition'] = None
    rows.append(None)
    report = run(rows)
    assert report['record_count'] == 4
    assert report['partition_counts']['UNASSIGNED'] == 2
    assert report['therapeutic_area_partition_counts']['UNKNOWN']['CALIBRATION'] == 1
    assert 'MISSING_FIELD_VALUE' in reasons(report, 0)
    assert 'THERAPEUTIC_AREA_NOT_ESTABLISHED' in reasons(report, 1)
    assert 'EXPLICIT_PARTITION_REQUIRED' in reasons(report, 2)
    assert 'MISSING_EVALUATION_PARTITION' in report['blocking_reasons']


def test_existing_future_evidence_and_outcome_document_exclusion_gates_reused():
    rows = records()
    rows[0]['prediction_inputs'][0]['public_available_at'] = rows[0]['evidence_cutoff']
    rows[1]['prediction_inputs'][0]['source_document_sha256'] = 'b' * 64
    report = run(rows)
    assert 'HISTORICAL_EVIDENCE_LEAKAGE' in reasons(report, 0)
    assert 'OUTCOME_DOCUMENT_IN_PREDICTION_INPUTS' in reasons(report, 1)


def test_empty_cohort_never_yields_performance():
    report = run([])
    assert report['record_count'] == 0
    assert report['operational_metrics'] is None
    assert all('MISSING_' + p + '_PARTITION' in report['blocking_reasons'] for p in ('TRAIN', 'CALIBRATION', 'EVALUATION'))


@pytest.mark.parametrize('updates', [
    {'calibration_starts_at': '2020-01-01'},
    {'calibration_starts_at': '2021-01-01T00:00:00Z'},
    {'evaluation_starts_at': '2019-01-01T00:00:00Z'},
    {'required_fields': []}, {'required_fields': ['efficacy', 'efficacy']},
])
def test_missing_or_ambiguous_protocol_proposals_rejected(updates):
    with pytest.raises(ValueError):
        run(**updates)


def test_cli_replay_no_overwrite_and_repeated_json_keys_rejected(tmp_path):
    data, proposal, output = [tmp_path / name for name in ('records.json', 'proposal.json', 'report.json')]
    data.write_text(json.dumps(records()))
    proposal.write_text(json.dumps(PROPOSAL))
    args = ['--records', str(data), '--proposal', str(proposal), '--output', str(output)]
    assert main(args) == 0
    assert json.loads(output.read_text()) == run()
    with pytest.raises(FileExistsError):
        main(args)
    output.unlink()
    data.write_text('[{"partition":"TRAIN", "partition":"EVALUATION"}]')
    with pytest.raises(ValueError, match='duplicate'):
        main(args)
    assert not output.exists()


def target(row):
    label = deepcopy(row['outcome_label'])
    year = row['evidence_cutoff'][:4]
    return {'events': [{'event_id': 'SYNTHETIC_EVENT',
        'application_id': row['application_id'], 'review_cycle_id': row['review_cycle_id'],
        'event': {'kind': 'APPROVAL', 'action_date': year + '-03-01',
            'public_available_on': year + '-03-02', 'source_url': label['source_url'],
            'target_date': year + '-04-01', 'revised_target_date': None,
            'decision_label': label}}], 'original_target_date': year + '-04-01',
        'horizon_at': year + '-05-01T00:00:00Z',
        'evaluation_as_of': year + '-06-01T00:00:00Z'}


def test_event_target_horizon_protocol_and_label_are_bound_to_manifest():
    from research.official_event_protocol import PROTOCOL_SHA256
    rows = records()
    rows[0]['event_target'] = target(rows[0])
    report = run(rows)
    assert report['event_target_protocol_sha256'] == PROTOCOL_SHA256
    event = report['records'][0]['event_target_preparation']
    assert event['research_target_candidate']['outcome'] == 'PASS'
    assert 'PREDICTION_TARGET_AND_HORIZON_NOT_ESTABLISHED' not in reasons(report, 0)
    assert 'AUTHENTICATED_INDEPENDENT_ADJUDICATION_NOT_ESTABLISHED' in reasons(report, 0)
    assert 'OUTCOME_LABEL_DISAGREES_WITH_EVENT_TARGET' not in reasons(report, 0)
    rows[0]['outcome_label']['outcome'] = 'CRL'
    assert 'OUTCOME_LABEL_DISAGREES_WITH_EVENT_TARGET' in reasons(run(rows), 0)


def test_event_target_cannot_bypass_partition_publication_boundary():
    rows = records()
    rows[1]['event_target'] = target(rows[1])
    event = rows[1]['event_target']
    event['evaluation_as_of'] = '2022-01-01T00:00:00Z'
    event['events'][0]['event']['public_available_on'] = '2021-01-01'
    event['events'][0]['event']['decision_label']['source_published_at'] = '2021-01-01T00:00:00Z'
    assert 'EVENT_TARGET_LABEL_NOT_KNOWN_BEFORE_NEXT_PARTITION' in reasons(run(rows), 1)


def test_malformed_event_target_cannot_disappear_as_ready():
    rows = records()
    rows[0]['event_target'] = {'independently_verified': True}
    assert 'INVALID_EVENT_TARGET_PROPOSAL' in reasons(run(rows), 0)
    assert 'PREDICTION_TARGET_AND_HORIZON_NOT_ESTABLISHED' in reasons(run(rows), 0)
