"""Read-only, opt-in isolated assessment contract dispatcher.

Does not import existing assessment runtime, persist data, or activate scoring.
Unsupported levels and malformed payloads fail closed.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .level07_population_review import validate_level7_review
from .level08_safety_review import validate_level8_review
from .level09_benefit_risk import validate_level9_benefit_risk
from .level10_dossier import validate_level10_dossier
from .level11_unmet_need import validate_level11_context
from .level12_replication import validate_level12_replication
from .level13_filing import validate_level13_filing
from .level14_pathway import validate_level14_pathway
from .level15_precedent import validate_level15_precedent
from .level16_manufacturing import validate_level16_manufacturing
from .level17_disclosures import validate_level17_disclosures
from .level18_challenge import validate_level18_challenge
from .level19_prospective import validate_level19_prospective
from .level20_outcome import validate_level20_outcome

_VALIDATORS = {
    7: validate_level7_review, 8: validate_level8_review,
    9: validate_level9_benefit_risk, 10: validate_level10_dossier,
    11: validate_level11_context, 12: validate_level12_replication,
    13: validate_level13_filing, 14: validate_level14_pathway,
    15: validate_level15_precedent, 16: validate_level16_manufacturing,
    17: validate_level17_disclosures, 18: validate_level18_challenge,
    19: validate_level19_prospective, 20: validate_level20_outcome,
}


def inspect_isolated_level(level: int, record: Mapping[str, Any]) -> dict[str, Any]:
    if type(level) is not int or level not in _VALIDATORS:
        raise ValueError("Only isolated Levels 7-20 are supported")
    if not isinstance(record, Mapping):
        raise TypeError("Assessment input must be a mapping")
    result = _VALIDATORS[level](dict(record))
    if result.get("level") != level:
        raise RuntimeError("Assessment validator level mismatch")
    if result.get("scientific_status") != "NOT_VERIFIED" or result.get("scientific_score") is not None or result.get("fda_prediction") != "ABSTAIN":
        raise RuntimeError("Isolated assessment contract must fail closed")
    return result
