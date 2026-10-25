"""Source-linked, quarantined review queue for unmatched FDA letter identities.

Only identity resolution is in scope. A match is not an FDA approval and a
nonmatch is not a rejection. Review tickets never become outcome labels.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import re

STATUS_UNRESOLVED = "APPLICATION_ID_UNRESOLVED"
STATUS_AMBIGUOUS = "MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS"
STATUS_NONMATCH = "NOT_FOUND_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT"
STATUS_MATCH = "PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT"
ALL_STATUSES = {STATUS_UNRESOLVED, STATUS_AMBIGUOUS, STATUS_NONMATCH, STATUS_MATCH}

REVIEW_ACTIONS = {
    STATUS_UNRESOLVED: (
        "Find original application number and type in the official FDA letter "
        "or action package; do not infer BL-to-BLA equivalence."
    ),
    STATUS_AMBIGUOUS: (
        "Resolve which official application or applications the published "
        "letter addresses; preserve original/supplement distinctions."
    ),
    STATUS_NONMATCH: (
        "Check official application and review documentation for registry "
        "coverage and later actions; nonmatch does not establish rejection."
    ),
}
PRIORITY = {STATUS_UNRESOLVED: 1, STATUS_AMBIGUOUS: 2, STATUS_NONMATCH: 3}


def create_fda_identity_review_queue(crosswalk: dict, letter_snapshot: dict) -> tuple[dict, dict]:
    """Return identity-review tickets with exact original source provenance."""
    if crosswalk.get("status") != "IDENTITY_LINKAGE_ONLY_NOT_A_REVIEW_CYCLE_OUTCOME_COHORT":
        raise ValueError("crosswalk is not a quarantined identity-only source")
    if letter_snapshot.get("status") != "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT":
        raise ValueError("letters are not a quarantined publication source")
    links = crosswalk.get("records")
    letters = letter_snapshot.get("records")
    if not isinstance(links, list) or not isinstance(letters, list) or len(links) != len(letters):
        raise ValueError("FDA published-letter and identity-link counts differ")
    letter_map = {}
    for letter in letters:
        if not isinstance(letter, dict) or letter.get("model_eligible") is not False:
            raise ValueError("source letters must remain model-ineligible")
        digest = letter.get("source_record_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("missing source-letter SHA256")
        if digest in letter_map:
            raise ValueError("duplicate source-letter SHA256 requires adjudication")
        letter_map[digest] = letter
    counts = Counter()
    review_items = []
    linked_digests = set()
    for linked in links:
        if (not isinstance(linked, dict)
                or linked.get("model_eligible") is not False
                or linked.get("complete_cohort_verified") is not False
                or linked.get("point_in_time_outcome_verified") is not False):
            raise ValueError("identity link cannot be promoted to model evidence")
        digest = linked.get("letter_record_sha256")
        if digest in linked_digests or digest not in letter_map:
            raise ValueError("identity link has duplicate or unknown source digest")
        linked_digests.add(digest)
        source = letter_map[digest]
        status = linked.get("identity_link_status")
        if status not in ALL_STATUSES:
            raise ValueError("unrecognized published identity status")
        counts[status] += 1
        if status == STATUS_MATCH:
            continue
        source_ids = source.get("application_numbers")
        if not isinstance(source_ids, list):
            source_ids = []
        if linked.get("source_application_identifiers_as_published") != source_ids:
            raise ValueError("original application identifiers do not reconcile")
        for key in ("letter_type_as_published", "letter_date_as_published"):
            if linked.get(key) != source.get(key):
                raise ValueError("published letter fields do not reconcile")
        candidates = linked.get("canonical_application_candidates")
        if not isinstance(candidates, list):
            raise ValueError("canonical application candidates missing")
        review_items.append({
            "source_record_sha256": digest,
            "source_partition": source.get("source_partition"),
            "source_record_index": source.get("source_record_index"),
            "file_name_as_published": source.get("file_name_as_published"),
            "company_name_as_published": source.get("company_name_as_published"),
            "letter_date_as_published": source.get("letter_date_as_published"),
            "letter_type_as_published": source.get("letter_type_as_published"),
            "application_ids_as_published": source_ids,
            "canonical_application_candidates": candidates,
            "matched_registry_candidates": linked.get("matched_registry_application_candidates"),
            "identity_link_status": status,
            "review_priority": PRIORITY[status],
            "required_reviewer_action": REVIEW_ACTIONS[status],
            "source_document_url": None,
            "independent_reviewer": None,
            "identity_verified": False,
            "review_cycle_verified": False,
            "complete_denominator_verified": False,
            "model_eligible": False,
            "review_status": "AWAITING_INDEPENDENT_SOURCE_REVIEW",
        })
    if linked_digests != set(letter_map):
        raise ValueError("crosswalk failed to cover every published FDA letter")
    review_items.sort(key=lambda item: (
        item["review_priority"],
        item["source_record_index"] if isinstance(item["source_record_index"], int) else -1,
        item["source_record_sha256"],
    ))
    audit = {
        "status": "IDENTITY_REVIEW_QUEUE_NOT_OUTCOME_COHORT",
        "published_letter_records": len(letters),
        "already_identity_linked_records": counts[STATUS_MATCH],
        "review_queue_records": len(review_items),
        "review_reason_counts": {key: counts[key] for key in (
            STATUS_UNRESOLVED, STATUS_AMBIGUOUS, STATUS_NONMATCH
        )},
        "source_export_date": letter_snapshot.get("source_export_date"),
        "independently_verified_review_cycles": 0,
        "complete_application_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "limitations": [
            "Review queue selects unresolved identity and nonmatch records, not all FDA applications",
            "Currently linked records still require independent review-cycle and evidence validation",
            "FDA CRL publication is selective; the queue is not a representative approval denominator",
            "No source PDF links are inferred from unverified filenames",
        ],
    }
    if audit["already_identity_linked_records"] + len(review_items) != len(letters):
        raise ValueError("FDA identity review queue does not reconcile")
    return {"schema_version": 1, "status": audit["status"], "records": review_items}, audit
