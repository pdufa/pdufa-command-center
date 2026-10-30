"""Operator workflow security boundaries; no live execution or credentials."""
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def workflow():
    return yaml.safe_load((ROOT / '.github/workflows/isolated-readiness-smoke.yml').read_text())


def job():
    return workflow()['jobs']['staging-pipeline-reconciliation']


def test_retrieval_is_only_manually_dispatched_on_exact_research_branch():
    source = workflow()
    # PyYAML uses YAML 1.1, where the key 'on' is parsed as True.
    assert set(source.get('on', source.get(True))) == {'workflow_dispatch'}
    assert source['permissions'] == {'contents': 'read'}
    assert job()['if'] == ("github.event_name == 'workflow_dispatch' && "
                           "github.ref == 'refs/heads/research/fda-decision-label-gate-20261028'")
    assert job()['timeout-minutes'] == 10
    assert job()['concurrency']['cancel-in-progress'] is False


def test_staging_uses_only_distinct_staging_secret_and_fixed_origin():
    step = next(s for s in job()['steps'] if 'run' in s)
    assert step['env'] == {'PDUFA_INTERNAL_API_KEY': '${{ secrets.PDUFA_STAGING_INTERNAL_API_KEY }}'}
    assert '--backend-origin https://pdufa-new-api-staging.onrender.com' in step['run']
    assert '--allow-staging-identity-allocation' in step['run']
    assert '--request-timeout 120' in step['run']
    assert '${{ inputs.' not in step['run']
    assert 'secrets.' not in step['run']
    assert 'set -x' not in step['run']
    assert 'echo ' not in step['run']
    assert 'export ' not in step['run']
    assert 'environment' not in job()  # Never consume isolated review environment.


def test_only_existing_runner_executes_without_deploy_or_database_commands():
    commands = [s['run'] for s in job()['steps'] if 'run' in s]
    assert len(commands) == 1
    assert commands[0].strip().startswith('python -m research.preliminary_workspace_http ')
    assert not any(token in commands[0] for token in ('curl ', 'psql ', 'render ', 'printenv', 'gh ', '>>'))
    checkout = next(s for s in job()['steps'] if s.get('uses') == 'actions/checkout@v4')
    assert checkout['with']['persist-credentials'] is False


def test_only_exact_aggregate_report_is_retained_for_one_day_after_success():
    steps = job()['steps']
    upload = next(s for s in steps if s.get('uses') == 'actions/upload-artifact@v4')
    assert upload['with']['path'] == '${{ runner.temp }}/pdufa-pipeline-reconciliation.json'
    assert upload['with']['retention-days'] == 1
    assert upload['with']['if-no-files-found'] == 'error'
    assert 'if' not in upload  # Default success() avoids retaining failed/partial results.
    assert '--output "$RUNNER_TEMP/pdufa-pipeline-reconciliation.json"' in next(s['run'] for s in steps if 'run' in s)


def test_unrelated_isolated_review_job_keeps_original_scope_and_secret():
    isolated = workflow()['jobs']['isolated-readiness']
    assert isolated['if'] == "github.ref == 'refs/heads/feature/pipeline-enrichment-foundation-20261023'"
    assert isolated['environment'] == 'isolated-alpaca-review'
    assert len(isolated['steps']) == 2
    assert isolated['steps'][1]['env'] == {
        'PDUFA_REVIEW_BASE_URL': 'https://pdufa-alpaca-enrichment-review.onrender.com',
        'PDUFA_INTERNAL_API_KEY': '${{ secrets.PDUFA_INTERNAL_API_KEY }}'}


def test_security_checks_run_when_manual_workflow_changes():
    source = yaml.safe_load((ROOT / '.github/workflows/preliminary-candidate-scope-safety.yml').read_text())
    triggers = source.get('on', source.get(True))
    for trigger in ('push', 'pull_request'):
        assert '.github/workflows/isolated-readiness-smoke.yml' in triggers[trigger]['paths']
        assert 'tests/test_mobile_staging_workflow.py' in triggers[trigger]['paths']
    script = source['jobs']['scope-tests']['steps'][-1]['run']
    assert 'pyyaml' in script
    assert 'tests/test_mobile_staging_workflow.py' in script
