"""Synthetic regression tests for strict prior-rate FDA baseline comparisons."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_fda_prediction_baseline import compare_to_prior_rate


def training(outcome="PASS", **changes):
    return {"application_id": "NDA000001", "submission_id": "ORIG",
            "review_cycle": 1, "independently_adjudicated": True,
            "decision_date": "2019-01-01", "outcome": outcome, **changes}


def holdout(outcome="PASS", **changes):
    return {"application_id": "NDA000002", "submission_id": "ORIG",
            "review_cycle": 1, "independently_adjudicated": True,
            "prediction_frozen": True, "prediction_as_of": "2020-01-01",
            "decision_date": "2020-02-01", "outcome": outcome,
            "approval_probability": 0.8, **changes}


def test_empty_sets_abstain():
    assert compare_to_prior_rate([], [holdout()])["status"] == "INSUFFICIENT_VERIFIED_HOLDOUT"
    assert compare_to_prior_rate([training()], [])["status"] == "INSUFFICIENT_VERIFIED_HOLDOUT"


def test_temporal_overlap_abstains():
    result = compare_to_prior_rate([training(decision_date="2020-01-01")], [holdout()])
    assert result["status"] == "INSUFFICIENT_VERIFIED_HOLDOUT"


def test_future_prediction_abstains():
    result = compare_to_prior_rate([training()], [holdout(prediction_as_of="2020-02-01")])
    assert result["status"] == "INSUFFICIENT_VERIFIED_HOLDOUT"


def test_unverified_holdout_abstains():
    result = compare_to_prior_rate([training()], [holdout(independently_adjudicated=False)])
    assert result["status"] == "INSUFFICIENT_VERIFIED_HOLDOUT"


def test_duplicate_holdout_abstains():
    result = compare_to_prior_rate([training()], [holdout(), holdout()])
    assert result["status"] == "INSUFFICIENT_VERIFIED_HOLDOUT"


def test_brier_skill_and_no_trading_authorization():
    train = [training(), training(outcome="FAIL", application_id="NDA000003")]
    result = compare_to_prior_rate(train, [holdout()])
    assert result["status"] == "DESCRIPTIVE_BASELINE_COMPARISON"
    assert abs(result["prior_approval_rate"] - .5) < 1e-10
    assert abs(result["model_brier"] - .04) < 1e-10
    assert abs(result["baseline_brier"] - .25) < 1e-10
    assert abs(result["brier_skill"] - .84) < 1e-10
    assert result["independently_validated"] is False
    assert result["trading_authorized"] is False


def test_invalid_probability_abstains():
    for value in [-.1, 1.1, "0.8", True, float("nan")]:
        result = compare_to_prior_rate([training()], [holdout(approval_probability=value)])
        assert result["status"] == "INSUFFICIENT_VERIFIED_HOLDOUT"
