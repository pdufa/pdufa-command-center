"""HOP historical comparator matching (research-only; no probability estimates).

Only adjudicated historical FDA outcomes with contemporaneous, dated evidence
may enter the comparator pool. Missing dates or uncertain outcomes are excluded.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Iterable
from .hop_outcomes_import import _fda_url

@dataclass(frozen=True)
class HistoricalCase:
    case_id: str
    indication: str
    therapeutic_area: str
    modality: str
    phase: int
    decision_date: date
    outcome: str
    evidence_as_of: date
    source_url: str
    public_features_as_of: date | None = None
    independently_adjudicated: bool = False

@dataclass(frozen=True)
class TargetCase:
    indication: str
    therapeutic_area: str
    modality: str
    phase: int
    prediction_as_of: date

@dataclass(frozen=True)
class Comparator:
    case_id: str
    similarity: float
    outcome: str
    source_url: str
    decision_date: date

VALID_OUTCOMES = {"APPROVED", "COMPLETE_RESPONSE"}

def match_historical_cases(target: TargetCase, history: Iterable[HistoricalCase], limit: int = 20) -> list[Comparator]:
    """Rank dated, independently adjudicated prior decisions without leakage.

    HistoricalCase is research input, not proof of independent adjudication.
    Its `independently_adjudicated` flag must never be set from CSV-schema
    validation, successful PDF downloading, or archive existence alone.
    Similarity is descriptive, NOT an FDA approval probability.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    cases = tuple(history)
    duplicates = Counter(case.case_id for case in cases if case.case_id)
    matched: list[Comparator] = []
    for case in cases:
        if (not case.case_id or duplicates[case.case_id] != 1
            or not _fda_url(case.source_url)
            or case.independently_adjudicated is not True
            or case.outcome not in VALID_OUTCOMES
            or case.decision_date >= target.prediction_as_of
            # Outcome evidence can only exist on/after the FDA decision;
            # it must be public before the target prediction cutoff.
            or case.evidence_as_of < case.decision_date
            or case.evidence_as_of > target.prediction_as_of
            # Clinical comparison features must have been public BEFORE
            # the historical FDA decision, never reconstructed afterward.
            or case.public_features_as_of is None
            or case.public_features_as_of >= case.decision_date
            or case.public_features_as_of > target.prediction_as_of
            or case.phase < 3):
            continue
        score = (
            0.45 * (case.indication.strip().casefold() == target.indication.strip().casefold())
            + 0.25 * (case.therapeutic_area.strip().casefold() == target.therapeutic_area.strip().casefold())
            + 0.20 * (case.modality.strip().casefold() == target.modality.strip().casefold())
            + 0.10 * (case.phase == target.phase)
        )
        matched.append(Comparator(case.case_id, round(score, 3), case.outcome, case.source_url, case.decision_date))
    return sorted(matched, key=lambda x: (-x.similarity, -x.decision_date.toordinal(), x.case_id))[:limit]

def prediction_status(comparators: list[Comparator]) -> dict:
    """No model calibration exists; always abstain from numerical PoA."""
    return {"status": "NOT_VALIDATED", "probability": None, "comparator_count": len(comparators)}
