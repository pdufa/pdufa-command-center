"""Research-only scoring of frozen prediction events against later FDA outcomes.

No source authentication or trusted timestamping is implied here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


VALID_DECISIONS = frozenset({"PASS", "CRL", "EXTENSION"})
VALID_PREDICTIONS = VALID_DECISIONS | {"ABSTAIN"}


def _parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class FrozenPrediction:
    trial_id: str
    prediction: str
    recorded_at_utc: str
    cutoff_utc: str
    ledger_entry_hash: str


@dataclass(frozen=True)
class VerifiedOutcome:
    trial_id: str
    decision: str
    decision_at_utc: str
    original_document_sha256: str
    independently_verified: bool


@dataclass(frozen=True)
class Score:
    trial_id: str
    status: str
    correct: bool | None


def score_prediction(prediction: FrozenPrediction, outcome: VerifiedOutcome) -> Score:
    if prediction.trial_id != outcome.trial_id:
        raise ValueError("Trial identity mismatch")
    if prediction.prediction not in VALID_PREDICTIONS or outcome.decision not in VALID_DECISIONS:
        raise ValueError("Invalid decision label")
    if not outcome.independently_verified or len(outcome.original_document_sha256) != 64:
        return Score(prediction.trial_id, "UNVERIFIED_OUTCOME", None)
    if not prediction.ledger_entry_hash or len(prediction.ledger_entry_hash) != 64:
        return Score(prediction.trial_id, "UNANCHORED_PREDICTION", None)
    if _parse_utc(prediction.recorded_at_utc) > _parse_utc(prediction.cutoff_utc):
        return Score(prediction.trial_id, "LATE_PREDICTION", None)
    if _parse_utc(prediction.recorded_at_utc) >= _parse_utc(outcome.decision_at_utc):
        return Score(prediction.trial_id, "POST_OUTCOME_PREDICTION", None)
    if prediction.prediction == "ABSTAIN":
        return Score(prediction.trial_id, "ABSTAIN", None)
    return Score(prediction.trial_id, "SCORED", prediction.prediction == outcome.decision)
