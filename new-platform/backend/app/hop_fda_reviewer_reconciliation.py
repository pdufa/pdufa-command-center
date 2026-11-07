"""Compare two local, claimed FDA source reviews without adjudicating outcomes.

This is an offline *difference detector*. Reviewer identities, actual original
document bytes, independence, and scientific/regulatory conclusions are NOT
authenticated here. Even identical answers remain quarantined and ineligible
for training, scoring, or live prediction.
"""
from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

from .hop_fda_dual_review_packets import (
    PACKET_COLUMNS, SOURCE_FIELDS, STATUS, SHA256, build_dual_review_packets,
)

OBSERVED_FIELDS = (
    "observed_pdf_sha256", "observed_letter_pages",
    "observed_application_ids", "observed_action_date",
    "observed_document_type", "observed_review_cycle",
)
COMPLETE_FIELDS = (*OBSERVED_FIELDS, "source_evidence_notes")
APPLICATION_ID = re.compile(r"(?:NDA|BLA|ANDA)-?[0-9]{6}\Z")
DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
PAGES = re.compile(r"[1-9][0-9]{0,5}(?:-[1-9][0-9]{0,5})?\Z")
REVIEWER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@-]{2,79}\Z")
DOCUMENT_TYPE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 /()._-]{0,99}\Z")


def load_completed_or_blank_packet(path: str | Path) -> list[dict[str, str]]:
    """Read strictly shaped CSV responses, refusing extra or missing cells."""
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(PACKET_COLUMNS):
            raise ValueError("Reviewer packet headers do not match source contract")
        rows = list(reader)
    if any(None in row or any(not isinstance(value, str) for value in row.values())
           for row in rows):
        raise ValueError("Malformed reviewer packet row")
    return rows


def _reviewer_claims(row: dict[str, str], source: dict[str, str], *,
                     role: str, cutoff: date) -> bool:
    """Validate only syntax and provenance lock, never reviewer credibility."""
    if (row.get("packet_role") != role or row.get("packet_status") != STATUS
            or any(row.get(col) != source[col] for col in SOURCE_FIELDS)):
        raise ValueError("Packet source fields modified, role changed, or status promoted")

    reviewer = row["reviewer_id"]
    if reviewer and not REVIEWER.fullmatch(reviewer):
        raise ValueError("Invalid reviewer token")
    digest = row["observed_pdf_sha256"]
    if digest and (not SHA256.fullmatch(digest) or digest != source["fda_pdf_sha256"]):
        raise ValueError("Observed PDF digest missing or different from source inventory")
    pages = row["observed_letter_pages"]
    if pages:
        if not PAGES.fullmatch(pages):
            raise ValueError("Observed page interval is invalid")
        numbers = [int(x) for x in pages.split("-")]
        if len(numbers) == 2 and numbers[0] > numbers[1]:
            raise ValueError("Observed page interval reversed")
    applications = row["observed_application_ids"]
    if applications:
        ids = [value.strip() for value in applications.split(";")]
        if any(not APPLICATION_ID.fullmatch(value) for value in ids):
            raise ValueError("Invalid reviewed application identifiers")
        normalized = [value.replace("-", "") for value in ids]
        if len(set(normalized)) != len(normalized):
            raise ValueError("Duplicate reviewed application identity")
    action_date = row["observed_action_date"]
    if action_date:
        if not DAY.fullmatch(action_date):
            raise ValueError("Invalid claimed FDA action date")
        try:
            parsed = date.fromisoformat(action_date)
        except ValueError:
            raise ValueError("Invalid claimed FDA action date") from None
        if parsed > cutoff:
            raise ValueError("Claimed FDA action date is in the future")
    document_type = row["observed_document_type"]
    if document_type and not DOCUMENT_TYPE.fullmatch(document_type):
        raise ValueError("Invalid reviewed document-type field")
    cycle = row["observed_review_cycle"]
    if cycle and (not re.fullmatch(r"[1-9][0-9]{0,2}", cycle)):
        raise ValueError("Invalid positive review-cycle number")
    notes = row["source_evidence_notes"]
    if len(notes) > 5000 or (notes and (
        notes.lstrip().startswith(("=", "+", "-", "@"))
        or "\x00" in notes
    )):
        raise ValueError("Unsafe or excessive evidence notes")
    return bool(reviewer and all(row[field].strip() for field in COMPLETE_FIELDS))


