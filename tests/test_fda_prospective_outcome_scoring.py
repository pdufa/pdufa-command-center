from dataclasses import replace

import pytest

from research.fda_prospective_outcome_scoring import (
    FrozenPrediction, VerifiedOutcome, score_prediction,
)


P = FrozenPrediction("TRIAL-1", "PASS", "2026-11-01T00:00:00Z", "2026-12-01T00:00:00Z", "a" * 64)
O = VerifiedOutcome("TRIAL-1", "CRL", "2026-12-01T12:00:00Z", "b" * 64, True)


def test_wrong_prediction_scored():
    result = score_prediction(P, O)
    assert result.status == "SCORED"
    assert result.correct is False


def test_abstain_not_counted_as_error_or_success():
    result = score_prediction(replace(P, prediction="ABSTAIN"), O)
    assert result.status == "ABSTAIN"
    assert result.correct is None


def test_unverified_outcome_excluded():
    result = score_prediction(P, replace(O, independently_verified=False))
    assert result.status == "UNVERIFIED_OUTCOME"
    assert result.correct is None


def test_post_outcome_prediction_excluded():
    result = score_prediction(
        replace(P, recorded_at_utc="2026-12-02T00:00:00Z", cutoff_utc="2026-12-03T00:00:00Z"), O
    )
    assert result.status == "POST_OUTCOME_PREDICTION"
    assert result.correct is None


def test_trial_mismatch_rejected():
    with pytest.raises(ValueError, match="identity"):
        score_prediction(P, replace(O, trial_id="OTHER"))
