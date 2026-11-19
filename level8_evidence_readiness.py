"""Level 8: deterministic evidence-readiness review, not FDA prediction.

Consumes immutable Level 7 records; does not infer approval or assign a
probability. Conflicts and unavailable evidence remain explicit.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from level7_evidence import EvidenceRecord

VALID_STATUSES = frozenset({
    "verified", "unverified", "missing", "inaccessible", "conflicting"
})

@dataclass(frozen=True)
class EvidenceReadiness:
    trial_id: str
    status: str
    verified_sources: int
    unverified_sources: int
    unavailable_sources: int
    conflicting_sources: int
    reasons: tuple[str, ...]

def assess_evidence_readiness(
    trial_id: str, records: Iterable[EvidenceRecord],
    *, minimum_verified_sources: int = 2,
) -> EvidenceReadiness:
    """Evaluate source readiness without manufacturing a clinical score."""
    if not trial_id.strip():
        raise ValueError("Exact trial identity required")
    if minimum_verified_sources < 1:
        raise ValueError("minimum_verified_sources must be positive")
    latest: dict[str, EvidenceRecord] = {}
    for record in records:
        if record.trial_id != trial_id:
            raise ValueError("Cross-trial evidence is not permitted")
        if record.status not in VALID_STATUSES:
            raise ValueError("Unknown evidence status")
        prior = latest.get(record.source_id)
        if prior is None or (record.retrieved_at, record.source_version) > (
            prior.retrieved_at, prior.source_version
        ):
            latest[record.source_id] = record
    counts = {status: sum(r.status == status for r in latest.values())
              for status in VALID_STATUSES}
    reasons: list[str] = []
    if counts["conflicting"]:
        reasons.append("Conflicting source evidence requires reconciliation")
    if counts["missing"] or counts["inaccessible"]:
        reasons.append("Unavailable source evidence is not negative clinical evidence")
    if counts["unverified"]:
        reasons.append("Unverified evidence requires source validation")
    independent_publishers = {r.publisher.strip().casefold() for r in latest.values()
                              if r.status == "verified" and r.publisher.strip()}
    if len(independent_publishers) < minimum_verified_sources:
        reasons.append("Insufficient independently verified publisher coverage")
    if counts["conflicting"]:
        status = "CONFLICT_REVIEW"
    elif len(independent_publishers) >= minimum_verified_sources and not (
        counts["unverified"] or counts["missing"] or counts["inaccessible"]
    ):
        status = "READY_FOR_SCIENTIFIC_REVIEW"
    else:
        status = "EVIDENCE_INCOMPLETE"
    return EvidenceReadiness(
        trial_id=trial_id, status=status,
        verified_sources=counts["verified"],
        unverified_sources=counts["unverified"],
        unavailable_sources=counts["missing"] + counts["inaccessible"],
        conflicting_sources=counts["conflicting"],
        reasons=tuple(reasons),
    )
