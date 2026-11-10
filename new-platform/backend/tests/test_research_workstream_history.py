"""Software-only history/failure isolation fixtures; no clinical evidence or grades."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import pytest
from scripts.research_workstream_history import append_snapshot,validate_history,changed_applications
from scripts.select_research_history_run import select
from scripts.build_focus_research_checkpoint_r47 import collect
from scripts.build_historical_source_checkpoint_r47 import verify
from test_parallel_focus_historical_r47 import source_bundle,HASHES,history_fixture

AT='2026-11-09T19:00:00Z'
SHA='a'*40

def test_append_only_restart_corruption_and_cross_track_rejection():
    report=collect(source_bundle(),HASHES,AT)
    first=append_snapshot(None,report,track='A',at=AT,run_id='123',commit=SHA)
    original=deepcopy(first)
    assert append_snapshot(first,report,track='A',at=AT,run_id='123',commit=SHA)==first
    changed=deepcopy(report);changed['rows'][0]['currentRegistryPrimaryTables']=2
    second=append_snapshot(first,changed,track='A',at=AT,run_id='124',commit=SHA)
    assert first==original and second['events'][0]==first['events'][0]
    assert second['events'][1]['previousSha256']==first['headSha256']
    corrupt=deepcopy(second);corrupt['events'][0]['snapshot']['rows'][0]['nct']='NCT99999999'
    with pytest.raises(ValueError,match='DIGEST'):validate_history(corrupt,'A')
    with pytest.raises(ValueError,match='CROSS_TRACK'):validate_history(first,'B')
    with pytest.raises(ValueError,match='REPLAY_CONFLICT'):
        append_snapshot(first,changed,track='A',at=AT,run_id='123',commit=SHA)
    assert second['events'][-1]['snapshot']['validatedFdaApplicationForecasts']==0


def test_only_source_version_changes_reopen_cases_not_run_timestamps():
    first=collect(source_bundle(),HASHES,AT)
    clock_only=collect(source_bundle(),HASHES,'2026-11-09T20:00:00Z')
    assert not any(r['reassessmentRequired'] for r in changed_applications(first,clock_only))
    inputs=source_bundle();inputs['primary']['records'][0]['sourceResponseSha256']='f'*64
    updated=collect(inputs,HASHES,AT)
    changed=[r for r in changed_applications(first,updated) if r['reassessmentRequired']]
    assert changed
    assert all(r['state']=='SOURCE_VERSION_CHANGED_REVIEW_REQUIRED' and r['materialScientificChangeAdjudicated'] is False for r in changed)
    assert all(r['currentResearchRecord']['numericalProbability'] is None for r in changed)
    assert all(r['priorResearchRecord']['evidenceFingerprint']!=r['currentResearchRecord']['evidenceFingerprint'] for r in changed)


def test_track_a_failure_does_not_prevent_independent_track_b_execution():
    def bad_a():
        inputs=source_bundle();inputs['documents']['records'].pop()
        return collect(inputs,HASHES,AT)
    def good_b():
        rows,receipt,raw=history_fixture();return verify(rows,receipt,raw,AT)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(bad_a);b=pool.submit(good_b)
        with pytest.raises(ValueError):a.result()
        assert b.result()['prospectiveAccuracy'] is None
        assert b.result()['researchSourceActionCandidates']==1


def test_prior_history_lookup_is_branch_track_specific_and_never_resets_on_api_failure():
    paths=[]
    def api(path):
        paths.append(path)
        if '/runs?' in path:return {'workflow_runs':[{'id':9,'head_branch':'feature/medical','conclusion':'success','status':'completed'}]}
        return {'artifacts':[{'name':'main-focus-research-history-9','expired':False}]}
    assert select('A','feature/medical',api)=={'run_id':'9','artifact_name':'main-focus-research-history-9'}
    assert 'branch=feature%2Fmedical' in paths[0]
    def denied(path):raise PermissionError('No read access')
    with pytest.raises(PermissionError):select('B','feature/medical',denied)
    def expired(path):
        if '/runs?' in path:return {'workflow_runs':[{'id':9,'head_branch':'feature/medical','conclusion':'success','status':'completed'}]}
        return {'artifacts':[{'name':'main-focus-research-history-9','expired':True}]}
    with pytest.raises(ValueError,match='EXPIRED'):select('A','feature/medical',expired)


def test_availability_loss_is_not_misrepresented_as_a_new_document_version():
    from scripts.research_workstream_history import digest
    first=collect(source_bundle(),HASHES,AT);current=deepcopy(first)
    case=current['applicationResearchRecords'][0]
    case['sourceVersions']['trials'][0]['sourceVersions']['primary']=None
    case['evidenceFingerprint']=digest(case['sourceVersions'])
    change=changed_applications(first,current)[0]
    assert change['state']=='SOURCE_AVAILABILITY_CHANGED_REVIEW_REQUIRED'
    assert change['reassessmentRequired'] is True
    assert change['materialScientificChangeAdjudicated'] is False


def test_recomputed_history_cannot_introduce_unvalidated_forecasts_or_signoffs():
    from scripts.research_workstream_history import digest
    report=collect(source_bundle(),HASHES,AT)
    first=append_snapshot(None,report,track='A',at=AT,run_id='123',commit=SHA)
    bad=deepcopy(first);event=bad['events'][0]
    event['snapshot']['applicationResearchRecords'][0]['numericalProbability']=0.9
    event['snapshotSha256']=digest(event['snapshot'])
    event['sha256']=digest({k:v for k,v in event.items() if k!='sha256'});bad['headSha256']=event['sha256']
    with pytest.raises(ValueError,match='UNVERIFIED_APPLICATION'):validate_history(bad,'A')
    rows,receipt,raw=history_fixture();backtest=verify(rows,receipt,raw,AT);backtest['approvalProbability']=.9
    with pytest.raises(ValueError,match='UNVERIFIED_BACKTEST'):
        append_snapshot(None,backtest,track='B',at=AT,run_id='123',commit=SHA)


def test_completed_failed_delivery_run_can_preserve_its_valid_history_artifact():
    def api(path):
        if '/runs?' in path:
            assert 'status=completed' in path
            return {'workflow_runs':[{'id':9,'head_branch':'feature/medical','status':'completed','conclusion':'failure'}]}
        return {'artifacts':[{'name':'main-focus-research-history-9','expired':False}]}
    assert select('A','feature/medical',api)['run_id']=='9'


def test_workflows_are_separate_with_no_cross_track_needs_or_writer_permissions():
    from pathlib import Path
    root=Path(__file__).resolve().parents[3]/'.github/workflows'
    a=(root/'main-r47-parallel-focus-historical-research.yml').read_text()
    b=(root/'main-r47-historical-source-track-b.yml').read_text()
    assert 'name: MAIN FOCUS Scientific Prediction Research' in a
    assert 'name: MAIN Historical FDA Backtesting and Calibration' in b
    assert 'group: main-r47-focus-research-' in a and 'group: main-r47-history-track-b-' in b
    for track,body in [('A',a),('B',b)]:
        assert 'needs:' not in body and 'contents: write' not in body
        assert 'workflow_dispatch:' in body and "cron: '28 10 * * *'" in body
        assert f'Report independent Track {track} failure' in body
        assert 'test -f "$RUNNER_TEMP/' in body
        assert '--previous ' in body and 'actions/download-artifact@v4' in body
