"""Semantic analytical protocol regressions; not FDA prediction validation."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from research.fda_verification_queue import build_verification_queue
from research.science_investigation_depths import (
    build_depth_framework, load_depth_catalog, validate_depth_catalog,
)

ROOT=Path(__file__).resolve().parents[1]
QUESTIONS=json.loads((ROOT/'new-platform/backend/app/science_40_question_catalog.json').read_text())


@pytest.fixture
def protocol():
    return load_depth_catalog(QUESTIONS)


@pytest.fixture
def cases():
    queue=build_verification_queue(ROOT/'data/prediction_engine_history.csv',
        ROOT/'research/evidence/2025_holdout_fda_action_evidence.json',
        reconstruction_manifest=ROOT/'research/evidence/2025_holdout_predecision_reconstruction.json',
        as_of=date(2026,10,28))
    return [row['predecision_reconstruction'] for row in queue['queue'] if 'predecision_reconstruction' in row]


def test_protocol_defines_twenty_concrete_tasks_covering_all_existing_questions_and_layers(protocol):
    levels=protocol['levels']
    assert [row['depth_level'] for row in levels]==list(range(1,21))
    assert [row['level_id'] for row in levels]==[f'D{i:02d}' for i in range(1,21)]
    coverage={q for row in levels for q in row['question_ids']}
    assert coverage=={q['id'] for q in QUESTIONS['questions']}
    assert {q['layer'] for q in QUESTIONS['questions'] if q['id'] in coverage}==set(range(1,9))
    assert levels[0]['title']=='Application and review-cycle identity'
    assert levels[-1]['title']=='Adversarial synthesis and frozen handoff'
    assert len({row['objective'] for row in levels})==20
    assert all(row['requirements'] and row['completion_artifacts'] for row in levels)
    assert protocol['completion_policy']['fixed_800_review_requirement'] is False


def test_all_six_dossiers_gain_analysis_tasks_without_completed_reviews(cases):
    assert len(cases)==6
    for case in cases:
        framework=case['scientific_dossier']['depth_framework']
        assert framework['catalog_version']=='science-investigation-depth-catalog-v1'
        assert framework['semantic_level_definitions_status']=='DEFINED_RESEARCH_PROTOCOL_NOT_INDEPENDENTLY_VALIDATED'
        assert framework['predictive_value_validated'] is False
        assert framework['independently_reviewed_levels']==[]
        assert all(row['status']=='INDEPENDENT_REVIEW_MISSING' and row['independently_completed'] is False
            and row['ready_for_independent_certification'] is False for row in framework['levels'])
        assert all(row['independently_reviewed_question_ids']==[] for row in framework['levels'])
        assert case['main']['pass_probability'] is case['main']['fail_probability'] is None


def test_source_leads_are_linked_by_existing_questions_and_never_admit_outcomes(cases):
    for case in cases:
        allowed={s['source_id']:s for s in case['source_classification']
                 if s['classification']=='PREDECISION_RESEARCH_CANDIDATE'}
        for level in case['scientific_dossier']['depth_framework']['levels']:
            expected=[identity for identity,source in allowed.items()
                      if set(source['science_question_ids']) & set(level['question_ids'])]
            assert level['source_lead_ids']==expected
            assert level['blocking_prerequisite_levels']==level['prerequisite_levels']
            assert level['completion_artifacts_status']=='NOT_INDEPENDENTLY_ADJUDICATED'


def test_no_sources_leaves_all_tasks_unknown_and_all_reviews_outstanding():
    framework=build_depth_framework(QUESTIONS,[],reconstruction_cutoff='2025-01-01')
    assert all(row['source_lead_ids']==[] and row['question_ids_with_source_leads']==[] for row in framework['levels'])
    assert all(row['question_ids_without_source_leads']==row['question_ids'] for row in framework['levels'])
    assert all(row['independently_completed'] is False for row in framework['levels'])


def test_protocol_and_source_inputs_are_not_modified(cases,protocol):
    case=cases[0]; original=deepcopy((case,protocol))
    framework=build_depth_framework(QUESTIONS,case['source_classification'],
        reconstruction_cutoff=case['reconstruction_cutoff'],protocol=protocol)
    framework['levels'][0]['requirements'].append('An output mutation')
    assert (case,protocol)==original


@pytest.mark.parametrize('mutation',[
    lambda p:p['levels'].pop(),
    lambda p:p['levels'][0].update(depth_level=True),
    lambda p:p['levels'][1].update(level_id='D01'),
    lambda p:p['levels'][0].update(prerequisite_levels=[20]),
    lambda p:p['levels'][2].update(prerequisite_levels=[1,1]),
    lambda p:p['levels'][0].update(question_ids=['S99']),
    lambda p:p['levels'][0].update(requirements=[]),
    lambda p:p['levels'][0].update(completion_artifacts=[]),
    lambda p:p['completion_policy'].update(automatic_completion_enabled=True),
    lambda p:p['completion_policy'].update(source_leads_complete_levels=0),
])
def test_invalid_or_auto_certifying_protocol_definitions_fail_closed(protocol,mutation):
    mutation(protocol)
    with pytest.raises(ValueError):
        validate_depth_catalog(protocol,QUESTIONS)


def test_all_forty_questions_must_remain_covered(protocol):
    for row in protocol['levels']:
        row['question_ids']=[q for q in row['question_ids'] if q!='S40']
    with pytest.raises(ValueError,match='all forty'):
        validate_depth_catalog(protocol,QUESTIONS)


def test_duplicate_json_keys_cannot_change_protocol_policy(tmp_path):
    path=tmp_path/'duplicate.json';path.write_text('{"levels":[],"levels":[]}')
    with pytest.raises(ValueError,match='duplicate investigation'):
        load_depth_catalog(QUESTIONS,path)


@pytest.mark.parametrize('field,value',[
    ('source_role','OUTCOME_ONLY'),('available_on','2026-01-01'),
    ('availability_basis','PRINTED_DATE_ONLY'),('independently_reviewed',True),
    ('eligible_for_frozen_prediction',True),
])
def test_spoofed_candidate_cannot_supply_investigation_leads(cases,field,value):
    case=deepcopy(cases[0])
    source=next(s for s in case['source_classification'] if s['classification']=='PREDECISION_RESEARCH_CANDIDATE')
    source[field]=value
    with pytest.raises(ValueError):
        build_depth_framework(QUESTIONS,case['source_classification'],reconstruction_cutoff=case['reconstruction_cutoff'])
