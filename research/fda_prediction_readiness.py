"""Research-only prediction readiness evaluation.

This module intentionally does not emit PASS/CRL/EXTENSION probabilities.
A complete evidence bundle is necessary but not sufficient for a
scientifically validated prospective FDA decision prediction.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessInputs:
    scientific_assessments_complete: bool = False
    independent_source_review_complete: bool = False
    original_fda_documents_authenticated: bool = False
    historical_cutoff_leakage_audit_passed: bool = False
    prospective_outcomes_scored: int = 0
    calibration_validated: bool = False
    model_frozen_before_outcomes: bool = False


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    decision: str
    blockers: tuple[str, ...]


def evaluate_readiness(inputs: ReadinessInputs) -> ReadinessResult:
    blockers = []
    for field, label in (
        ("scientific_assessments_complete", "Scientific assessments incomplete"),
        ("independent_source_review_complete", "Independent source review incomplete"),
        ("original_fda_documents_authenticated", "Original FDA documents unauthenticated"),
        ("historical_cutoff_leakage_audit_passed", "Historical leakage audit incomplete"),
        ("model_frozen_before_outcomes", "No frozen pre-outcome model"),
        ("calibration_validated", "Prediction calibration unvalidated"),
    ):
        if not getattr(inputs, field):
            blockers.append(label)
    if inputs.prospective_outcomes_scored <= 0:
        blockers.append("No scored prospective outcomes")
    # A positive count and checked boxes cannot establish statistical
    # reliability, representative sampling or decision-grade calibration.
    blockers.append("Independent out-of-sample performance certification unavailable")
    return ReadinessResult(False, "ABSTAIN", tuple(blockers))
