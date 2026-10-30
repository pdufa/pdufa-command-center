"""Research-only actionable blockers for FDA prospective performance readiness."""
from __future__ import annotations

from dataclasses import dataclass

from research.fda_provenance_scoring_pipeline import PipelineResult


@dataclass(frozen=True)
class BlockerReport:
    ready_for_validated_scoring: bool
    blockers: tuple[str, ...]


def report_blockers(result: PipelineResult) -> BlockerReport:
    blockers = []
    if result.prediction_gate != "TRUSTED_ANCHOR_VERIFIED":
        blockers.append("INDEPENDENT_TIMESTAMP_AUTHORITY_REQUIRED")
    if result.membership_gate != "LEDGER_MEMBERSHIP_VERIFIED_TIME_UNTRUSTED":
        blockers.append("FROZEN_PREDICTION_MEMBERSHIP_REQUIRED")
    if result.chronology_gate != "CHRONOLOGY_CONSISTENT_TIME_UNTRUSTED":
        blockers.append("CHRONOLOGY_RECONCILIATION_REQUIRED")
    if result.outcome_gate != "FDA_ORIGIN_AUTHENTICATED":
        blockers.append("FDA_ORIGINAL_DOCUMENT_AUTHENTICATION_REQUIRED")
    # No current research path can certify independently trusted timing
    # or FDA provenance, even if status strings are constructed by a caller.
    blockers.append("INDEPENDENT_VALIDATION_WORKFLOW_NOT_ESTABLISHED")
    return BlockerReport(False, tuple(blockers))
