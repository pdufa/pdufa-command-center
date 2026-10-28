"""Research-only TNXP RESILIENT ITT exclusion adjudication.

No production wiring, model probabilities, or retrospective outcome features.
Boolean evidence flags are NOT evidence of authenticated documents.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Adjudication(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    CONFORMANT = "CONFORMANT"
    NONCONFORMANT = "NONCONFORMANT"


@dataclass(frozen=True)
class Evidence:
    final_signed_sap: bool = False
    version_history: bool = False
    database_lock_timing: bool = False
    csr_population_listing: bool = False
    deviation_record: bool = False
    adjudication_record: bool = False
    all_randomized_sensitivity: bool = False
    authenticated_sources: bool = False
    explicit_conformance_finding: bool | None = None


def adjudicate(evidence: Evidence) -> Adjudication:
    """Legacy flag-only inputs are never sufficient to certify compliance.

    Even all-true flags are caller assertions, not verified source provenance.
    Until authenticated document identifiers, hashes, dates, and independently
    reviewed adjudication are implemented, the only safe state is UNRESOLVED.
    """
    return Adjudication.UNRESOLVED


def prediction_gate(evidence: Evidence) -> str:
    """ITT conformance alone is never sufficient to authorize prediction."""
    return "ABSTAIN"
