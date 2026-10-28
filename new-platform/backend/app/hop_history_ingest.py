"""Versioned, quarantined JSON intake for historical FDA comparator evidence.

Outcome-document availability and predecision feature availability are separate
clocks. This module validates the same fields as the CSV intake; neither intake
independently adjudicates FDA actions or permits training/prediction.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .hop_comparators import HistoricalCase, VALID_OUTCOMES
from .hop_outcomes_import import REQUIRED_COLUMNS, validate_record

SCHEMA_VERSION = 2
MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_RECORDS = 10_000
REQUIRED = frozenset(REQUIRED_COLUMNS)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Historical input: duplicate JSON field {key}")
        result[key] = value
    return result


def parse_history(text: str, *, as_of: date | None = None) -> list[HistoricalCase]:
    """Parse schema v2 only, preserving application/cycle identity in quarantine.

    Legacy unversioned arrays cannot distinguish outcome evidence from features
    and are rejected with a migration error. No missing chronology is inferred.
    """
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("Historical input exceeds bounded text size")
    cutoff = date.today() if as_of is None else as_of
    if type(cutoff) is not date:
        raise ValueError("Historical import as_of must be a date")
    raw = json.loads(text, object_pairs_hook=_unique_object)
    if (not isinstance(raw, dict) or set(raw) != {"schema_version", "records"}
            or type(raw["schema_version"]) is not int
            or raw["schema_version"] != SCHEMA_VERSION):
        raise ValueError("Historical input requires schema_version 2; migrate legacy chronology explicitly")
    records = raw["records"]
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError("Historical records must be a bounded JSON array")
    cases = []
    seen_ids = set()
    seen_cycles = set()
    for index, item in enumerate(records):
        if not isinstance(item, dict) or set(item) != REQUIRED:
            raise ValueError(f"Historical case {index}: missing or unexpected fields")
        if (type(item["phase"]) is not int or item["phase"] not in (3, 4)
                or type(item["review_cycle"]) is not int or item["review_cycle"] < 1):
            raise ValueError(f"Historical case {index}: invalid trial phase or review cycle")
        if any(not isinstance(item[key], str) or not item[key].strip()
               for key in REQUIRED - {"phase", "review_cycle"}):
            raise ValueError(f"Historical case {index}: required text must be nonempty strings")
        # Use the established CSV contract for strict dates, official URL shape,
        # canonical application IDs, and both independent availability clocks.
        csv_row = {**item, "phase": str(item["phase"]), "review_cycle": str(item["review_cycle"])}
        record, errors = validate_record(csv_row, as_of=cutoff)
        if errors:
            raise ValueError(f"Historical case {index}: {', '.join(errors)}")
        if record.outcome not in VALID_OUTCOMES:
            raise ValueError(f"Historical case {index}: unsupported binary comparator outcome")
        key = (record.application_id, record.review_cycle)
        if record.case_id in seen_ids:
            raise ValueError(f"Historical case {index}: duplicate case ID")
        if key in seen_cycles:
            raise ValueError(f"Historical case {index}: duplicate application review cycle")
        seen_ids.add(record.case_id)
        seen_cycles.add(key)
        cases.append(HistoricalCase(
            case_id=record.case_id, indication=record.indication,
            therapeutic_area=record.therapeutic_area, modality=record.modality,
            phase=record.phase, decision_date=record.decision_date, outcome=record.outcome,
            evidence_as_of=record.evidence_as_of, source_url=record.source_url,
            public_features_as_of=record.public_features_as_of,
            independently_adjudicated=False,
            application_id=record.application_id, review_cycle=record.review_cycle,
        ))
    return cases


def load_history(path: str | Path, *, as_of: date | None = None) -> list[HistoricalCase]:
    with Path(path).open(encoding="utf-8") as stream:
        text = stream.read(MAX_INPUT_BYTES + 1)
    return parse_history(text, as_of=as_of)
