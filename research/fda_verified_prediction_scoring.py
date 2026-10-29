"""Fail-closed provenance boundary for prospective FDA prediction scoring.

The existing scorer is a calculation helper. This gate forbids publishing
its result as validated performance without independently authenticated
prediction timestamp and original FDA outcome document provenance.
"""
from __future__ import annotations

from dataclasses import dataclass

from research.fda_prospective_outcome_scoring import (
    FrozenPrediction, VerifiedOutcome, Score, score_prediction,
)


@dataclass(frozen=True)
class ValidationEvidence:
    externally_anchored_prediction_hash: str = ""
    trusted_anchor_receipt_verified: bool = False
    original_fda_document_digest: str = ""
    original_fda_document_source_verified: bool = False
    independent_outcome_review_signed: bool = False


def verified_score(
    prediction: FrozenPrediction,
    outcome: VerifiedOutcome,
    evidence: ValidationEvidence,
) -> Score:
    """Do not score unless provenance is verified by a trusted boundary.

    Boolean claims alone are not proof of verification. Until a trusted
    receipt verifier and FDA source authenticator are integrated, refuse
    all attempts to publish a scored result.
    """
    if prediction.trial_id != outcome.trial_id:
        raise ValueError("Trial identity mismatch")
    return Score(prediction.trial_id, "PROVENANCE_NOT_VERIFIED", None)
