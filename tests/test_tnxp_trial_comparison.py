"""Source comparison and synthetic corruption guards, not prediction validation."""
from copy import deepcopy
import json

import pytest

from research.tnxp_trial_comparison import COMPARISON_PATH, build_tnxp_trial_comparison


def packet():
    return json.loads(COMPARISON_PATH.read_text())


def test_real_three_trial_matrix_preserves_mixed_primary_replication_and_zero_certification():
    source=packet(); original=deepcopy(source)
    result=build_tnxp_trial_comparison(source)
    assert source==original
    rows={r['trial_id']:r for r in result['trials']}
    assert rows['F304']['primary_analysis']['p_value']=='0.010'
    assert rows['F306']['primary_analysis']['p_value']=='0.115'
    assert rows['F306']['primary_analysis']['source_reported_outcome']=='FAILED'
    assert rows['F306']['sensitivity_analyses'][0]['p_value']=='0.014'
    assert rows['F307']['primary_analysis']['p_value']=='0.00005'
    summary=result['comparison_summary']
    assert summary['source_reported_positive_primary_trials']==['F304','F307']
    assert summary['source_reported_failed_primary_trials']==['F306']
    assert summary['predicted_decision']=='ABSTAIN'
    assert summary['pooled_p_value'] is summary['pooled_effect'] is summary['prediction_accuracy'] is None
    assert all(v is None for v in summary['probabilities'].values())
    assert summary['independently_completed_assessments']==summary['independently_completed_levels']==0
    assert summary['within_program_comparison_is_independent_fda_cohort'] is False


@pytest.mark.parametrize('change',['swap','promote','remove','method','outcome'])
def test_favorable_rally_sensitivity_does_not_replace_failed_primary(change):
    source=packet(); rally=source['trials'][1]
    if change=='swap':rally['primary_analysis'],rally['sensitivity_analyses'][0]=rally['sensitivity_analyses'][0],rally['primary_analysis']
    if change=='promote':rally['primary_analysis']['p_value']='0.014'
    if change=='remove':rally['sensitivity_analyses']=[]
    if change=='method':rally['primary_analysis']['method']='MMRM_WITHOUT_MULTIPLE_IMPUTATION'
    if change=='outcome':rally['primary_analysis']['source_reported_outcome']='POSITIVE'
    with pytest.raises(ValueError):build_tnxp_trial_comparison(source)


def test_unverified_relief_and_resilient_sensitivity_values_remain_unknown():
    result=build_tnxp_trial_comparison()
    relief,resilient=result['trials'][0],result['trials'][2]
    assert all(relief['populations'][field] is None for field in ('randomized_total','efficacy_total','safety_total'))
    assert relief['design']['sites'] is relief['design']['duration_weeks'] is None
    assert relief['sensitivity_analyses'][0]['standard_error'] is None
    assert resilient['sensitivity_analyses']==[]
    source=packet(); source['trials'][0]['populations']['randomized_total']=503
    with pytest.raises(ValueError,match='populations'):build_tnxp_trial_comparison(source)
    source=packet();source['trials'][2]['sensitivity_analyses']=[deepcopy(source['trials'][0]['sensitivity_analyses'][0])]
    with pytest.raises(ValueError,match='sensitivity'):build_tnxp_trial_comparison(source)


def test_resilient_population_difference_and_safety_causality_are_not_silently_resolved():
    result=build_tnxp_trial_comparison(); row=result['trials'][2]
    assert row['populations']['randomized_total']==row['populations']['safety_total']==457
    assert row['populations']['efficacy_total']==456
    assert row['safety']['causality_status']=='NOT_INDEPENDENTLY_ADJUDICATED'
    assert result['comparison_summary']['resilient_exclusion_compliance_status']=='NOT_ESTABLISHED'
    source=packet(); source['trials'][2]['populations']['efficacy_total']=457
    with pytest.raises(ValueError):build_tnxp_trial_comparison(source)
    source=packet(); source['trials'][1]['safety']['source_reported_events'][0]['independently_adjudicated']=True
    with pytest.raises(ValueError,match='causality'):build_tnxp_trial_comparison(source)


@pytest.mark.parametrize('field,value',[
    ('research_only',False),('original_prediction_cutoff','2025-08-14'),
    ('eligible_for_predecision_features',True),('eligible_for_validated_accuracy',True),
    ('trading_authorized',1),('independently_completed_assessments',True),
    ('independently_completed_levels',1),('assembled_on','2025-08-14'),
])
def test_retrospective_research_cannot_self_promote(field,value):
    source=packet();source[field]=value
    with pytest.raises(ValueError):build_tnxp_trial_comparison(source)


@pytest.mark.parametrize('change',['source_url','source_date','clock','hash','bytes','review','reference','duplicate'])
def test_source_identity_availability_and_adjudication_are_preserved(change):
    source=packet()
    if change=='source_url':source['sources'][0]['source_url']='https://example.com/forged.htm'
    if change=='source_date':source['sources'][0]['document_date']='2026-01-01'
    if change=='clock':source['sources'][0]['public_availability_verified']=True
    if change=='hash':source['sources'][0]['original_document_sha256']='a'*64
    if change=='bytes':source['sources'][0]['source_bytes_retained']=True
    if change=='review':source['sources'][0]['independently_reviewed']=True
    if change=='reference':source['trials'][1]['primary_analysis']['source_id']='TNXP-RESILIENT-EFFECT-20240610'
    if change=='duplicate':source['sources'][2]=deepcopy(source['sources'][0])
    with pytest.raises(ValueError):build_tnxp_trial_comparison(source)


@pytest.mark.parametrize('container',['root','trial','analysis','population','source','safety'])
def test_forecast_metrics_cannot_be_injected_into_unadjudicated_comparison(container):
    source=packet()
    targets={'root':source,'trial':source['trials'][0],
        'analysis':source['trials'][0]['primary_analysis'],'population':source['trials'][0]['populations'],
        'source':source['sources'][0],'safety':source['trials'][0]['safety']}
    targets[container]['approval_probability']=0.99
    with pytest.raises(ValueError):build_tnxp_trial_comparison(source)