def reconcile_review_claims(
    original_rows: list[dict[str, str]],
    first: list[dict[str, str]],
    second: list[dict[str, str]],
    *, as_of: date,
) -> dict:
    """Compare complete claims; no approval of reviewer identities or outcomes."""
    if not isinstance(as_of, date):
        raise ValueError("A controlled calendar cutoff is required")
    # Re-verify the original worksheet remains unreviewed and source-locked.
    expected_first, expected_second, _ = build_dual_review_packets(original_rows)
    expected = {row["source_record_sha256"]: row for row in expected_first}

    def index(rows: list[dict[str, str]], role: str) -> dict[str, dict[str, str]]:
        if not isinstance(rows, list):
            raise ValueError("Invalid reviewer packet")
        records: dict[str, dict[str, str]] = {}
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(PACKET_COLUMNS):
                raise ValueError("Invalid reviewer packet columns")
            identity = row["source_record_sha256"]
            if identity not in expected or identity in records:
                raise ValueError("Missing, duplicate, or unknown FDA source reference")
            _reviewer_claims(row, expected[identity], role=role, cutoff=as_of)
            records[identity] = row
        if set(records) != set(expected):
            raise ValueError("Reviewer packet omits one or more original source references")
        return records

    a = index(first, "FIRST")
    b = index(second, "SECOND")
    ids_a = {r["reviewer_id"] for r in first if r["reviewer_id"]}
    ids_b = {r["reviewer_id"] for r in second if r["reviewer_id"]}
    if len(ids_a) > 1 or len(ids_b) > 1:
        raise ValueError("More than one claimed reviewer per packet")
    if ids_a and ids_b and ids_a == ids_b:
        raise ValueError("Both packets claim the same reviewer identity")

    agreements = 0
    disagreements = 0
    incomplete = 0
    dispute_rows = []
    for identity in sorted(expected):
        lhs, rhs = a[identity], b[identity]
        full_a = bool(lhs["reviewer_id"] and all(lhs[k].strip() for k in COMPLETE_FIELDS))
        full_b = bool(rhs["reviewer_id"] and all(rhs[k].strip() for k in COMPLETE_FIELDS))
        if not full_a or not full_b:
            incomplete += 1
            continue
        # Normalize only cosmetic application-ID hyphens; do not infer cycles.
        diff = []
        for field in OBSERVED_FIELDS:
            left, right = lhs[field], rhs[field]
            if field == "observed_application_ids":
                left = tuple(v.strip().replace("-", "") for v in left.split(";"))
                right = tuple(v.strip().replace("-", "") for v in right.split(";"))
            if left != right:
                diff.append(field)
        if diff:
            disagreements += 1
            # Source digest and field names are not reviewer notes or identities.
            dispute_rows.append({
                "source_record_sha256": identity,
                "disputed_fields": diff,
            })
        else:
            agreements += 1

    total = len(expected)
    if total != agreements + disagreements + incomplete:
        raise ValueError("Source comparison does not reconcile")
    return {
        "status": "REVIEW_CLAIMS_COMPARED_NO_INDEPENDENT_ADJUDICATION",
        "source_reference_rows": total,
        "two_reported_complete_claims": agreements + disagreements,
        "matching_unverified_claims": agreements,
        "disagreeing_unverified_claims": disagreements,
        "incomplete_or_missing_reviewer_claims": incomplete,
        "disagreements_needing_human_resolution": dispute_rows,
        "claimed_distinct_reviewer_tokens": len(ids_a) + len(ids_b),
        "reviewer_identity_authenticated": False,
        "reviewer_independence_confirmed": False,
        "independently_verified_review_cycles": 0,
        "complete_application_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "approval_rate": None,
        "readiness": "REVIEW_REQUIRED",
        "note": (
            "Matching reviewer text is not independent source verification. "
            "All original FDA source and decision claims require qualified "
            "independent authentication, adjudication and denominator validation."
        ),
    }
