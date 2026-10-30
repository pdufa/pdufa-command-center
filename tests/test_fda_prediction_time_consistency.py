from dataclasses import replace

from research.fda_anchor_receipt import AnchorReceipt
from research.fda_prediction_time_consistency import check_time_consistency
from research.fda_prospective_outcome_scoring import FrozenPrediction, VerifiedOutcome


P = FrozenPrediction("EXAMPLE", "PASS", "2026-11-01T00:00:00Z", "2026-12-01T00:00:00Z", "a" * 64)
R = AnchorReceipt("a" * 64, "2026-11-01T00:01:00Z", "signer", "")
O = VerifiedOutcome("EXAMPLE", "PASS", "2026-12-02T00:00:00Z", "b" * 64, True)


def test_consistent_chronology_not_external_time_proof():
    assert check_time_consistency(P, R, O) == "CHRONOLOGY_CONSISTENT_TIME_UNTRUSTED"


def test_anchor_before_recorded_rejected():
    assert check_time_consistency(P, replace(R, anchored_at_utc="2026-10-31T23:00:00Z"), O) == "ANCHOR_BEFORE_RECORDED"


def test_cutoff_after_decision_rejected():
    assert check_time_consistency(P, R, replace(O, decision_at_utc="2026-11-30T00:00:00Z")) == "CUTOFF_NOT_BEFORE_DECISION"


def test_invalid_time_rejected():
    assert check_time_consistency(replace(P, recorded_at_utc="invalid"), R, O) == "INVALID_TIME"
