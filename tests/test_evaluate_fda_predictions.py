"""Synthetic regression tests for the descriptive FDA prediction evaluator."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_fda_predictions import evaluate


def record(**changes):
    base = {"application_id": "NDA123456", "submission_id": "ORIG-1",
            "review_cycle": 1, "independently_adjudicated": True,
            "prediction_frozen": True, "prediction_as_of": "2020-01-01",
            "decision_date": "2020-02-01", "outcome": "PASS",
            "approval_probability": 0.8}
    return {**base, **changes}


def test_empty_and_unverified_never_validate():
    assert evaluate([])["status"] == "INSUFFICIENT_VERIFIED_HOLDOUT"
    r = evaluate([record(independently_adjudicated=False)])
    assert r["evaluated_cycles"] == 0
    assert r["excluded"]["unverified_outcome"] == 1


def test_unfrozen_or_future_prediction_excluded():
    r = evaluate([record(prediction_frozen=False),
                  record(submission_id="ORIG-2", prediction_as_of="2020-02-01")])
    assert r["evaluated_cycles"] == 0
    assert r["excluded"]["unfrozen_prediction"] == 1
    assert r["excluded"]["temporal_leakage"] == 1


def test_duplicate_cycle_is_not_double_counted():
    r = evaluate([record(), record(approval_probability=0.1)])
    assert r["evaluated_cycles"] == 1
    assert r["excluded"]["duplicate_review_cycle"] == 1


def test_metrics_are_descriptive_not_certification():
    r = evaluate([record(), record(application_id="NDA999999",
                                   outcome="FAIL", approval_probability=0.2)])
    assert r["evaluated_cycles"] == 2
    assert abs(r["metrics"]["brier_score"] - 0.04) < 1e-10
    assert r["metrics"]["threshold_0_5_accuracy"] == 1
    assert r["independently_validated"] is False
    assert r["trading_authorized"] is False


def test_bad_probability_excluded():
    for value in [-0.1, 1.1, float("nan"), "0.8", True]:
        r = evaluate([record(approval_probability=value)])
        assert r["evaluated_cycles"] == 0


def test_separate_review_cycles_allowed():
    r = evaluate([record(), record(review_cycle=2, outcome="FAIL",
                                    approval_probability=0.3)])
    assert r["evaluated_cycles"] == 2
