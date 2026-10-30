"""Fail-closed validation of the partial v1.1 scientific field inventory.

This does not certify clinical correctness or completion of 650 proposed slots.
"""
import json
from pathlib import Path

CATALOG = Path(__file__).parent / "evidence" / "prediction_v1_1_field_catalog_draft.json"
CANONICAL_QUESTIONS = Path(__file__).parents[1] / "new-platform" / "backend" / "app" / "science_40_question_catalog.json"
SEGMENTS = {"BIO", "MOA", "TRIAL", "EFFICACY", "SAFETY", "CMC", "PRECEDENT", "VALIDATION"}
REQUIRED = {"id", "segment", "name", "definition", "data_type", "applicability", "source", "assessment_ids", "mandatory", "critical"}


def validate_catalog(document):
    errors = []
    seen = set()
    canonical = json.loads(CANONICAL_QUESTIONS.read_text(encoding="utf-8"))
    valid_questions = {q["id"] for q in canonical["questions"]}
    if len(valid_questions) != 40:
        errors.append("canonical question catalog does not contain 40 unique IDs")
    fields = document.get("fields", [])
    if not isinstance(fields, list):
        return ["fields must be a list"]
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            errors.append(f"field {index}: expected object")
            continue
        missing = REQUIRED - field.keys()
        if missing:
            errors.append(f"field {index}: missing {sorted(missing)}")
            continue
        identifier = field["id"]
        if not isinstance(identifier, str) or not identifier.startswith(field["segment"] + "-"):
            errors.append(f"field {index}: invalid stable ID")
        if identifier in seen:
            errors.append(f"field {index}: duplicate ID {identifier}")
        seen.add(identifier)
        if field["segment"] not in SEGMENTS:
            errors.append(f"field {index}: unknown segment")
        for key in ("name", "definition", "data_type", "applicability", "source"):
            if not isinstance(field[key], str) or not field[key].strip():
                errors.append(f"field {index}: empty {key}")
        if not isinstance(field["assessment_ids"], list) or not field["assessment_ids"]:
            errors.append(f"field {index}: missing assessment cross-reference")
        for question_id in field["assessment_ids"] if isinstance(field["assessment_ids"], list) else []:
            if question_id not in valid_questions:
                errors.append(f"field {index}: unknown canonical assessment ID {question_id}")
        for key in ("mandatory", "critical"):
            if not isinstance(field[key], bool):
                errors.append(f"field {index}: {key} must be boolean")
    if document.get("status") != "PARTIAL_CATALOG_NOT_VALIDATED":
        errors.append("draft must remain explicitly unvalidated")
    if document.get("proposed_slots") != 650:
        errors.append("proposal slot count changed")
    if len(fields) >= 650:
        errors.append("draft requires independent scientific review before declaring 650 complete")
    return errors


if __name__ == "__main__":
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    problems = validate_catalog(catalog)
    if problems:
        raise SystemExit("\n".join(problems))
    print(f"PASS: {len(catalog['fields'])} draft definitions checked; 650-field inventory NOT COMPLETE")
