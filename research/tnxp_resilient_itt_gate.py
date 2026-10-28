"""Research-only adjudication of TNXP RESILIENT ITT exclusion.

No model probabilities, retrospective outcome features, or production wiring.
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
    """Return a finding only with authenticated and complete evidence.

    A missing all-randomized sensitivity result blocks scientific readiness
    even when an exclusion's governance could be otherwise adjudicated.
    """
    required = (
        evidence.final_signed_sap,
        evidence.version_history,
        evidence.database_lock_timing,
        evidence.csr_population_listing,
        evidence.deviation_record,
        evidence.adjudication_record,
        evidence.all_randomized_sensitivity,
        evidence.authenticated_sources,
    )
    if not all(required) or evidence.explicit_conformance_finding is None:
        return Adjudication.UNRESOLVED
    return (
        Adjudication.CONFORMANT
        if evidence.explicit_conformance_finding
        else Adjudication.NONCONFORMANT
    )


def prediction_gate(evidence: Evidence) -> str:
    """ITT conformance alone is never sufficient to authorize prediction."""
    return "ABSTAIN"
