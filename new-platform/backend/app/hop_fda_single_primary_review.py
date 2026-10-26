"""Optional ONE primary reviewer for quarantined FDA source identity-gap research.

The earlier A/B independent review remains available for disputed records, but
a routine source-search packet no longer needs an unused second reviewer copy.
Primary reviewer *claims* do not authenticate a person, independently verify
an original FDA action, reconstruct the NDA/BLA denominator, or authorize
model labels. This module has no network, database, cloud or prediction writes.
"""
from __future__ import annotations

import copy
import re
from collections import Counter
from datetime import date

from .hop_fda_identity_gap_dual_review import (
    ALLOWED_CLASS, APP, CLAIM_FIELDS, LOCKED, PAGES, REVIEWER, REVIEW_STATUS,
    SOURCE_STATUS, SUBMISSION_CLASS, _lock,
)
from .hop_fda_private_review_batches import prepare_private_review_batches

SINGLE = "SINGLE_PRIMARY_REVIEW_ONLY_NOT_INDEPENDENTLY_VERIFIED"
AWAITING = "AWAITING_PRIMARY_REVIEW"
ESCALATE = "SECOND_SOURCE_CHECK_RECOMMENDED"
PRELIMINARY = "PRIMARY_REVIEW_CLAIM_RECORDED_NOT_AUTHENTICATED"
PRIORITY = ("AMBIGUOUS_ID", "APPLICATION_ID")


def prepare_single_primary_batches(
    first_blank_rows: list[dict], *, expected_references: int = 124,
    expected_groups: int = 101,
) -> tuple[list[dict], dict]:
    """Reuse the strict immutable A/B validation but emit FIRST role only.

    The memory-only SECOND copy does not represent an assigned second
    reviewer, a dual signoff, or a stored second reviewer handoff.
    """
    if not isinstance(first_blank_rows, list) or not first_blank_rows:
        raise ValueError("Primary FDA source packet list required")
    second_memory_only = []
    for original in first_blank_rows:
        if not isinstance(original, dict):
            raise ValueError("Malformed FDA primary source record")
        second = copy.deepcopy(original)
        second["packet_role"] = "SECOND"
        second_memory_only.append(second)
    batches, source_audit = prepare_private_review_batches(
        first_blank_rows, second_memory_only, max_references=20,
        expected_references=expected_references,
        expected_groups=expected_groups,
    )
    primary = [{
        "batch_id": batch["batch_id"],
        "review_category": batch["review_category"],
        "primary_blank_source_rows": batch["first_blank_reviewer_sources"],
        "research_groups": batch["research_groups"],
        "source_references": batch["source_references"],
        "primary_identity_authenticated": False,
        "reviewed_original_fda_actions_verified": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
    } for batch in batches]
    return primary, {
        "status": "BLANK_SINGLE_PRIMARY_FDA_REVIEW_BATCHES_PREPARED",
        "review_mode": SINGLE,
        "primary_reviewer_slots": 1,
        "independent_second_reviewer_required_for_all": False,
        "second_review_escalation_available": True,
        "published_letter_references": source_audit["published_letter_references"],
        "research_group_count": source_audit["application_research_groups"],
        "batch_count": len(primary),
        "primary_blank_source_rows": sum(
            b["source_references"] for b in primary
        ),
        "second_review_files_exported": 0,
        "priority_batches": [b["batch_id"] for b in primary],
        "primary_reviewer_authenticated": False,
        "independently_verified_original_fda_actions": 0,
        "complete_original_nda_bla_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "source_identifiers_not_exported_in_public_audit": True,
    }


