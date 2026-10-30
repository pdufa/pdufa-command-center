"""Structural review of draft definitions is not scientific evidence validation."""
from copy import deepcopy
import json

import pytest

from research.scientific_field_catalog import (
    BASE_KEYS, LEGACY, PARTS, QUESTIONS, DOMAIN_SPECS, build_scientific_catalog, read_json,
)


def parts():
    return [read_json(PARTS/name) for name in ('bio_moa.json','trial_efficacy.json','safety_cmc.json','precedent_validation.json')]


def test_six_hundred_fifty_distinct_definitions_and_fifty_task_contracts():
    catalog=build_scientific_catalog()
    assert len(catalog['fields'])==catalog['defined_slots']==650
    assert len({r['id'] for r in catalog['fields']})==650
    assert catalog['independently_validated_definitions']==0
    assert catalog['prediction_readiness']=='NOT_READY' and catalog['predicted_decision']=='ABSTAIN'
    assert catalog['canonical_assessment_ids']==[f'S{i:02d}' for i in range(1,41)]
    for code,_,count in DOMAIN_SPECS:
        assert sum(f['segment']==code for f in catalog['fields'])==count
    assert len(catalog['investigation_levels'])==50
    for level in catalog['investigation_levels']:
        assert level['input_field_ids'] and level['assessment_criteria'] and level['source_requirements']
        assert level['uncertainty_handling']
        assert level['readiness_conditions']['automatic_completion'] is False
        assert level['independently_completed'] is False
    assert all(f['definition_independently_validated'] is False and f['clinical_value'] is None for f in catalog['fields'])


def test_original_eight_definitions_and_canonical_mappings_are_unchanged():
    legacy=read_json(LEGACY)
    by_id={f['id']:f for f in build_scientific_catalog()['fields']}
    assert len(legacy['fields'])==8
    for old in legacy['fields']:
        assert {key:by_id[old['id']][key] for key in BASE_KEYS}==old
        assert by_id[old['id']]['mapping_status']=='LEGACY_MAPPING_PRESERVED_REQUIRES_SCIENTIFIC_REVIEW'


def test_canonical_questions_are_preserved_and_conditional_requirements_do_not_exempt_missing_fields():
    catalog=build_scientific_catalog()
    assert catalog['canonical_assessments']==read_json(QUESTIONS)['questions']
    policy=catalog['applicability_policy']
    assert policy['exemptions_require_independent_review'] is True
    assert policy['missing_evidence_establishes_inapplicability'] is False
    assert policy['automatic_denominator_reduction_allowed'] is False
    by_id={f['id']:f for f in catalog['fields']}
    assert 'Children or adolescents' in by_id['TRIAL-049']['applicability']
    assert 'surrogate endpoint' in by_id['EFFICACY-013']['applicability']
    assert 'binding from neutralizing' in by_id['SAFETY-055']['assessment_criteria'][0]
    assert 'planned validation is not completed validation' in by_id['CMC-050']['assessment_criteria'][0]
    assert 'field counts are not independent studies' in catalog['correlation_policy']


def test_outcome_and_model_evaluation_fields_do_not_authorize_same_case_features():
    catalog=build_scientific_catalog()
    assert 'Same-case FDA actions' in catalog['evidence_role_policy']
    fields={r['id']:r for r in catalog['fields']}
    for field in ('PRECEDENT-020','PRECEDENT-021','PRECEDENT-024','PRECEDENT-050'):
        assert any('never a predecision feature' in text for text in fields[field]['uncertainty_handling'])
    assert any('held-out evaluation context' in text for text in fields['VALIDATION-028']['uncertainty_handling'])


@pytest.mark.parametrize('change',['missing','duplicate','unknown_assessment','placeholder','certificate','bad_bool'])
def test_missing_padded_or_self_certifying_catalog_fragments_rejected(change):
    fragments=parts();row=fragments[0]['domains']['BIO'][0]
    if change=='missing':fragments[0]['domains']['BIO'].pop()
    elif change=='duplicate':fragments[0]['domains']['BIO'].append(deepcopy(row))
    elif change=='unknown_assessment':row['assessment_ids']=['S41']
    elif change=='placeholder':row['definition']='Placeholder slot 500'
    elif change=='certificate':row['scientifically_validated']=True
    elif change=='bad_bool':row['mandatory']=1
    with pytest.raises(ValueError):build_scientific_catalog(parts=fragments)


def test_catalog_content_digest_changes_with_a_reviewable_definition():
    first=build_scientific_catalog()
    assert first['catalog_sha256']==build_scientific_catalog()['catalog_sha256']
    fragments=parts();fragments[0]['domains']['BIO'][0]['definition']+=' Require an explicit scope review.'
    assert build_scientific_catalog(parts=fragments)['catalog_sha256']!=first['catalog_sha256']
