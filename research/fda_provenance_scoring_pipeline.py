"""Research-only combined evidence gate for FDA prospective scoring.

A valid signed receipt and matching document digest do not by themselves
establish independent timestamping or FDA publication provenance.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from research.fda_anchor_receipt import AnchorReceipt
from research.fda_anchor_cutoff_gate import check_anchor_before_cutoff
from research.fda_outcome_document_integrity import check_outcome_document
from research.fda_prospective_outcome_scoring import FrozenPrediction, VerifiedOutcome, Score


@dataclass(frozen=True)
class PipelineResult:
    prediction_gate: str
    outcome_gate: str
    score: Score


def inspect_prospective_evidence(
    prediction: FrozenPrediction,
    outcome: VerifiedOutcome,
    *,
    ledger_path: str | Path,
    anchor_receipt: AnchorReceipt,
    trusted_signers: Mapping[str, bytes],
    outcome_document_path: str | Path,
) -> PipelineResult:
    if prediction.trial_id != outcome.trial_id:
        raise ValueError("Trial identity mismatch")
    ledger = check_anchor_before_cutoff(
        ledger_path, anchor_receipt, trusted_signers,
        prediction_cutoff_utc=prediction.cutoff_utc,
    )
    document = check_outcome_document(
        outcome_document_path, pinned_sha256=outcome.original_document_sha256,
    )
    # Neither signer-clock trust nor FDA publication origin has been proven.
    return PipelineResult(
        prediction_gate=ledger.status,
        outcome_gate=document.status,
        score=Score(prediction.trial_id, "PROVENANCE_NOT_VERIFIED", None),
    )
