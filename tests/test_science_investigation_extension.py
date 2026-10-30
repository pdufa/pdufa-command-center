"""Fifty-level task definitions are not completed FDA scientific validation."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from research.science_investigation_depths import build_depth_framework
from research.science_investigation_extension import (
    EXTENSION_PATH, build_extended_investigation_framework,
    load_extension_catalog, validate_extension_catalog,
)
from research.fda_verification_queue import build_verification_queue

ROOT=Path(__file__).resolve().parents[1]
QUESTIONS=json.loads((ROOT/'new-platform/backend/app/science_40_question_catalog.json').read_text())


@pytest.fixture
def extension():
    return load_extension_catalog(QUESTIONS)


@pytest.fixture
def cases():
    queue=build_verification_queue(ROOT/'data/prediction_engine_history.csv',
        ROOT/'research/evidence/2025_holdout_fda_action_evidence.json',
        reconstruction_manifest=ROOT/'research/evidence/2025_holdout_predecision_reconstruction.json',
        as_of=date(2026,10,28))
    return [row['predecision_reconstruction'] for row in queue['queue'] if 'predecision_reconstruction' in row]


def test_extension_inherits_twenty_semantics_without_copying_or_replacing_base(extension,cases):
    assert len(json.loads(EXTENSION_PATH.read_text())['additional_levels'])==30
    assert 'levels' not in extension
    for case in cases:
        sources=case['source_classification'];cutoff=case['reconstruction_cutoff']
        original=deepcopy((sources,extension))
        base=build_depth_framework(QUESTIONS,sources,reconstruction_cutoff=cutoff)
        expanded=build_extended_investigation_framework(QUESTIONS,sources,cutoff,extension=extension)
        assert expanded['levels'][:20]==base['levels']
        assert expanded['base_catalog_version']==base['catalog_version']
        assert expanded['legacy_backend_review_boundary_changed'] is False
        expanded['levels'][0]['requirements'].append('Output mutation')
        assert (sources,extension)==original


def test_fifty_unique_tasks_cover_all_questions_and_layers_without_certifying(cases):
    for case in cases:
        result=build_extended_investigation_framework(QUESTIONS,case['source_classification'],case['reconstruction_cutoff'])
        levels=result['levels']
        assert result['required_levels']==list(range(1,51))
        assert [level['depth_level'] for level in levels]==list(range(1,51))
        assert [level['level_id'] for level in levels]==[f'D{i:02d}' for i in range(1,51)]
        coverage={q for level in levels[20:] for q in level['question_ids']}
        assert coverage=={q['id'] for q in QUESTIONS['questions']}
        assert {q['layer'] for q in QUESTIONS['questions'] if q['id'] in coverage}==set(range(1,9))
        assert result['independently_completed_level_count']==0
        assert result['predictive_value_validated'] is False
        assert result['independently_reviewed_levels']==[]
        assert result['completion_policy']['fixed_800_review_requirement'] is False
        assert all(level['status']=='INDEPENDENT_REVIEW_MISSING' and level['independently_completed'] is False
                   and level['ready_for_independent_certification'] is False for level in levels)
        assert all(not level['independently_reviewed_question_ids'] for level in levels)


def test_population_compliance_and_failed_primary_have_concrete_tasks(extension):
    by_number={level['depth_level']:level for level in extension['additional_levels']}
    assert 'modified' in ' '.join(by_number[23]['requirements'])
    assert 'sponsor explanation' in ' '.join(by_number[23]['requirements'])
    assert 'prespecified primary endpoint as failed' in ' '.join(by_number[27]['requirements'])
    assert 'PASS/CRL/EXTENSION' in ' '.join(by_number[49]['requirements'])
    assert 'ABSTAIN' in ' '.join(by_number[50]['requirements'])


def test_only_audited_pre_cutoff_candidates_inform_extended_tasks(cases):
    for case in cases:
        sources=case['source_classification']
        allowed={s['source_id']:s for s in sources if s['classification']=='PREDECISION_RESEARCH_CANDIDATE'}
        result=build_extended_investigation_framework(QUESTIONS,sources,case['reconstruction_cutoff'])
        for level in result['levels'][20:]:
            expected=[key for key,source in allowed.items()
                      if set(source['science_question_ids']) & set(level['question_ids'])]
            assert level['source_lead_ids']==expected
            assert level['blocking_prerequisite_levels']==level['prerequisite_levels']
            assert set(level['question_ids_with_source_leads']).isdisjoint(level['question_ids_without_source_leads'])
            assert set(level['question_ids_with_source_leads']+level['question_ids_without_source_leads'])==set(level['question_ids'])


def test_missing_sources_never_become_opposing_findings_or_completed_tasks():
    result=build_extended_investigation_framework(QUESTIONS,[],'2025-01-01')
    assert all(level['source_lead_ids']==[] for level in result['levels'])
    assert all(level['question_ids_without_source_leads']==level['question_ids'] for level in result['levels'])
    assert all(level['completion_artifacts_status']=='NOT_INDEPENDENTLY_ADJUDICATED' for level in result['levels'])


@pytest.mark.parametrize('mutation',[
    lambda p:p['additional_levels'].pop(),
    lambda p:p['additional_levels'][0].update(depth_level=True),
    lambda p:p['additional_levels'][0].update(depth_level=20),
    lambda p:p['additional_levels'][1].update(level_id='D21'),
    lambda p:p['additional_levels'][1].update(title=p['additional_levels'][0]['title']),
    lambda p:p['additional_levels'][1].update(objective=p['additional_levels'][0]['objective']),
    lambda p:p['additional_levels'][0].update(prerequisite_levels=[21]),
    lambda p:p['additional_levels'][0].update(prerequisite_levels=[1,1]),
    lambda p:p['additional_levels'][0].update(question_ids=['S99']),
    lambda p:p['additional_levels'][0].update(requirements=[]),
    lambda p:p['additional_levels'][0].update(completion_artifacts=[]),
    lambda p:p['additional_levels'][0].update(independently_completed=True),
    lambda p:p.update(inherited_levels=False),
    lambda p:p.update(required_levels=True),
    lambda p:p.update(extends_catalog_version='unbound-base'),
    lambda p:p.update(protocol_status='INDEPENDENTLY_VALIDATED'),
    lambda p:p['completion_policy'].update(automatic_completion_enabled=True),
    lambda p:p['completion_policy'].update(source_leads_complete_levels=0),
])
def test_invalid_or_self_certifying_extension_fails_closed(extension,mutation):
    mutation(extension)
    with pytest.raises(ValueError):
        validate_extension_catalog(extension,QUESTIONS)


def test_added_tasks_must_include_entire_question_catalog(extension):
    for level in extension['additional_levels']:
        level['question_ids']=[q for q in level['question_ids'] if q!='S40']
    with pytest.raises(ValueError,match='all forty'):
        validate_extension_catalog(extension,QUESTIONS)


def test_duplicate_json_policy_cannot_overwrite_extension(tmp_path):
    path=tmp_path/'duplicate.json';path.write_text('{"required_levels":50,"required_levels":20}')
    with pytest.raises(ValueError,match='duplicate fifty-level'):
        load_extension_catalog(QUESTIONS,path)


@pytest.mark.parametrize('field,value',[
    ('source_role','OUTCOME_ONLY'),('available_on','2026-01-01'),
    ('availability_basis','PRINTED_DATE_ONLY'),('independently_reviewed',True),
    ('eligible_for_frozen_prediction',True),
])
def test_unsupported_candidate_cannot_supply_extended_task_leads(cases,field,value):
    case=deepcopy(cases[0])
    source=next(s for s in case['source_classification'] if s['classification']=='PREDECISION_RESEARCH_CANDIDATE')
    source[field]=value
    with pytest.raises(ValueError):
        build_extended_investigation_framework(QUESTIONS,case['source_classification'],case['reconstruction_cutoff'])
