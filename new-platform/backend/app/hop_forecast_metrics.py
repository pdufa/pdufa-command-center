"""Transparent binary outcome metrics for HOP historical research backtests.

These compute *mathematical* metrics on explicitly supplied predictions and
labels. They do not independently verify the input cohort or its labels and
must never be reported as real FDA validation before source/adjudication gates.
"""
from __future__ import annotations

from math import isfinite, log, sqrt
from collections import defaultdict

_Z95 = 1.959963984540054
_EPS = 1e-15


def _auc_rank(pairs: list[tuple[float, int]]) -> float | None:
    """Tie-correct AUROC as Mann-Whitney U, O(n log n) instead of O(n^2)."""
    pos = sum(y for _, y in pairs)
    neg = len(pairs) - pos
    if not pos or not neg:
        return None
    ordered = sorted(pairs, key=lambda x: x[0])
    positive_rank_sum = 0.0
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][0] == ordered[i][0]:
            j += 1
        midpoint_rank = (i + 1 + j) / 2.0
        positive_rank_sum += midpoint_rank * sum(y for _, y in ordered[i:j])
        i = j
    return (positive_rank_sum - pos * (pos + 1) / 2.0) / (pos * neg)


def summarize_binary_forecasts(
    predictions: list[tuple[float, int]],
    *,
    eligible_count: int,
    baseline_probabilities: list[float] | None = None,
) -> dict:
    """Score only predictions actually emitted; abstentions retain denominator.

    Binary labels must be 1 (FDA approval at specified action) or 0
    (documented Complete Response at that cycle). Real label verification,
    cohort completeness, chronological splits and any true FDA relevance
    must be established *upstream*. Model selection and thresholds must be
    frozen before evaluation on an untouched cohort.
    """
    if type(eligible_count) is not int or eligible_count < 0:
        raise ValueError("Eligible test count must be a nonnegative integer")
    if not isinstance(predictions, list) or len(predictions) > eligible_count:
        raise ValueError("Forecast rows may not exceed eligible holdout count")
    if baseline_probabilities is not None and (
        not isinstance(baseline_probabilities, list)
        or len(baseline_probabilities) != len(predictions)
    ):
        raise ValueError("Baseline probabilities must match covered forecasts")
    clean = []
    for value in predictions:
        if not isinstance(value, tuple) or len(value) != 2:
            raise ValueError("Expected (probability, withheld binary label)")
        p, outcome = value
        if (type(p) not in (int, float) or not isfinite(p) or not 0 <= p <= 1
                or type(outcome) is not int or outcome not in (0, 1)):
            raise ValueError("Probabilities must be finite in [0,1]; labels 0 or 1")
        clean.append((float(p), outcome))
    baselines = []
    for p in baseline_probabilities or []:
        if type(p) not in (int, float) or not isfinite(p) or not 0 <= p <= 1:
            raise ValueError("Baseline probability must be finite in [0,1]")
        baselines.append(float(p))
    n = len(clean)
    empty = {
        "status": "MATH_METRICS_ONLY_NOT_INDEPENDENT_FDA_VALIDATION",
        "eligibleTestCount": eligible_count,
        "predictedCount": n,
        "abstainedCount": eligible_count - n,
        "coverage": n / eligible_count if eligible_count else None,
        "threshold": 0.5,
        "brierScore": None, "logLoss": None, "accuracy": None,
        "balancedAccuracy": None, "rocAuc": None,
        "expectedCalibrationError": None, "calibrationBins": [],
        "accuracyWilson95": None,
        "baselineBrierScore": None, "brierSkillScore": None,
        "modelHistoricallyValidated": False,
    }
    if not n:
        return empty
    brier = sum((p - y)**2 for p, y in clean) / n
    logloss = -sum(y * log(max(_EPS, min(1-_EPS, p))) +
                   (1-y)*log(max(_EPS, min(1-_EPS, 1-p)))
                   for p, y in clean) / n
    outcomes = [y for _, y in clean]
    positive = sum(outcomes)
    negative = n - positive
    correct = sum((p >= 0.5) == bool(y) for p, y in clean)
    accuracy = correct / n
    tpr = (sum(p >= 0.5 for p, y in clean if y) / positive) if positive else None
    tnr = (sum(p < 0.5 for p, y in clean if not y) / negative) if negative else None
    balanced = (tpr + tnr) / 2 if positive and negative else None
    bins = defaultdict(list)
    for p, y in clean:
        bins[min(int(p * 5), 4)].append((p, y))
    calibration = []
    ece = 0.0
    for index in range(5):
        segment = bins[index]
        if not segment:
            continue
        mean_p = sum(p for p, _ in segment) / len(segment)
        observed = sum(y for _, y in segment) / len(segment)
        ece += (len(segment) / n) * abs(mean_p - observed)
        calibration.append({
            "lowInclusive": index/5, "highExclusiveExceptOne": (index+1)/5,
            "count": len(segment), "meanProbability": mean_p,
            "observedApprovalRate": observed,
        })
    center = (accuracy + _Z95**2/(2*n))/(1 + _Z95**2/n)
    half_width = _Z95*sqrt(accuracy*(1-accuracy)/n + _Z95**2/(4*n*n))/(1+_Z95**2/n)
    baseline_brier = (sum((p-y)**2 for p, (_, y) in zip(baselines, clean)) / n
                      if baseline_probabilities is not None else None)
    empty.update({
        "brierScore": brier,
        "logLoss": logloss,
        "accuracy": accuracy,
        "balancedAccuracy": balanced,
        "rocAuc": _auc_rank(clean),
        "expectedCalibrationError": ece,
        "calibrationBins": calibration,
        "accuracyWilson95": [max(0.0, center-half_width), min(1.0, center+half_width)],
        "baselineBrierScore": baseline_brier,
        "brierSkillScore": (1 - brier/baseline_brier
                            if baseline_brier is not None and baseline_brier > 0
                            else None),
    })
    return empty
