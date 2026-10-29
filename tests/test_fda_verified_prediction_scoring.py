from dataclasses import replace

import pytest

from research.fda_prospective_outcome_scoring import FrozenPrediction, VerifiedOutcome
from research.fda_verified_prediction_scoring import ValidationEvidence, verified_score


P = FrozenPrediction("TRIAL-1", "PASS", "2026-11-01T00:00:00Z", "2026-12-01T00:00:00Z", "a" * 64)
O = VerifiedOutcome("TRIAL-1", "PASS", "2026-12-01T12:00:00Z", "b" * 64, True)


def test_default_provenance_blocks_scoring():
    result = verified_score(P, O, ValidationEvidence())
    assert result.status == "PROVENANCE_NOT_VERIFIED"
    assert result.correct is None


def test_all_self_attested_flags_still_block_scoring():
    evidence = ValidationEvidence(
        externally_anchored_prediction_hash="a" * 64,
        trusted_anchor_receipt_verified=True,
        original_fda_document_digest="b" * 64,
        original_fda_document_source_verified=True,
        independent_outcome_review_signed=True,
    )
    result = verified_score(P, O, evidence)
    assert result.status == "PROVENANCE_NOT_VERIFIED"
    assert result.correct is None


def test_trial_identity_mismatch_rejected():
    with pytest.raises(ValueError, match="identity"):
        verified_score(P, replace(O, trial_id="OTHER"), ValidationEvidence())
