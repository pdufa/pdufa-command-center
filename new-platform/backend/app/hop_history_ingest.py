"""Quarantined JSON intake sharing the historical CSV metadata contract.

Outcome evidence is dated on/after the action; clinical features have a separate
predecision cutoff. Legacy rows with one ambiguous clock are rejected, never
silently reinterpreted. Parsing cannot certify a source or authorize prediction.
"""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from .hop_comparators import HistoricalCase
from .hop_outcomes_import import REQUIRED_COLUMNS, validate_record

REQUIRED = frozenset(REQUIRED_COLUMNS)


def _unique_object(pairs):
    record = {}
    for key, value in pairs:
        if key in record:
            raise ValueError(f"Duplicate JSON field: {key}")
        record[key] = value
    return record


def parse_history(text: str, *, as_of: date | None = None) -> list[HistoricalCase]:
    """Parse complete metadata; reject the entire invalid inventory.

    JSON phase/review_cycle values are integers; remaining fields follow CSV.
    Returned cases always remain independently unadjudicated. An explicit as_of
    makes replay deterministic; no dates are imputed or source flags promoted.
    """
    cutoff = date.today() if as_of is None else as_of
    if type(cutoff) is not date:
        raise ValueError("as_of must be a date")
    raw = json.loads(text, object_pairs_hook=_unique_object)
    if not isinstance(raw, list):
        raise ValueError("Historical outcomes must be a JSON array")
    cases = []
    seen_ids = set()
    seen_cycles = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or set(item) != REQUIRED:
            raise ValueError(
                f"Historical case {index}: complete historical metadata required; "
                "legacy single-clock rows require source review, not automatic migration")
        if any(type(item[key]) is not int for key in ("phase", "review_cycle")):
            raise ValueError(f"Historical case {index}: phase and review_cycle must be integers")
        csv_row = dict(item, phase=str(item["phase"]), review_cycle=str(item["review_cycle"]))
        record, errors = validate_record(csv_row, as_of=cutoff)
        if errors:
            raise ValueError(f"Historical case {index}: {', '.join(errors)}")
        cycle = (record.application_id, record.review_cycle)
        if record.case_id in seen_ids or cycle in seen_cycles:
            raise ValueError(f"Historical case {index}: duplicate case/application review cycle")
        seen_ids.add(record.case_id)
        seen_cycles.add(cycle)
        cases.append(HistoricalCase(
            case_id=record.case_id, indication=record.indication,
            therapeutic_area=record.therapeutic_area, modality=record.modality,
            phase=record.phase, decision_date=record.decision_date,
            outcome=record.outcome, evidence_as_of=record.evidence_as_of,
            source_url=record.source_url,
            public_features_as_of=record.public_features_as_of,
            application_id=record.application_id, review_cycle=record.review_cycle,
            drug_name=record.drug_name, sponsor=record.sponsor,
            source_title=record.source_title,
        ))
    return cases

def load_history(path: str | Path, *, as_of: date | None = None) -> list[HistoricalCase]:
    return parse_history(Path(path).read_text(encoding="utf-8"), as_of=as_of)
