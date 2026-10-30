from copy import deepcopy
import json

import pytest

from research.historical_decision_registry import DEFAULT_PROGRAM, build_historical_registry
from research.scientific_historical_verification import build_verification_worklist, main


def test_source_leads_remain_unverified_and_cutoff_exclusions_remain_visible():
    registry = build_historical_registry()
    before = deepcopy(registry)
    result = build_verification_worklist(registry, program_id=DEFAULT_PROGRAM)
    assert registry == before
    assert result['case_count'] == 6
    assert result['source_observation_count'] == 26
    assert result['cutoff_admitted_research_observation_count'] == 17
    assert result['independently_verified_cases'] == result['evaluated_predictions'] == 0
    assert result['measured_performance'] is result['probabilities'] is None
    assert result['prediction_action'] == 'ABSTAIN'
    for case in result['cases']:
        assert not case['eligible_for_training_or_evaluation']
        admitted = set(case['cutoff_admitted_research_observation_ids'])
        excluded = {row['observation_id'] for row in case['cutoff_exclusions']}
        assert not admitted & excluded
        assert admitted | excluded == {row['observation_id'] for row in case['observation_source_leads']}
        assert all(row['observation_id'] in excluded for row in case['observation_source_leads']
                   if row['source_role'] == 'OUTCOME_ONLY')
        assert len(case['verification_tasks']) == 9


def test_scope_and_self_certification_cannot_bypass_existing_registry_gate():
    registry = build_historical_registry()
    with pytest.raises(ValueError, match='cross-program'):
        build_verification_worklist(registry, program_id='OTHER')
    registry['records'][0]['review_cycle_independently_adjudicated'] = True
    with pytest.raises(ValueError, match='self-certify'):
        build_verification_worklist(registry, program_id=DEFAULT_PROGRAM)


def test_local_snapshot_hash_binds_changes_without_claiming_original_bytes():
    registry = build_historical_registry()
    first = build_verification_worklist(registry, program_id=DEFAULT_PROGRAM)
    registry['records'][0]['missing_documents'].append('Additional independent review required')
    second = build_verification_worklist(registry, program_id=DEFAULT_PROGRAM)
    assert first['registry_snapshot_sha256'] != second['registry_snapshot_sha256']
    assert second['hash_scope'] == 'LOCAL_REGISTRY_NOT_ORIGINAL_SOURCE_BYTES'


def test_cli_reproduction_drift_and_no_overwrite(tmp_path):
    output = tmp_path / 'audit.json'
    args = ['--output', str(output)]
    assert main(args) == main(args + ['--check']) == 0
    with pytest.raises(FileExistsError):
        main(args)
    payload = json.loads(output.read_text())
    payload['independently_verified_cases'] = 6
    output.write_text(json.dumps(payload))
    with pytest.raises(SystemExit) as exc:
        main(args + ['--check'])
    assert exc.value.code == 1