def reconcile_single_primary_claims(
    baseline_first: list[dict], first_claims: list[dict], *, as_of: date,
) -> dict:
    """Triage typed source claims; never certify review or emit row-level IDs.

    The public-safe result includes category counts only. The private original
    claims must remain separately retained and access controlled.
    """
    if not isinstance(as_of, date):
        raise ValueError("An FDA research cutoff date is required")
    # Validate baseline source locks, exact original research cohort and
    # blank model gates before examining any submitted observations.
    _, inventory = prepare_single_primary_batches(baseline_first)
    if (not isinstance(first_claims, list)
            or len(first_claims) != inventory["published_letter_references"]):
        raise ValueError("Single-reviewer FDA claims missing source references")
    by_source = {}
    for row in baseline_first:
        sid = row["published_letter_source_sha256"]
        if sid in by_source:
            raise ValueError("Duplicate baseline FDA source hash")
        by_source[sid] = row

    seen = set()
    counts = Counter()
    claimed_tokens = set()
    for row in first_claims:
        if not isinstance(row, dict):
            raise ValueError("Malformed FDA reviewer observation")
        sid = row.get("published_letter_source_sha256")
        if sid not in by_source or sid in seen:
            raise ValueError("FDA reviewer claims duplicated or missing source")
        seen.add(sid)
        original = by_source[sid]
        if (set(row) != set(original)
                or any(row[key] != value for key, value in original.items()
                       if key not in ("reviewer_token", *CLAIM_FIELDS))
                or row.get("source_lock_sha256") != _lock(row)
                or row.get("packet_role") != "FIRST"
                or row.get("review_packet_status") != REVIEW_STATUS
                or row.get("model_eligible") is not False
                or row.get("reviewer_authentication_verified") is not False
                or row.get("independent_regulatory_adjudication_verified") is not False):
            raise ValueError("FDA original source or model acceptance flag altered")
        token = row["reviewer_token"]
        if not isinstance(token, str) or (token and not REVIEWER.fullmatch(token)):
            raise ValueError("Invalid FDA claimed reviewer token")
        if token:
            claimed_tokens.add(token)
        for field in CLAIM_FIELDS:
            value = row[field]
            if (not isinstance(value, str)
                    or len(value) > (4000 if field == "source_evidence_notes" else 140)
                    or value.lstrip().startswith(("=", "+", "-", "@"))
                    or "\x00" in value):
                raise ValueError("Malformed or unsafe FDA source observation")
        if row["observed_application_id"] and not APP.fullmatch(row["observed_application_id"]):
            raise ValueError("Observed original FDA application ID invalid")
        if (row["observed_submission_class"]
                and row["observed_submission_class"] not in SUBMISSION_CLASS):
            raise ValueError("Unknown FDA original/supplement classification")
        if (row["observed_document_class"]
                and row["observed_document_class"] not in ALLOWED_CLASS):
            raise ValueError("Unknown FDA original regulatory action class")
        if row["observed_letter_pages"]:
            pages = row["observed_letter_pages"]
            if not PAGES.fullmatch(pages):
                raise ValueError("Original FDA page range malformed")
            nums = [int(p) for p in pages.split("-")]
            if len(nums) == 2 and nums[0] > nums[1]:
                raise ValueError("Original FDA page range reversed")
        if row["observed_fda_action_date"]:
            try:
                claimed_date = date.fromisoformat(row["observed_fda_action_date"])
            except ValueError:
                raise ValueError("Malformed original FDA action date") from None
            if claimed_date > as_of:
                raise ValueError("Claimed FDA action occurred after review cutoff")
        if row["observed_review_cycle"] and not re.fullmatch(
                r"(?:[1-9][0-9]{0,2}|UNKNOWN)", row["observed_review_cycle"]):
            raise ValueError("Original FDA review-cycle claim invalid")

        filled = bool(token) and all(
            isinstance(row[f], str) and bool(row[f].strip()) for f in CLAIM_FIELDS
        )
        if not filled:
            counts[AWAITING] += 1
            continue
        if (original["application_id_candidate"] is None
                or original["prior_pdf_source_status"] == SOURCE_STATUS[1]
                or row["observed_application_id"] !=
                    original["application_id_candidate"]
                or row["observed_submission_class"] != "ORIGINAL"
                or row["observed_review_cycle"] == "UNKNOWN"
                or row["observed_document_class"] == "OTHER_OR_UNCLASSIFIED"):
            counts[ESCALATE] += 1
        else:
            counts[PRELIMINARY] += 1
    if len(seen) != len(by_source):
        raise ValueError("Incomplete original FDA reviewer submission")
    if len(claimed_tokens) > 1:
        raise ValueError("One primary reviewer cannot claim multiple reviewer tokens")
    return {
        "status": "SINGLE_PRIMARY_FDA_CLAIMS_TRIAGED_NOT_ADJUDICATED",
        "review_mode": SINGLE,
        "published_letter_references": len(by_source),
        "single_reviewer_record_counts": {
            AWAITING: counts[AWAITING],
            ESCALATE: counts[ESCALATE],
            PRELIMINARY: counts[PRELIMINARY],
        },
        "additional_review_recommended_references": counts[ESCALATE],
        "provisional_single_reviewer_claims": counts[PRELIMINARY],
        "claimed_reviewer_token_present": bool(claimed_tokens),
        "reviewer_identity_authenticated": False,
        "independently_verified_original_fda_actions": 0,
        "complete_original_nda_bla_denominator_verified": False,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "readiness": "REVIEW_REQUIRED",
        "individual_reviewer_data_not_exported": True,
    }
