"""Synthetic math tests only: no historical FDA prediction performance claims."""
from datetime import date
import math
import pytest

from app.hop_forecast_metrics import summarize_binary_forecasts
from app.hop_backtest import walk_forward_backtest
from app.hop_outcome_cohort import OutcomeObservation

def test_perfect_ranking_and_accurate_probabilities():
    result = summarize_binary_forecasts(
        [(0.9, 1), (0.1, 0)], eligible_count=3,
        baseline_probabilities=[0.5, 0.5],
    )
    assert result["status"] == "MATH_METRICS_ONLY_NOT_INDEPENDENT_FDA_VALIDATION"
    assert result["eligibleTestCount"] == 3
    assert result["predictedCount"] == 2
    assert result["abstainedCount"] == 1
    assert result["coverage"] == pytest.approx(2/3)
    assert result["brierScore"] == pytest.approx(0.01)
    assert result["logLoss"] == pytest.approx(-math.log(0.9))
    assert result["accuracy"] == 1.0
    assert result["balancedAccuracy"] == 1.0
    assert result["rocAuc"] == 1.0
    assert result["expectedCalibrationError"] == pytest.approx(0.1)
    assert result["baselineBrierScore"] == pytest.approx(0.25)
    assert result["brierSkillScore"] == pytest.approx(0.96)
    assert result["accuracyWilson95"][0] < 1
    assert result["accuracyWilson95"][1] == 1.0
    assert result["modelHistoricallyValidated"] is False
    assert sum(x["count"] for x in result["calibrationBins"]) == 2

def test_reversed_rank_and_ties_not_overstated():
    r = summarize_binary_forecasts([(0.1, 1), (0.9, 0)], eligible_count=2)
    assert r["rocAuc"] == 0
    assert r["accuracy"] == 0
    assert r["balancedAccuracy"] == 0
    ties = summarize_binary_forecasts([(0.5, 1), (0.5, 0)], eligible_count=2)
    assert ties["rocAuc"] == pytest.approx(0.5)
    assert ties["brierScore"] == 0.25
    assert ties["accuracy"] == 0.5
    assert ties["expectedCalibrationError"] == 0

def test_one_class_discrimination_and_balanced_accuracy_are_undefined():
    result = summarize_binary_forecasts([(0.8, 1), (0.6, 1)], eligible_count=2)
    assert result["rocAuc"] is None
    assert result["balancedAccuracy"] is None
    assert result["accuracy"] == 1

def test_no_predictions_is_abstention_not_model_accuracy():
    result = summarize_binary_forecasts([], eligible_count=4, baseline_probabilities=[])
    assert result["predictedCount"] == 0
    assert result["coverage"] == 0
    assert result["abstainedCount"] == 4
    assert result["accuracy"] is None
    assert result["rocAuc"] is None
    assert result["brierScore"] is None
    assert result["baselineBrierScore"] is None
    assert result["calibrationBins"] == []
    zero = summarize_binary_forecasts([], eligible_count=0)
    assert zero["coverage"] is None

def test_boundary_probabilities_do_not_overflow_log_loss():
    result = summarize_binary_forecasts([(0.0, 1), (1.0, 0)], eligible_count=2)
    assert math.isfinite(result["logLoss"])
    assert result["logLoss"] > 20
    assert result["brierScore"] == 1.0

@pytest.mark.parametrize("pairs,eligible", [
    ([(1.1, 1)], 1),
    ([(-0.2, 0)], 1),
    ([(float("nan"), 1)], 1),
    ([(float("inf"), 0)], 1),
    ([(True, 1)], 1),
    ([(0.5, True)], 1),
    ([(0.5, 2)], 1),
    ([(0.5, "PASS")], 1),
    ([(0.5, 0), (0.5, 1)], 1),
    ([(0.5, 0)], True),
    ([(0.5, 0)], -1),
    ([{"approval":0.5}], 1),
])
def test_invalid_probabilities_or_fake_binary_labels_rejected(pairs, eligible):
    with pytest.raises(ValueError):
        summarize_binary_forecasts(pairs, eligible_count=eligible)

