"""Research-only evidence-slot registry: structure is not scientific verification.

This module deliberately refuses to inflate the eight reviewed draft definitions
into 650 invented scientific fields. It tracks which slots are actually defined.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

CATALOG_PATH = Path(__file__).parent / "evidence" / "prediction_v1_1_field_catalog_draft.json"
EXPECTED_SLOTS = 650
VALID_STATES = frozenset({"MISSING", "UNVERIFIED", "IN_REVIEW", "VERIFIED", "CONFLICTED"})


@dataclass(frozen=True)
class SlotStatus:
    field_id: str
    evidence_state: str
    source_count: int
    independently_verified: bool


def load_defined_fields(path: Path = CATALOG_PATH) -> dict[str, dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    from research.prediction_v1_1_catalog_validator import validate_catalog
    errors = validate_catalog(document)
    if errors:
        raise ValueError("Invalid draft catalog: " + "; ".join(errors))
    return {field["id"]: field for field in document["fields"]}


def summarize_registry(
    fields: Mapping[str, dict], observations: Mapping[str, SlotStatus] | None = None
) -> dict:
    if not isinstance(fields, Mapping) or any(not isinstance(key, str) or not key for key in fields):
        raise ValueError("Defined fields must be a mapping of nonempty field identifiers")
    if observations is None:
        observations = {}
    if not isinstance(observations, Mapping) or any(not isinstance(key, str) or not key for key in observations):
        raise ValueError("Observations must be a mapping of nonempty field identifiers")
    if len(fields) > EXPECTED_SLOTS:
        raise ValueError("More defined fields than proposed slots")
    unknown = set(observations) - set(fields)
    if unknown:
        raise ValueError("Evidence references undefined fields: " + ", ".join(sorted(unknown)))
    counts = {state: 0 for state in sorted(VALID_STATES)}
    for field_id in fields:
        if field_id not in observations:
            counts["MISSING"] += 1
            continue
        status = observations[field_id]
        if (not isinstance(status, SlotStatus) or status.field_id != field_id
                or not isinstance(status.evidence_state, str) or status.evidence_state not in VALID_STATES):
            raise ValueError("Invalid evidence status for " + field_id)
        if type(status.independently_verified) is not bool:
            raise ValueError("Independent verification must be an explicit boolean for " + field_id)
        if not isinstance(status.source_count, int) or isinstance(status.source_count, bool) or status.source_count < 0:
            raise ValueError("Invalid source count for " + field_id)
        if status.evidence_state == "VERIFIED" and (
            not status.independently_verified or status.source_count == 0
        ):
            raise ValueError("VERIFIED requires independent verification and a source")
        counts[status.evidence_state] += 1
    return {
        "proposed_slots": EXPECTED_SLOTS,
        "defined_fields": len(fields),
        "undefined_slots": EXPECTED_SLOTS - len(fields),
        "evidence_states": counts,
        "scientific_catalog_validated": False,
        "prediction_readiness": "NOT_READY",
        "prediction_action": "ABSTAIN",
        "note": "A defined or populated field is not independently validated evidence.",
    }
