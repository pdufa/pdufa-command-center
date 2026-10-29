"""Actionable research-only validation blockers for prospective FDA scoring."""
from __future__ import annotations

from dataclasses import dataclass

from research.fda_provenance_scoring_pipeline import PipelineResult


@dataclass(frozen=True)
class BlockerReport:
    ready_for_validated_scoring: bool
    blockers: tuple[str, ...]


def explain_validation_blockers(result: PipelineResult) -> BlockerReport:
    blockers = []
    if result.prediction_gate != "SIGNED_PRE_CUTOFF_UNTRUSTED_TIME":
        blockers.append("Repair ledger integrity, signed receipt, or cutoff validation.")
    if result.membership_gate != "LEDGER_MEMBERSHIP_VERIFIED_TIME_UNTRUSTED":
        blockers.append("Link the exact frozen prediction to the audited ledger.")
    if result.chronology_gate != "CHRONOLOGY_CONSISTENT_TIME_UNTRUSTED":
        blockers.append("Reconcile prediction, anchor, cutoff, and FDA decision chronology.")
    if result.outcome_gate != "BYTES_MATCH_ORIGIN_UNVERIFIED":
        blockers.append("Repair missing, altered, or invalid FDA document bytes.")
    blockers.extend((
        "Obtain independent trusted timestamp evidence for the frozen prediction.",
        "Authenticate the original FDA decision source and independent outcome review.",
        "Validate a prospective cohort before reporting prediction accuracy.",
    ))
    return BlockerReport(False, tuple(blockers))
