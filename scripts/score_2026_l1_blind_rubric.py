#!/usr/bin/env python3
"""Qualitative L1 rubric v0.1; sanitized evidence only, never reads outcome files.

This is a retrospective reconstruction aid, NOT a historical frozen forecast.
Only independently blinded reviewers may use results in blind accuracy studies.
"""
from dataclasses import dataclass
from typing import Literal

Rating = Literal["SUPPORTIVE", "CONCERN", "UNKNOWN"]
DOMAINS = ("efficacy", "trial_integrity", "safety", "regulatory_pathway", "evidence_sufficiency")

@dataclass(frozen=True)
class EvidenceRatings:
    efficacy: Rating
    trial_integrity: Rating
    safety: Rating
    regulatory_pathway: Rating
    evidence_sufficiency: Rating
    # A concern must be explicitly documented and unresolved before cutoff.
    material_concern_domains: tuple[str, ...] = ()

def classify(evidence: EvidenceRatings) -> str:
    values = {name: getattr(evidence, name) for name in DOMAINS}
    if any(value not in {"SUPPORTIVE", "CONCERN", "UNKNOWN"} for value in values.values()):
        raise ValueError("Invalid evidence domain rating")
    material = set(evidence.material_concern_domains)
    if material - set(DOMAINS):
        raise ValueError("Unknown concern domain")
    if any(values[domain] != "CONCERN" for domain in material):
        raise ValueError("Material concerns require a CONCERN rating")
    if material & {"efficacy", "trial_integrity", "safety", "regulatory_pathway"}:
        return "NONAPPROVAL_LEAN"
    if all(value != "UNKNOWN" for value in values.values()) and (
        values["efficacy"] == values["trial_integrity"] == "SUPPORTIVE"
        and values["safety"] == "SUPPORTIVE"
        and values["regulatory_pathway"] == "SUPPORTIVE"
        and values["evidence_sufficiency"] == "SUPPORTIVE"
    ):
        return "APPROVAL_LEAN"
    return "ABSTAIN"
