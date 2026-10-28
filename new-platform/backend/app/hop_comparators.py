"""HOP historical comparator matching (research-only; no probability estimates).

Only adjudicated historical FDA outcomes with contemporaneous, dated evidence
may enter the comparator pool. Missing dates or uncertain outcomes are excluded.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Iterable
from .hop_outcomes_import import APPLICATION_PATTERN, _fda_url

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
    application_id: str | None = None
    review_cycle: int | None = None

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
    application_id: str | None = None
    review_cycle: int | None = None

VALID_OUTCOMES = {"APPROVED", "COMPLETE_RESPONSE"}


def _cycle_key(case: HistoricalCase) -> tuple[str, int] | None:
    if not isinstance(case.application_id, str):
        return None
    application = case.application_id.strip().upper()
    if (not APPLICATION_PATTERN.fullmatch(application)
            or type(case.review_cycle) is not int or case.review_cycle < 1):
        return None
    return application.replace("-", ""), case.review_cycle


def match_historical_cases(target: TargetCase, history: Iterable[HistoricalCase], limit: int = 20) -> list[Comparator]:
    """Rank dated, independently adjudicated prior decisions without leakage.

    HistoricalCase is research input, not proof of independent adjudication.
    Its `independently_adjudicated` flag must never be set from CSV-schema
    validation, successful PDF downloading, or archive existence alone.
    Similarity is descriptive, NOT an FDA approval probability.

    A case/trial identifier is not an independent FDA observation. Require the
    preserved application/cycle identity, collapse repeated trials for one cycle,
    and quarantine conflicting dates/outcomes before ranking by clinical features.
    Distinct cycles remain visible but are correlated observations from the same
    application, not an independent sample for validation or frequency estimates.
    """
    if type(limit) is not int or limit < 1:
        raise ValueError("limit must be a positive integer")
    if type(target.prediction_as_of) is not date:
        raise ValueError("target prediction_as_of must be a date")
    cases = tuple(history)
    duplicates = Counter(case.case_id.strip() for case in cases
                         if isinstance(case.case_id, str) and case.case_id.strip())
    cycles: dict[tuple[str, int], list[HistoricalCase]] = defaultdict(list)
    matched: list[Comparator] = []
    for case in cases:
        key = _cycle_key(case)
        if (not isinstance(case.case_id, str) or not case.case_id.strip() or key is None
            or not _fda_url(case.source_url)
            or case.independently_adjudicated is not True
            or not isinstance(case.outcome, str)
            or type(case.decision_date) is not date
            or type(case.evidence_as_of) is not date
            or case.decision_date >= target.prediction_as_of
            # Outcome evidence can only exist on/after the FDA decision;
            # it must be public before the target prediction cutoff.
            or case.evidence_as_of < case.decision_date
            or case.evidence_as_of >= target.prediction_as_of):
            continue
        cycles[key].append(case)

    for (application, cycle), rows in cycles.items():
        # Nonbinary/revision observations and contradictory source-adjudicated
        # action claims require further review; do not pick a favorable trial.
        if (len({(case.outcome, case.decision_date) for case in rows}) != 1
                or rows[0].outcome not in VALID_OUTCOMES):
            continue
        representatives = []
        for case in rows:
            # Clinical comparison features must have been public BEFORE the
            # historical FDA decision, never reconstructed afterward.
            if (duplicates[case.case_id.strip()] != 1
                    or type(case.public_features_as_of) is not date
                    or case.public_features_as_of >= case.decision_date
                    or type(case.phase) is not int or case.phase not in (3, 4)
                    or any(not isinstance(value, str) or not value.strip()
                           for value in (case.indication, case.therapeutic_area, case.modality))):
                continue
            score = (
                0.45 * (case.indication.strip().casefold() == target.indication.strip().casefold())
                + 0.25 * (case.therapeutic_area.strip().casefold() == target.therapeutic_area.strip().casefold())
                + 0.20 * (case.modality.strip().casefold() == target.modality.strip().casefold())
                + 0.10 * (case.phase == target.phase)
            )
            representatives.append(Comparator(case.case_id.strip(), round(score, 3), case.outcome,
                                               case.source_url, case.decision_date, application, cycle))
        if representatives:
            matched.append(min(representatives, key=lambda x: (-x.similarity, x.case_id)))
    return sorted(matched, key=lambda x: (-x.similarity, -x.decision_date.toordinal(), x.case_id))[:limit]

def prediction_status(comparators: list[Comparator]) -> dict:
    """No model calibration exists; always abstain from numerical PoA."""
    return {"status": "NOT_VALIDATED", "probability": None, "comparator_count": len(comparators)}
