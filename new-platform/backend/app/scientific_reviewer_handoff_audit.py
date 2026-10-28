"""Offline A/B reviewer worksheet reconciliation. Zero external trust or write effects.

The input CSVs are *editable human handoff worksheets*; they are never proof
of reviewer identity, source authenticity, signatures or completed science.
This audit rejects corrupted inventories, reports candidate observations and
disagreements, and can NEVER promote a scientific score or FDA prediction.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
import io
import json
from pathlib import Path
import re
from typing import Any

from .scientific_investigation_contract import LAYERS, DEPTH_LEVELS

BASE_FIELDS = (
    "nct_id", "layer", "assessment", "depth_level", "depth", "review_objective",
    "review_status", "independently_verified", "scientific_score",
    "fda_approval_probability",
)
REVIEWER_FIELDS = (
    "reviewer_slot", "reviewer_name", "qualification_verification",
    "primary_document_url", "document_sha256", "public_document_date",
    "evidence_section_or_table", "finding_notes", "reviewer_decision",
    "reviewer_signature", "submission_status",
)
DECISIONS = {"supports", "contradicts", "uncertain", "not_assessable"}
_SHA256 = re.compile(r"[a-fA-F0-9]{64}\Z")
_NCT = re.compile(r"NCT[0-9]{8}\Z")
_MAX_CSV_BYTES = 1024 * 1024
_MAX_CELL = 5000


def _read_csv(path: Path, header: tuple[str, ...]) -> list[dict[str, str]]:
    """Exact known schema, bounded size, complete 320 rows and no duplicate headers."""
    raw = path.read_bytes()
    if len(raw) > _MAX_CSV_BYTES or not raw or b"\x00" in raw:
        raise ValueError("Worksheet size or encoding is not accepted")
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if reader.fieldnames != list(header):
            raise ValueError("Worksheet header mismatch or duplicate column")
        rows = list(reader)
    except (UnicodeError, csv.Error) as error:
        raise ValueError("Worksheet CSV is malformed") from error
    if len(rows) != 320 or any(
        None in row or any(not isinstance(v, str) or len(v) > _MAX_CELL for v in row.values())
        for row in rows
    ):
        raise ValueError("Worksheet must contain exactly 320 complete, bounded rows")
    return rows


def _expected_base(nct_id: str) -> list[dict[str, str]]:
    if not isinstance(nct_id, str) or not _NCT.fullmatch(nct_id):
        raise ValueError("Exact trial NCT ID required")
    rows: list[dict[str, str]] = []
    for layer, questions in LAYERS.items():
        for question in questions:
            for depth_num, (depth_id, objective) in enumerate(DEPTH_LEVELS, start=1):
                rows.append(dict(zip(BASE_FIELDS, (
                    nct_id, layer, f"{layer}.{question}", str(depth_num), depth_id,
                    objective, "PENDING_INDEPENDENT_REVIEW", "FALSE",
                    "NOT_ASSIGNED", "NOT_ASSIGNED",
                ))))
    if len(rows) != 320:
        raise ValueError("Scientific task contract is not a complete 320-task plan")
    return rows


def _source_is_well_formed(row: dict[str, str]) -> bool:
    """Only syntactic provenance, NOT fetched content or independently checked bytes."""
    url = row["primary_document_url"]
    sha = row["document_sha256"]
    raw_date = row["public_document_date"]
    try:
        parsed_date = date.fromisoformat(raw_date)
    except ValueError:
        return False
    return (
        url.startswith("https://") and len(url) <= 2000
        and "\n" not in url and "\r" not in url and "\t" not in url
        and _SHA256.fullmatch(sha) is not None
        and parsed_date <= date.today()
        and bool(row["evidence_section_or_table"].strip())
    )


def reconcile_handoff_files(
    nct_id: str, inventory_path: Path, reviewer_a_path: Path, reviewer_b_path: Path,
) -> dict[str, Any]:
    """Read three *local* CSVs, validate immutable inventory and compare candidates.

    A full set of perfectly matching human-entered values is not an authenticated
    review. These reports must never be consumed as an evidence admission gate.
    """
    expected = _expected_base(nct_id)
    base = _read_csv(Path(inventory_path), BASE_FIELDS)
    if base != expected:
        raise ValueError("Inventory differs from exact-NCT scientific task contract")
    a = _read_csv(Path(reviewer_a_path), BASE_FIELDS + REVIEWER_FIELDS)
    b = _read_csv(Path(reviewer_b_path), BASE_FIELDS + REVIEWER_FIELDS)
    for rows, slot in ((a, "A"), (b, "B")):
        for i, row in enumerate(rows):
            if any(row[key] != expected[i][key] for key in BASE_FIELDS):
                raise ValueError(f"Reviewer {slot} task identity or source baseline altered")
            if row["reviewer_slot"] != slot:
                raise ValueError("Reviewer handoff slot identity mismatch")
            if row["qualification_verification"] != "NOT_VERIFIED":
                raise ValueError("Worksheet claims unauthorized qualification verification")
            if row["submission_status"] != "NOT_SUBMITTED":
                raise ValueError("Worksheet claims unauthorized submission or signoff")
            if row["reviewer_decision"] not in DECISIONS | {"NOT_SUBMITTED"}:
                raise ValueError("Worksheet contains an unrecognized reviewer decision")
    candidate_count = {"A": 0, "B": 0}
    provenance_missing = {"A": 0, "B": 0}
    incomplete_notes = {"A": 0, "B": 0}
    disagreements: list[str] = []
    notes_without_a_second_candidate = 0

    def candidate(row: dict[str, str], slot: str) -> bool:
        if row["reviewer_decision"] == "NOT_SUBMITTED":
            return False
        if not _source_is_well_formed(row):
            provenance_missing[slot] += 1
            return False
        if not row["reviewer_name"].strip() or not row["finding_notes"].strip():
            incomplete_notes[slot] += 1
            return False
        candidate_count[slot] += 1
        return True

    for row_a, row_b in zip(a, b):
        good_a = candidate(row_a, "A")
        good_b = candidate(row_b, "B")
        if good_a != good_b:
            notes_without_a_second_candidate += 1
        if good_a and good_b and row_a["reviewer_decision"] != row_b["reviewer_decision"]:
            disagreements.append(row_a["assessment"] + ":" + row_a["depth_level"])
    return {
        "nctId": nct_id,
        "mode": "offline_untrusted_reviewer_worksheet_diagnostic",
        "inventoryTasksValidated": 320,
        "reviewerSlots": ["A", "B"],
        "candidateObservationsWithSyntacticProvenance": candidate_count,
        "candidateObservationsMissingValidProvenance": provenance_missing,
        "candidateObservationsMissingReviewerOrNotes": incomplete_notes,
        "tasksWithOnlyOneCandidateObservation": notes_without_a_second_candidate,
        "candidateDisagreementCount": len(disagreements),
        "candidateDisagreementTaskIds": disagreements,
        "sourceDocumentsFetchedAndAuthenticated": False,
        "reviewerIdentitiesAuthenticated": False,
        "qualificationsIndependentlyVerified": False,
        "cryptographicReviewerSignaturesVerified": False,
        "signedDisagreementsReconciled": False,
        "tasksIndependentlyAdjudicated": 0,
        "scientificScore": None,
        "fdaApprovalProbability": None,
        "readyForScientificConclusion": False,
        "promotionAllowed": False,
        "status": "REQUIRES_INDEPENDENT_AUTHENTICATION_AND_ADJUDICATION",
        "note": (
            "CSV entries and stated SHA-256 hashes are UNTRUSTED until source bytes "
            "are independently captured and matched; worksheet names or typed "
            "signatures are not authenticated clinical reviewer attestations."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nct-id", required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = reconcile_handoff_files(
            args.nct_id, args.inventory, args.reviewer_a, args.reviewer_b,
        )
    except (ValueError, OSError) as error:
        print(json.dumps({"status": "REJECTED_UNTRUSTED_INPUT", "reason": str(error)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    # Unverified worksheet inputs must never be represented as a passed science gate.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
