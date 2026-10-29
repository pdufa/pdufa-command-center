"""Research-only chronological consistency checks; not a trusted clock."""
from __future__ import annotations

from datetime import datetime, timezone

from research.fda_anchor_receipt import AnchorReceipt
from research.fda_prospective_outcome_scoring import FrozenPrediction, VerifiedOutcome


def _parse(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    return dt.astimezone(timezone.utc)


def check_time_consistency(
    prediction: FrozenPrediction,
    receipt: AnchorReceipt,
    outcome: VerifiedOutcome,
) -> str:
    try:
        recorded = _parse(prediction.recorded_at_utc)
        cutoff = _parse(prediction.cutoff_utc)
        anchor = _parse(receipt.anchored_at_utc)
        decision = _parse(outcome.decision_at_utc)
    except (ValueError, TypeError, AttributeError):
        return "INVALID_TIME"
    if recorded > cutoff:
        return "RECORDED_AFTER_CUTOFF"
    if anchor < recorded:
        return "ANCHOR_BEFORE_RECORDED"
    if anchor > cutoff:
        return "ANCHOR_AFTER_CUTOFF"
    if cutoff >= decision:
        return "CUTOFF_NOT_BEFORE_DECISION"
    return "CHRONOLOGY_CONSISTENT_TIME_UNTRUSTED"
