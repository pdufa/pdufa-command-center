"""Real population audit metadata and synthetic promotion guards, not FDA accuracy."""
from copy import deepcopy
import json

import pytest

from research.tnxp_resilient_population import AUDIT, build_population_issue
from research.fda_holdout_dashboard_snapshot import build_dashboard_snapshot
from datetime import date


def test_sponsor_arithmetic_explanation_does_not_establish_sap_compliance():
    row=build_population_issue()
    assert row['randomized_population']['total']==row['reported_safety_population']['total']==457
    assert row['reported_efficacy_population']['total']==456
    assert row['randomized_population']['placebo']-row['reported_efficacy_population']['placebo']==1
    assert row['protocol_compliance_status']=='NOT_ESTABLISHED'
    assert row['independently_adjudicated'] is False
    assert row['eligible_for_predecision_features'] is False
    assert row['effect_on_proposed_fda_decision']=='ABSTAIN_NO_CERTIFIED_PROBABILITY_EFFECT'
    assert row['approval_probability'] is None


@pytest.mark.parametrize('field,value',[
    ('protocol_compliance_status','COMPLIANT'),('independently_adjudicated',True),
    ('eligible_for_validated_accuracy',True),('eligible_for_predecision_features',True),
    ('source_bytes_retained',1),('trading_authorized',True),
    ('original_prediction_cutoff','2025-08-14'),
])
def test_unresolved_audit_cannot_self_promote(field,value):
    row=json.loads(AUDIT.read_text());row[field]=value
    with pytest.raises(ValueError):build_population_issue(row)


def test_internal_sap_date_is_not_promoted_to_public_availability():
    row=json.loads(AUDIT.read_text())
    sap=next(s for s in row['sources'] if s['id']=='RESILIENT-SAP-FINAL-V1')
    assert sap['document_date']=='2023-10-17' and sap['public_availability_verified'] is False
    sap['public_availability_verified']=True
    with pytest.raises(ValueError,match='availability'):build_population_issue(row)


def test_changed_or_unsafe_source_and_rounded_population_rejected():
    for alteration in ('source','denominator','duplicate'):
        row=json.loads(AUDIT.read_text())
        if alteration=='source':row['sources'][0]['url']='javascript:alert(1)'
        if alteration=='denominator':row['reported_efficacy_population']['placebo']=226
        if alteration=='duplicate':row['sources'][0]=deepcopy(row['sources'][1])
        with pytest.raises(ValueError):build_population_issue(row)


def test_dossier_keeps_tnxp_issue_separate_from_frozen_features_and_other_cases():
    cases=build_dashboard_snapshot(as_of=date(2026,10,28))['caseReports']
    for case in cases:
        issues=case['scientific_dossier']['scientific_issues']
        assert len(issues)==(1 if case['event_key']=='TNXP|2025-08-15' else 0)
        assert case['decision_contract']['predicted_decision']=='ABSTAIN'
        assert all(p is None for p in case['decision_contract']['probabilities'].values())
        assert len(case['scientific_dossier']['extended_investigation_framework']['levels'])==50
        assert len(case['depth_worklist'])==20
        for layer in case['scientific_dossier']['layers']:
            for q in layer['questions']:
                assert q['historical_prediction_cutoff'] is None
                assert q['supporting_findings']==q['contradictory_findings']==[]
                assert q['confidence_grade']=='NOT_ESTABLISHED'
                assert q['effect_on_proposed_fda_decision']=='NO_CERTIFIED_EFFECT_ABSTAIN'


def test_original_fda_label_corrobates_denominator_without_sap_authority_or_historical_features():
    row=build_population_issue()
    context=row['postdecision_context']
    assert context['reported_efficacy_population']['total']==456
    assert context['source_role']=='OUTCOME_ONLY'
    assert context['protocol_exclusion_authority_established'] is False
    assert context['eligible_for_predecision_features'] is False
    assert row['protocol_compliance_status']=='NOT_ESTABLISHED'
    for field,value in [('source_role','PREDECISION_RESEARCH'),
                        ('protocol_exclusion_authority_established',True),
                        ('eligible_for_predecision_features',True)]:
        changed=json.loads(AUDIT.read_text());changed['postdecision_context'][field]=value
        with pytest.raises(ValueError,match='FDA label'):build_population_issue(changed)


def test_source_order_does_not_change_supplementary_index_binding():
    row=json.loads(AUDIT.read_text());row['sources'].reverse()
    assert build_population_issue(row)['protocol_compliance_status']=='NOT_ESTABLISHED'
