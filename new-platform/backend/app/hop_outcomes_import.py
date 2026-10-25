"""Fail-closed *schema* intake for manually curated historical FDA action evidence.

Parsing a CSV does not verify FDA source content, completeness of the application
denominator, a review-cycle label, or the point-in-time availability of features.
The imported records are never approved for training or prediction by this module.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

REQUIRED_COLUMNS = (
    "case_id", "application_id", "review_cycle", "drug_name", "sponsor",
    "indication", "therapeutic_area", "modality", "phase", "decision_date",
    "outcome", "public_features_as_of", "evidence_as_of", "source_url",
    "source_title",
)
ALLOWED_OUTCOMES = {"APPROVED", "COMPLETE_RESPONSE", "WITHDRAWN", "OTHER_NONAPPROVAL"}
OFFICIAL_FDA_HOSTS = frozenset({
    "fda.gov", "www.fda.gov", "accessdata.fda.gov",
    "open.fda.gov", "download.open.fda.gov",
})
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
APPLICATION_PATTERN = re.compile(r"(NDA|BLA|ANDA)-?[0-9]{6}\Z")


@dataclass(frozen=True)
class HistoricalOutcomeRecord:
    case_id: str
    application_id: str
    review_cycle: int
    drug_name: str
    sponsor: str
    indication: str
    therapeutic_area: str
    modality: str
    phase: int
    decision_date: date
    outcome: str
    public_features_as_of: date
    evidence_as_of: date
    source_url: str
    source_title: str


def _date(value: str) -> date:
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise ValueError("date must be YYYY-MM-DD")
    return date.fromisoformat(value)


def _fda_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return (
            parsed.scheme == "https"
            and parsed.hostname in OFFICIAL_FDA_HOSTS
            and parsed.username is None
            and parsed.password is None
            and parsed.port is None
            and bool(parsed.path and parsed.path != "/")
            and not parsed.fragment
        )
    except (ValueError, TypeError):
        return False


def validate_record(row: dict[str, str], *, as_of: date) -> tuple[HistoricalOutcomeRecord | None, list[str]]:
    errors: list[str] = []
    if not isinstance(row, dict):
        return None, ["row_not_object"]
    for col in REQUIRED_COLUMNS:
        value = row.get(col)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"missing:{col}")
    if errors:
        return None, errors
    try:
        decision_date = _date(row["decision_date"].strip())
        evidence_as_of = _date(row["evidence_as_of"].strip())
        features_as_of = _date(row["public_features_as_of"].strip())
        if not re.fullmatch(r"[1-4]", row["phase"].strip()):
            raise ValueError("invalid phase")
        phase = int(row["phase"].strip())
        if not re.fullmatch(r"[1-9][0-9]*", row["review_cycle"].strip()):
            raise ValueError("invalid cycle")
        review_cycle = int(row["review_cycle"].strip())
    except (ValueError, TypeError):
        return None, ["invalid_date_phase_or_review_cycle"]

    outcome = row["outcome"].strip().upper()
    if outcome not in ALLOWED_OUTCOMES:
        errors.append("invalid_outcome")
    if decision_date > as_of:
        errors.append("decision_after_import_as_of")
    if evidence_as_of > as_of:
        errors.append("outcome_evidence_after_import_as_of")
    if features_as_of > as_of:
        errors.append("features_after_import_as_of")
    if evidence_as_of < decision_date:
        errors.append("outcome_evidence_predates_decision")
    if features_as_of >= decision_date:
        errors.append("features_not_predecision")
    application_id = row["application_id"].strip().upper()
    if not APPLICATION_PATTERN.fullmatch(application_id):
        errors.append("invalid_application_id")
    if not _fda_url(row["source_url"].strip()):
        errors.append("source_not_official_fda_https")
    if errors:
        return None, errors
    return HistoricalOutcomeRecord(
        case_id=row["case_id"].strip(),
        application_id=application_id.replace("-", ""),
        review_cycle=review_cycle,
        drug_name=row["drug_name"].strip(),
        sponsor=row["sponsor"].strip(),
        indication=row["indication"].strip(),
        therapeutic_area=row["therapeutic_area"].strip(),
        modality=row["modality"].strip(),
        phase=phase,
        decision_date=decision_date,
        outcome=outcome,
        public_features_as_of=features_as_of,
        evidence_as_of=evidence_as_of,
        source_url=row["source_url"].strip(),
        source_title=row["source_title"].strip(),
    ), []


def validate_csv(path: str | Path, *, as_of: date) -> dict:
    """Return quarantined parsed records plus row-level errors; never model clearance."""
    accepted: list[HistoricalOutcomeRecord] = []
    rejected: list[dict] = []
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        missing = sorted(set(REQUIRED_COLUMNS) - set(headers))
        unexpected = sorted(set(headers) - set(REQUIRED_COLUMNS))
        if missing or unexpected or len(headers) != len(set(headers)):
            return {
                "status": "REJECTED_SCHEMA",
                "missing_columns": missing,
                "unexpected_columns": unexpected,
                "duplicate_headers": len(headers) != len(set(headers)),
                "accepted": 0, "rejected": 0, "records": [],
                "model_eligible_records": 0, "independently_verified": False,
                "probability": None,
            }
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                rejected.append({"line": line_number, "case_id": row.get("case_id", ""),
                                 "errors": ["extra_csv_fields"]})
                continue
            record, errors = validate_record(row, as_of=as_of)
            if errors:
                rejected.append({"line": line_number, "case_id": row.get("case_id", ""),
                                 "errors": errors})
            else:
                accepted.append(record)

    case_keys: dict[str, int] = {}
    cycle_keys: dict[tuple[str, int], int] = {}
    for record in accepted:
        case_keys[record.case_id] = case_keys.get(record.case_id, 0) + 1
        key = (record.application_id, record.review_cycle)
        cycle_keys[key] = cycle_keys.get(key, 0) + 1
    unique_records = []
    for record in accepted:
        reasons = []
        if case_keys[record.case_id] > 1:
            reasons.append("duplicate_case_id")
        if cycle_keys[(record.application_id, record.review_cycle)] > 1:
            reasons.append("duplicate_application_review_cycle")
        if reasons:
            rejected.append({"case_id": record.case_id, "errors": reasons})
        else:
            unique_records.append(record)
    return {
        "status": "SCHEMA_VALIDATED_REVIEW_REQUIRED" if unique_records and not rejected
                  else "REVIEW_REQUIRED",
        "accepted": len(unique_records),
        "rejected": len(rejected),
        "rejections": rejected,
        "records": unique_records,
        "model_eligible_records": 0,
        "independently_verified": False,
        "probability": None,
    }
