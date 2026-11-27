"""Flag reviewer claims inconsistent with *published source metadata*.

Metadata is only a publication-derived candidate, not an original-document
adjudication. Findings are REVIEW WARNINGS, never proof that the source or
reviewer is right. Do not use these warnings as FDA decisions or labels.
"""
from __future__ import annotations

import re
from datetime import date

from .hop_fda_reviewer_reconciliation import APPLICATION_ID

ALLOWED_FLAGS = (
    "REVIEWED_APPLICATION_NOT_IN_SOURCE_CANDIDATES",
    "PUBLISHED_SOURCE_APPLICATION_ID_MISSING",
    "ACTION_DATE_DIFFERS_FROM_PUBLISHED_LETTER_DATE",
    "PUBLISHED_LETTER_DATE_MISSING_OR_INVALID",
    "DOCUMENT_TYPE_DIFFERS_FROM_PUBLISHED_LETTER_TYPE",
    "PUBLISHED_LETTER_TYPE_MISSING",
)
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")


def _normalized_ids(value: str) -> set[str]:
    if not isinstance(value, str):
        raise ValueError("Missing published source application metadata")
    tokens = [part.strip().upper() for part in value.split(";") if part.strip()]
    # The worksheet's candidate fields are *provisional*: malformed candidate
    # identity is not a verified match and must be investigated.
    return {part.replace("-", "") for part in tokens
            if APPLICATION_ID.fullmatch(part)}


def _normalized_document_type(value: str) -> str:
    return " ".join(value.upper().split())


def source_consistency_flags(source: dict, reviewer: dict) -> list[str]:
    """Compare one reported full review to source metadata; emit no labels.

    Only caller-validated, complete reviewer reports should be supplied here.
    Different original FDA action dates or applications may be valid in
    multi-application source documents: flag for investigation, do not reject.
    """
    if not isinstance(source, dict) or not isinstance(reviewer, dict):
        raise ValueError("Source and reviewer claims must be objects")
    expected = (
        "published_application_ids", "canonical_application_candidates",
        "source_letter_date_as_published", "published_letter_type",
    )
    submitted = ("observed_application_ids", "observed_action_date",
                 "observed_document_type")
    if any(not isinstance(source.get(k), str) for k in expected) or any(
        not isinstance(reviewer.get(k), str) or not reviewer[k].strip()
        for k in submitted
    ):
        raise ValueError("Metadata consistency check requires complete review fields")

    flagged: set[str] = set()
    source_ids = (_normalized_ids(source["published_application_ids"])
                  | _normalized_ids(source["canonical_application_candidates"]))
    reported = _normalized_ids(reviewer["observed_application_ids"])
    if not reported:
        raise ValueError("Invalid claimed reviewer application IDs")
    if not source_ids:
        flagged.add("PUBLISHED_SOURCE_APPLICATION_ID_MISSING")
    elif not reported.issubset(source_ids):
        flagged.add("REVIEWED_APPLICATION_NOT_IN_SOURCE_CANDIDATES")

    source_date = source["source_letter_date_as_published"].strip()
    if not _DATE.fullmatch(source_date):
        flagged.add("PUBLISHED_LETTER_DATE_MISSING_OR_INVALID")
    else:
        try:
            date.fromisoformat(source_date)
        except ValueError:
            flagged.add("PUBLISHED_LETTER_DATE_MISSING_OR_INVALID")
        else:
            if source_date != reviewer["observed_action_date"]:
                flagged.add("ACTION_DATE_DIFFERS_FROM_PUBLISHED_LETTER_DATE")

    published_type = _normalized_document_type(source["published_letter_type"])
    reported_type = _normalized_document_type(reviewer["observed_document_type"])
    if not published_type:
        flagged.add("PUBLISHED_LETTER_TYPE_MISSING")
    elif published_type != reported_type:
        flagged.add("DOCUMENT_TYPE_DIFFERS_FROM_PUBLISHED_LETTER_TYPE")

    return [flag for flag in ALLOWED_FLAGS if flag in flagged]