@pytest.mark.parametrize("baseline", [[0.5,0.5], [float("inf")], [True], [1.1], [-0.1]])
def test_invalid_baseline_inputs_rejected(baseline):
    with pytest.raises(ValueError):
        summarize_binary_forecasts([(0.5, 1)], eligible_count=1,
                                   baseline_probabilities=baseline)

def row(app, year, outcome):
    return OutcomeObservation(
        app, 1, date(year, 6, 1), outcome,
        "COMPLETE_APPLICATION_COHORT", "synthetic-not-a-real-fda-cohort",
        date(year, 1, 1), True, outcome_public_as_of=date(year, 6, 1),
    )

def test_synthetic_walk_forward_exposes_metrics_and_base_rate_without_validation():
    samples = [
        row("historical-pass", 2018, "APPROVED"),
        row("historical-fail", 2019, "COMPLETE_RESPONSE"),
        row("heldout-pass", 2020, "APPROVED"),
        row("heldout-fail", 2020, "COMPLETE_RESPONSE"),
    ]
    saw = []
    def score(train, masked):
        saw.append((masked.application_id, [x.application_id for x in train], masked.outcome))
        return 0.8 if masked.application_id == "heldout-pass" else 0.2
    folds = walk_forward_backtest(
        samples, [date(2020,1,1), date(2021,1,1)], score, min_train=2,
    )
    r = folds[0]
    assert len(saw) == 2
    assert all(label == "WITHHELD" for _, _, label in saw)
    assert all(names == ["historical-pass", "historical-fail"] for _, names, _ in saw)
    assert r.test_count == 2
    assert r.brier_score == pytest.approx(0.04)
    assert r.research_metrics["brierScore"] == pytest.approx(r.brier_score)
    assert r.research_metrics["baselineBrierScore"] == pytest.approx(0.25)
    assert r.research_metrics["brierSkillScore"] == pytest.approx(0.84)
    assert r.research_metrics["coverage"] == 1
    assert r.research_metrics["accuracy"] == 1
    assert r.research_metrics["rocAuc"] == 1
    assert r.independent_fda_validation_complete is False
    assert r.research_metrics["modelHistoricallyValidated"] is False

def test_backtest_abstention_excludes_from_baseline_comparison():
    samples = [
        row("historical-pass", 2018, "APPROVED"),
        row("historical-fail", 2019, "COMPLETE_RESPONSE"),
        row("heldout-pass", 2020, "APPROVED"),
        row("heldout-fail", 2020, "COMPLETE_RESPONSE"),
    ]
    r = walk_forward_backtest(samples,
        [date(2020,1,1),date(2021,1,1)],
        lambda train, row: None if row.application_id == "heldout-fail" else 0.75,
        min_train=2,
    )[0]
    assert r.test_count == 1
    assert r.eligible_test_count == 2
    assert r.abstained_test_count == 1
    assert r.research_metrics["coverage"] == 0.5
    assert r.research_metrics["baselineBrierScore"] == pytest.approx(0.25)
    assert r.research_metrics["rocAuc"] is None
    assert r.research_metrics["balancedAccuracy"] is None
    assert r.independent_fda_validation_complete is False

def test_insufficient_training_yields_no_calibrated_output():
    samples = [row("future-only",2020,"APPROVED")]
    fold = walk_forward_backtest(
        samples, [date(2020,1,1), date(2021,1,1)],
        lambda train, row: pytest.fail("must not call"),
        min_train=100,
    )[0]
    assert fold.brier_score is None
    assert fold.research_metrics["predictedCount"] == 0
    assert fold.research_metrics["abstainedCount"] == 1
    assert fold.research_metrics["modelHistoricallyValidated"] is False
