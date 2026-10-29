"""Frozen protocol and arithmetic tests; fixtures contain no actual FDA cases."""
import json
import math
import pytest
from research.official_validation import (
    CLASSES, PROTOCOL_PATH, PROTOCOL_SHA256, load_frozen_protocol,
    prepare_operational_validation, synthetic_fixture_diagnostics,
)


def test_protocol_is_frozen_and_has_no_invented_scientific_parameters(tmp_path):
    protocol = load_frozen_protocol()
    assert protocol['outcomes'] == list(CLASSES)
    assert protocol['evaluation_starts_at'] is None
    assert protocol['model_version'] is None
    assert protocol['minimum_sample_size'] is None
    assert protocol['abstention_threshold'] is None
    assert len(PROTOCOL_SHA256) == 64
    copy = tmp_path / 'protocol.json'
    copy.write_bytes(PROTOCOL_PATH.read_bytes())
    assert load_frozen_protocol(copy) == protocol
    copy.write_bytes(copy.read_bytes() + b' ')
    with pytest.raises(ValueError, match='integrity mismatch'):
        load_frozen_protocol(copy)


def test_protocol_modifications_require_new_reviewed_version(tmp_path):
    protocol = load_frozen_protocol()
    protocol['status'] = 'VERIFIED'
    path = tmp_path / 'changed.json'
    path.write_text(json.dumps(protocol))
    with pytest.raises(ValueError):
        load_frozen_protocol(path)


def test_three_class_reference_arithmetic_and_denominators():
    result = synthetic_fixture_diagnostics('three_class_reference_v1')
    metrics = result['metrics']
    assert result['scope'] == 'SYNTHETIC_MATHEMATICAL_DIAGNOSTICS_NOT_PLATFORM_PERFORMANCE'
    assert result['evaluated_platform_predictions'] == 0
    assert metrics['sample_size'] == 4
    assert metrics['scored_sample_size'] == 3
    assert metrics['abstention_count'] == 1
    assert metrics['abstention_rate'] == .25
    assert metrics['coverage'] == .75
    assert metrics['conditional_accuracy'] == pytest.approx(2 / 3)
    assert metrics['confusion_matrix'] == {
        'PASS': {'PASS': 1, 'CRL': 0, 'EXTENSION': 0},
        'CRL': {'PASS': 0, 'CRL': 1, 'EXTENSION': 0},
        'EXTENSION': {'PASS': 1, 'CRL': 0, 'EXTENSION': 0}}
    assert metrics['per_class']['PASS']['precision'] == .5
    assert metrics['per_class']['PASS']['recall'] == 1.
    assert metrics['per_class']['EXTENSION']['precision'] is None
    assert metrics['per_class']['EXTENSION']['recall'] == 0.
    assert metrics['multiclass_brier'] == pytest.approx((.06 + .24 + .86) / 3)
    assert metrics['multiclass_log_loss'] == pytest.approx(-math.log(.8 * .6 * .3) / 3)
    assert metrics['top_label_ece'] == pytest.approx(.4 / 3)
    assert metrics['brier_interval'] is None
    assert metrics['log_loss_interval'] is None
    json.dumps(result, allow_nan=False)


def test_wilson_intervals_are_finite_and_include_sample_proportion():
    metrics = synthetic_fixture_diagnostics('three_class_reference_v1')['metrics']
    for rate, interval in [('conditional_accuracy', 'conditional_accuracy_wilson_95'),
                           ('abstention_rate', 'abstention_wilson_95')]:
        lo, hi = metrics[interval]
        assert 0 <= lo <= metrics[rate] <= hi <= 1
    assert metrics['per_class']['EXTENSION']['precision_wilson_95'] is None
    assert metrics['per_class']['EXTENSION']['recall_wilson_95'][0] == 0
    assert metrics['interval_assumption'] == 'DESCRIPTIVE_BINOMIAL_IID_NOT_VALIDATED_FOR_FDA_COHORTS'


def test_calibration_bins_have_fixed_edges_and_empty_bins_are_null():
    bins = synthetic_fixture_diagnostics('three_class_reference_v1')['metrics']['calibration_bins']
    assert len(bins) == 5
    assert [(b['lower'], b['upper']) for b in bins] == [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1)]
    assert [b['sample_size'] for b in bins] == [0, 0, 0, 2, 1]
    assert bins[0]['observed_accuracy'] is None
    assert bins[3]['mean_confidence'] == .6
    assert bins[3]['observed_accuracy'] == .5


