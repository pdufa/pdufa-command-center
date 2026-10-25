"""Create two independently fillable, *unreviewed* FDA source packets.

Input is the quarantined page-worksheet CSV, not an adjudicated outcome cohort.
Neither packet may claim an FDA decision, a completed review or model eligibility.
All operations are offline; reviewer independence must be verified separately.
"""
from __future__ import annotations

import csv
import io
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from .hop_fda_page_review_worksheet import COLUMNS, ALLOWED_STATUS

SHA256 = re.compile(r"[0-9a-f]{64}\\Z")
VERIFICATION_FIELDS = (
    "original_letter_page_range_verified", "effective_fda_action_date_verified",
    "regulatory_review_cycle_verified", "regulatory_outcome_verified",
    "independent_review_complete", "model_eligible",
)
EMPTY_REVIEW_FIELDS = (
    "first_reviewer", "first_reviewer_observed_page_range",
    "first_reviewer_original_fda_action_date", "first_reviewer_document_action_type",
    "first_reviewer_evidence_notes", "second_reviewer",
    "second_reviewer_evidence_notes", "independent_discrepancy_resolution",
)
SOURCE_FIELDS = (
    "review_priority", "review_reason", "source_record_sha256",
    "fda_pdf_sha256", "fda_pdf_url", "provisional_page_link",
    "published_application_ids", "canonical_application_candidates",
    "source_letter_date_as_published", "published_letter_type",
    "candidate_status", "candidate_pages_1_based", "candidate_page_count",
    "cross_application_pdf", "same_date_type_collision",
)
PACKET_COLUMNS = (
    "packet_role", "packet_status", *SOURCE_FIELDS,
    "reviewer_id", "observed_pdf_sha256", "observed_letter_pages",
    "observed_application_ids", "observed_action_date",
    "observed_document_type", "observed_review_cycle",
    "source_evidence_notes",
)
STATUS = "UNREVIEWED_SOURCE_REFERENCE_NOT_OUTCOME_COHORT"


def _false(value: object) -> bool:
    return value is False or value == "False"


def _csv_safe(value: object) -> bool:
    if not isinstance(value, str):
        return False
    # Avoid spreadsheet formula execution when the packets are opened as CSV.
    return not value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n"))


def _official_pdf(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https" and parsed.hostname == "download.open.fda.gov"
            and parsed.path.startswith("/crl/") and parsed.path.endswith(".pdf")
            and not parsed.username and not parsed.password and parsed.port is None
            and not parsed.query and not parsed.fragment
        )
    except (ValueError, TypeError):
        return False


def load_unreviewed_worksheet(path: str | Path) -> list[dict[str, str]]:
    """Require exact official worksheet headers; no silently discarded columns."""
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(COLUMNS):
            raise ValueError("Expected exact quarantined FDA worksheet CSV headers")
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("Malformed worksheet CSV row")
    return rows


def build_dual_review_packets(
    rows: list[dict],
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict]:
    """Return two identically scoped blank reviews and a *nonclinical* audit."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("No FDA published-letter source references to review")
    seen: set[str] = set()
    priorities: Counter[str] = Counter()
    first: list[dict[str, str]] = []
    second: list[dict[str, str]] = []

    for row in rows:
        if not isinstance(row, dict) or set(row) != set(COLUMNS):
            raise ValueError("Missing or unexpected worksheet fields")
        if (row.get("review_status") != "NOT_ADJUDICATED"
                or any(not _false(row.get(k)) for k in VERIFICATION_FIELDS)
                or any(row.get(k) != "" for k in EMPTY_REVIEW_FIELDS)):
            raise ValueError("Cannot prepare blank packets from reviewed or promoted data")
        digest = row["source_record_sha256"]
        pdf_sha = row["fda_pdf_sha256"]
        if (not isinstance(digest, str) or not SHA256.fullmatch(digest)
                or digest in seen or not isinstance(pdf_sha, str)
                or not SHA256.fullmatch(pdf_sha)):
            raise ValueError("Repeated or invalid source identity/hash")
        seen.add(digest)
        if not _official_pdf(row["fda_pdf_url"]):
            raise ValueError("Unexpected or unsafe FDA source URL")
        if (row["candidate_status"] not in ALLOWED_STATUS
                or str(row["review_priority"]) not in {"1", "2", "3", "4", "5", "6"}
                or not row["review_reason"]):
            raise ValueError("Unknown provisional review priority/status")
        if any(not _csv_safe(row[k]) for k in SOURCE_FIELDS if isinstance(row[k], str)):
            raise ValueError("Spreadsheet-formula-like source cell rejected")
        page_link = row["provisional_page_link"]
        if page_link:
            if (not isinstance(page_link, str)
                    or not re.fullmatch(re.escape(row["fda_pdf_url"]) + r"#page=[1-9][0-9]*", page_link)):
                raise ValueError("Provisional page link changed source")
        candidate_text = row["candidate_pages_1_based"]
        page_values = [] if not candidate_text else [part.strip() for part in candidate_text.split(",")]
        if any(not re.fullmatch(r"[1-9][0-9]*", page) for page in page_values):
            raise ValueError("Invalid provisional page number")
        if len(set(page_values)) != len(page_values):
            raise ValueError("Duplicate page number")
        try:
            candidate_count = int(row["candidate_page_count"])
        except (ValueError, TypeError):
            raise ValueError("Invalid candidate page count") from None
        if candidate_count != len(page_values):
            raise ValueError("Provisional page count mismatch")
        priorities[str(row["review_priority"])] += 1
        common = {key: str(row[key]) for key in SOURCE_FIELDS}
        for role, destination in (("FIRST", first), ("SECOND", second)):
            destination.append({
                "packet_role": role,
                "packet_status": STATUS,
                **common,
                "reviewer_id": "",
                "observed_pdf_sha256": "",
                "observed_letter_pages": "",
                "observed_application_ids": "",
                "observed_action_date": "",
                "observed_document_type": "",
                "observed_review_cycle": "",
                "source_evidence_notes": "",
            })

    return first, second, {
        "status": "DUAL_REVIEW_PACKETS_PREPARED_NOT_ADJUDICATED",
        "published_letter_references": len(seen),
        "first_reviewer_blank_packets": len(first),
        "second_reviewer_blank_packets": len(second),
        "priority_counts": dict(sorted(priorities.items())),
        "reviewer_identity_verified": False,
        "independent_review_pairs_completed": 0,
        "original_page_ranges_verified": 0,
        "fda_review_cycle_outcomes_verified": 0,
        "complete_application_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "note": "Two blank copies are not independent reviews or verified regulatory outcomes.",
    }


def packet_csv(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=PACKET_COLUMNS, extrasaction="raise",
                            lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if (row.get("packet_status") != STATUS
                or row.get("packet_role") not in {"FIRST", "SECOND"}
                or any(row.get(k) != "" for k in PACKET_COLUMNS if k not in
                       {"packet_role", "packet_status", *SOURCE_FIELDS})):
            raise ValueError("Refuse to export completed or modified reviewer packet")
        writer.writerow(row)
    return buffer.getvalue()
