"""Frozen protocol and synthetic metric diagnostics; no operational evaluation.

Operational inputs only produce readiness blockers. The public metric entry
point accepts names of built-in synthetic fixtures, never outcome data or caller
verification assertions. No result is a validated platform performance claim.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path

from research.official_history_readiness import prepare_chronological_backtest

PROTOCOL_SHA256 = '0382810f6dda4c83402d18409d76dd1de3411db2da52292a46a431a4624a9d0f'
PROTOCOL_PATH = Path(__file__).parent / 'evidence' / 'official_validation_protocol_v1.json'
CLASSES = ('PASS', 'CRL', 'EXTENSION')


def load_frozen_protocol(path=PROTOCOL_PATH):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('frozen validation protocol integrity mismatch; create a new reviewed version')
    return json.loads(raw)


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def _wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    proportion = successes / total
    scale = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / scale
    radius = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / scale
    return [max(0.0, center - radius), min(1.0, center + radius)]


def _summarize(rows):
    """Internal arithmetic on trusted built-in fixtures, never evidence review."""
    confusion = {true: {predicted: 0 for predicted in CLASSES} for true in CLASSES}
    bins = [{'lower': i / 5, 'upper': (i + 1) / 5, 'sample_size': 0,
             'confidence_sum': 0.0, 'correct': 0} for i in range(5)]
    scored = 0
    abstained = 0
    correct = 0
    brier = 0.0
    loss = 0.0
    infinite = False
    for row in rows:
        true = row['outcome']
        probabilities = row['probabilities']
        if probabilities is None:
            abstained += 1
            continue
        if (set(probabilities) != set(CLASSES)
                or any(type(p) not in (int, float) or not math.isfinite(p) or p < 0 or p > 1
                       for p in probabilities.values())
                or not math.isclose(sum(probabilities.values()), 1.0, abs_tol=1e-12)):
            raise ValueError('finite normalized three-class probabilities required')
        predicted = max(CLASSES, key=lambda label: probabilities[label])
        confidence = probabilities[predicted]
        hit = int(true == predicted)
        confusion[true][predicted] += 1
        scored += 1
        correct += hit
        brier += sum((probabilities[label] - int(label == true)) ** 2 for label in CLASSES)
        if probabilities[true] == 0:
            infinite = True
        else:
            loss -= math.log(probabilities[true])
        bucket = bins[min(int(confidence * 5), 4)]
        bucket['sample_size'] += 1
        bucket['confidence_sum'] += confidence
        bucket['correct'] += hit
    per_class = {}
    for label in CLASSES:
        tp = confusion[label][label]
        predicted_count = sum(confusion[true][label] for true in CLASSES)
        actual_count = sum(confusion[label].values())
        per_class[label] = {'true_positive': tp, 'predicted_count': predicted_count,
                            'actual_scored_count': actual_count,
                            'precision': _ratio(tp, predicted_count),
                            'recall': _ratio(tp, actual_count),
                            'precision_wilson_95': _wilson(tp, predicted_count),
                            'recall_wilson_95': _wilson(tp, actual_count)}
    ece = 0.0
    for bucket in bins:
        n = bucket['sample_size']
        mean = _ratio(bucket.pop('confidence_sum'), n)
        observed = _ratio(bucket['correct'], n)
        bucket['mean_confidence'] = mean
        bucket['observed_accuracy'] = observed
        bucket['observed_accuracy_wilson_95'] = _wilson(bucket['correct'], n)
        if n:
            ece += n * abs(mean - observed)
    return {'sample_size': len(rows), 'scored_sample_size': scored,
            'abstention_count': abstained, 'abstention_rate': _ratio(abstained, len(rows)),
            'abstention_wilson_95': _wilson(abstained, len(rows)),
            'coverage': _ratio(scored, len(rows)),
            'conditional_accuracy': _ratio(correct, scored),
            'conditional_accuracy_wilson_95': _wilson(correct, scored),
            'confusion_matrix': confusion, 'per_class': per_class,
            'multiclass_brier': _ratio(brier, scored),
            'multiclass_log_loss': None if infinite else _ratio(loss, scored),
            'log_loss_is_infinite': infinite,
            'brier_interval': None, 'log_loss_interval': None,
            'score_interval_status': 'REQUIRES_PRESPECIFIED_FAMILY_CLUSTER_RESAMPLING',
            'calibration_bins': bins, 'top_label_ece': _ratio(ece, scored),
            'interval_assumption': 'DESCRIPTIVE_BINOMIAL_IID_NOT_VALIDATED_FOR_FDA_COHORTS'}


def _fixture(name):
    if name == 'three_class_reference_v1':
        return [
            {'outcome': 'PASS', 'probabilities': {'PASS': .8, 'CRL': .1, 'EXTENSION': .1},
             'therapeutic_area': 'SYNTHETIC_A', 'decision_year': '2020'},
            {'outcome': 'CRL', 'probabilities': {'PASS': .2, 'CRL': .6, 'EXTENSION': .2},
             'therapeutic_area': 'SYNTHETIC_A', 'decision_year': '2021'},
            {'outcome': 'EXTENSION', 'probabilities': {'PASS': .6, 'CRL': .1, 'EXTENSION': .3},
             'therapeutic_area': 'SYNTHETIC_B', 'decision_year': '2021'},
            {'outcome': 'PASS', 'probabilities': None,
             'therapeutic_area': 'SYNTHETIC_B', 'decision_year': '2022'}]
    if name == 'all_abstain_v1':
        rows = _fixture('three_class_reference_v1')
        for row in rows:
            row['probabilities'] = None
        return rows
    if name == 'zero_probability_v1':
        return [{'outcome': 'CRL', 'probabilities': {'PASS': 1., 'CRL': 0., 'EXTENSION': 0.},
                 'therapeutic_area': 'SYNTHETIC_A', 'decision_year': '2020'}]
    if name == 'empty_v1':
        return []
    raise ValueError('only built-in synthetic fixture names are accepted')


def synthetic_fixture_diagnostics(fixture_name):
    protocol = load_frozen_protocol()
    rows = _fixture(fixture_name)
    strata = {}
    for key in ('therapeutic_area', 'decision_year'):
        strata[key] = {value: _summarize([row for row in rows if row[key] == value])
                       for value in sorted({row[key] for row in rows})}
    return {'schema_version': 'official-validation-fixture-diagnostics-v1',
            'scope': 'SYNTHETIC_MATHEMATICAL_DIAGNOSTICS_NOT_PLATFORM_PERFORMANCE',
            'fixture_name': fixture_name, 'protocol_sha256': PROTOCOL_SHA256,
            'protocol_status': protocol['status'],
            'metrics': _summarize(rows), 'strata': strata,
            'independently_verified_decisions': 0, 'evaluated_platform_predictions': 0,
            'eligible_for_validated_accuracy': False, 'prediction_action': 'ABSTAIN'}


def prepare_operational_validation(records, *, evaluation_starts_at, required_fields):
    """Triage only; operational metrics cannot be unlocked by caller flags.

    Boundary and field proposals are diagnostics, not authorization to override
    the frozen protocol's unresolved scientific parameters.
    """
    protocol = load_frozen_protocol()
    readiness = prepare_chronological_backtest(records,
        evaluation_starts_at=evaluation_starts_at, required_fields=required_fields)
    return {'schema_version': 'official-operational-validation-preparation-v1',
            'protocol_sha256': PROTOCOL_SHA256, 'protocol': deepcopy(protocol),
            'readiness': readiness, 'operational_metrics': None,
            'blocking_reasons': ['INDEPENDENT_ADJUDICATION_NOT_ESTABLISHED',
                                 'SCIENTIFIC_PROTOCOL_PARAMETERS_NOT_PRESPECIFIED',
                                 'MODEL_AND_CALIBRATION_NOT_VALIDATED'],
            'independently_verified_decisions': 0, 'evaluated_predictions': 0,
            'eligible_for_validated_accuracy': False,
            'prediction_readiness': 'NOT_READY', 'prediction_action': 'ABSTAIN'}
