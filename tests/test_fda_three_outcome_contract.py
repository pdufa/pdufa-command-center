"""Three-outcome research contracts never certify real FDA forecasts."""
from copy import deepcopy
from datetime import date, datetime
import json
from pathlib import Path

import pytest

from research.fda_outcome_provenance_gate import (
    build_outcome_provenance_status,
    build_unvalidated_decision_contract,
    validate_unvalidated_decision_contract,
)
from research.fda_science_outcome_status_view import build_research_status

ROOT = Path(__file__).resolve().parents[1]


def real_packet():
    return json.loads((ROOT/'research/evidence/2025_holdout_predecision_reconstruction.json').read_text())


def test_six_real_historical_outcomes_do_not_become_three_class_predictions():
    packet=real_packet()
    dossiers=[{'event_key':c['event_key'], 'research_only':True,
               'original_prediction_cutoff':None,
               'schema_version':'fda-science-research-dossier-v1'} for c in packet['cases']]
    result=build_outcome_provenance_status(packet,dossiers)
    assert len(result['cases']) == 6 and result['validated_predictions'] == 0
    for case in result['cases']:
        contract=case['decision_contract']
        assert validate_unvalidated_decision_contract(contract) is contract
        assert contract['predicted_decision']=='ABSTAIN'
        assert contract['probabilities']=={'PASS':None,'CRL':None,'EXTENSION':None}
        assert contract['science_readiness_grade']=='NOT_READY'
        assert contract['prediction_confidence_grade']=='NOT_ESTABLISHED'
        assert contract['trading_authorized'] is False
        assert contract['eligible_for_validated_accuracy'] is False
        assert case['approval_probability'] is None  # Legacy binary API is preserved.


def test_extension_requires_formal_target_revision_and_a_prespecified_horizon():
    contract=build_unvalidated_decision_contract(as_of=date(2026,10,28))
    assert contract['target_classes']==['PASS','CRL','EXTENSION']
    assert contract['target_definition_status']=='PRESPECIFIED_REVIEW_HORIZON_REQUIRED'
    assert 'formal FDA revision' in contract['class_definitions']['EXTENSION']
    assert 'missed date' in contract['class_definitions']['EXTENSION']
    assert contract['extension_is_binary_nonapproval'] is False
    assert contract['last_updated']=='2026-10-28'
    assert contract['uncertainty_range'] is None


@pytest.mark.parametrize('key,value',[
    ('predicted_decision','PASS'),('predicted_decision','CRL'),('predicted_decision','EXTENSION'),
    ('probabilities',{'PASS':0.8,'CRL':0.1,'EXTENSION':0.1}),
    ('probabilities',{'PASS':None,'CRL':None}),
    ('science_readiness_grade','READY'),('prediction_confidence_grade','HIGH'),
    ('historical_validation_status','VALIDATED'),('eligible_for_validated_accuracy',True),
    ('trading_authorized',True),('trading_authorized',0),
    ('model_version','synthetic-validated-v1'),('prediction_version','historical-action-copy'),
    ('target_classes',['PASS','CRL']),('extension_is_binary_nonapproval',True),
    ('source_verification_status','VERIFIED'),('last_updated','2026-02-30'),
])
def test_research_contract_rejects_unsupported_promotion_and_malformed_payloads(key,value):
    contract=build_unvalidated_decision_contract(blockers=['source_bytes_missing'])
    contract[key]=value
    with pytest.raises(ValueError):
        validate_unvalidated_decision_contract(contract)


def test_missing_fields_and_extra_validation_claims_are_rejected():
    contract=build_unvalidated_decision_contract()
    missing=deepcopy(contract); missing.pop('probabilities')
    forged=deepcopy(contract); forged['validated_accuracy']=0.9
    for changed in (missing,forged,None):
        with pytest.raises(ValueError):
            validate_unvalidated_decision_contract(changed)


@pytest.mark.parametrize('value',[False,datetime(2026,10,28),'2026-10-28'])
def test_snapshot_date_does_not_accept_implicit_or_ambiguous_types(value):
    with pytest.raises(ValueError):
        build_unvalidated_decision_contract(as_of=value)


def test_status_view_exposes_three_class_abstention_without_replacing_legacy_fields():
    view=build_research_status(real_packet())
    assert len(view['cases'])==6
    for case in view['cases']:
        assert case['outcomeDecision']=='ABSTAIN' and case['approvalProbability'] is None
        assert case['decisionContract']['probabilities']=={'PASS':None,'CRL':None,'EXTENSION':None}
