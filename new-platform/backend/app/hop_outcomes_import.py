"""Validated import boundary for HOP historical FDA decisions.

This module intentionally does not fetch or invent records. Populate the input file
from documented primary sources, then validate every row before database loading.
"""
from __future__ import annotations
import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

REQUIRED_COLUMNS = (
    "case_id", "application_id", "drug_name", "sponsor", "indication",
    "therapeutic_area", "modality", "phase", "decision_date", "outcome",
    "evidence_as_of", "source_url", "source_title",
)
ALLOWED_OUTCOMES = {"APPROVED", "COMPLETE_RESPONSE", "WITHDRAWN", "OTHER_NONAPPROVAL"}
ALLOWED_DECISIONS = {"APPROVED", "COMPLETE_RESPONSE", "WITHDRAWN", "OTHER_NONAPPROVAL"}

@dataclass(frozen=True)
class HistoricalOutcomeRecord:
    case_id: str
    application_id: str
    drug_name: str
    sponsor: str
    indication: str
    therapeutic_area: str
    modality: str
    phase: int
    decision_date: date
    outcome: str
    evidence_as_of: date
    source_url: str
    source_title: str

def validate_record(row: dict[str, str], *, as_of: date) -> tuple[HistoricalOutcomeRecord | None, list[str]]:
    errors: list[str] = []
    for col in REQUIRED_COLUMNS:
        if not (row.get(col) or "").strip():
            errors.append(f"missing:{col}")
    if errors:
        return None, errors
    try:
        decision_date = date.fromisoformat(row["decision_date"])
        evidence_as_of = date.fromisoformat(row["evidence_as_of"])
        phase = int(row["phase"])
    except (ValueError, TypeError):
        return None, ["invalid_date_or_phase"]
    outcome = row["outcome"].strip().upper()
    if outcome not in ALLOWED_OUTCOMES:
        errors.append("invalid_outcome")
    if phase < 1 or phase > 4:
        errors.append("invalid_phase")
    if decision_date > as_of:
        errors.append("decision_after_import_as_of")
    if evidence_as_of > as_of:
        errors.append("evidence_after_import_as_of")
    if decision_date > evidence_as_of:
        errors.append("evidence_predates_decision")
    if not row["source_url"].strip().startswith("https://"):
        errors.append("source_not_https")
    if errors:
        return None, errors
    return HistoricalOutcomeRecord(
        case_id=row["case_id"].strip(), application_id=row["application_id"].strip(),
        drug_name=row["drug_name"].strip(), sponsor=row["sponsor"].strip(),
        indication=row["indication"].strip(), therapeutic_area=row["therapeutic_area"].strip(),
        modality=row["modality"].strip(), phase=phase, decision_date=decision_date,
        outcome=outcome, evidence_as_of=evidence_as_of, source_url=row["source_url"].strip(),
        source_title=row["source_title"].strip(),
    ), []

def validate_csv(path: str | Path, *, as_of: date) -> dict:
    accepted: list[HistoricalOutcomeRecord] = []
    rejected: list[dict] = []
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = sorted(set(REQUIRED_COLUMNS) - set(reader.fieldnames or []))
        if missing:
            return {"status": "REJECTED_SCHEMA", "missing_columns": missing, "accepted": 0, "rejected": 0, "records": []}
        for line_number, row in enumerate(reader, start=2):
            record, errors = validate_record(row, as_of=as_of)
            if errors:
                rejected.append({"line": line_number, "case_id": row.get("case_id", ""), "errors": errors})
            else:
                accepted.append(record)
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in accepted:
        if record.case_id in seen:
            duplicates.add(record.case_id)
        seen.add(record.case_id)
    if duplicates:
        rejected.extend({"case_id": case_id, "errors": ["duplicate_case_id"]} for case_id in sorted(duplicates))
        accepted = [record for record in accepted if record.case_id not in duplicates]
    return {
        "status": "VALIDATED" if accepted and not rejected else "REVIEW_REQUIRED",
        "accepted": len(accepted), "rejected": len(rejected), "rejections": rejected,
        "records": accepted,
    }