def test_strata_show_small_sample_counts_and_abstention_denominators():
    strata = synthetic_fixture_diagnostics('three_class_reference_v1')['strata']
    assert strata['therapeutic_area']['SYNTHETIC_A']['sample_size'] == 2
    assert strata['therapeutic_area']['SYNTHETIC_B']['abstention_rate'] == .5
    assert strata['decision_year']['2022']['sample_size'] == 1
    assert strata['decision_year']['2022']['conditional_accuracy'] is None
    assert strata['decision_year']['2021']['scored_sample_size'] == 2


@pytest.mark.parametrize('name', ['empty_v1', 'all_abstain_v1'])
def test_no_scored_cases_never_fabricate_performance(name):
    result = synthetic_fixture_diagnostics(name)
    metrics = result['metrics']
    assert metrics['scored_sample_size'] == 0
    assert metrics['conditional_accuracy'] is None
    assert metrics['multiclass_brier'] is None
    assert metrics['multiclass_log_loss'] is None
    assert metrics['top_label_ece'] is None
    assert all(metrics['per_class'][c]['precision'] is None for c in CLASSES)
    assert result['eligible_for_validated_accuracy'] is False


def test_zero_true_class_probability_is_explicit_infinite_log_loss_without_nonfinite_json():
    metrics = synthetic_fixture_diagnostics('zero_probability_v1')['metrics']
    assert metrics['multiclass_brier'] == 2.
    assert metrics['multiclass_log_loss'] is None
    assert metrics['log_loss_is_infinite'] is True
    json.dumps(metrics, allow_nan=False)


@pytest.mark.parametrize('value', ['actual_fda_records', {'independently_verified': True}, None])
def test_diagnostic_entrypoint_does_not_accept_external_records_or_verification_flags(value):
    with pytest.raises(ValueError):
        synthetic_fixture_diagnostics(value)


def test_operational_validation_always_blocked_despite_client_verification_flags():
    row = {'application_id': 'NDA123456', 'review_cycle_id': 'ORIG-001',
           'program_id': 'synthetic', 'program_family': 'synthetic',
           'partition': 'TRAIN', 'evidence_cutoff': '2020-01-01T00:00:00Z',
           'prediction_inputs': [], 'independently_verified': True,
           'review_receipt': {'approved': True, 'reviewer': 'client'},
           'outcome_label': {'independently_verified': True}}
    result = prepare_operational_validation([row],
        evaluation_starts_at='2021-01-01T00:00:00Z', required_fields={'efficacy'})
    assert result['operational_metrics'] is None
    assert result['prediction_action'] == 'ABSTAIN'
    assert result['prediction_readiness'] == 'NOT_READY'
    assert result['independently_verified_decisions'] == 0
    assert result['evaluated_predictions'] == 0
    assert result['eligible_for_validated_accuracy'] is False
    assert result['readiness']['records'][0]['eligible_for_training_or_evaluation'] is False
    assert 'MISSING_REQUIRED_EVIDENCE' in result['readiness']['records'][0]['blocking_reasons']
    assert result['protocol']['evaluation_starts_at'] is None


def test_operational_wrapper_preserves_family_and_chronology_safeguards():
    rows = [
        {'application_id': 'NDA123456', 'review_cycle_id': 'ORIG-001',
         'program_family': 'synthetic', 'partition': 'TRAIN',
         'evidence_cutoff': '2022-01-01T00:00:00Z'},
        {'application_id': 'NDA123456', 'review_cycle_id': 'SUPPL-002',
         'program_family': 'synthetic', 'partition': 'EVALUATION',
         'evidence_cutoff': '2021-01-01T00:00:00Z'}]
    result = prepare_operational_validation(rows,
        evaluation_starts_at='2021-01-01T00:00:00Z', required_fields={'efficacy'})
    first = result['readiness']['records'][0]['blocking_reasons']
    assert 'TRAINING_CUTOFF_NOT_BEFORE_EVALUATION' in first
    assert 'RELATED_APPLICATION_SPLIT_LEAKAGE' in first
    assert 'RELATED_PROGRAM_SPLIT_LEAKAGE' in first
