"""Publication-source FDA action review worklist, without regulatory outcome labels.

Published CRLs, rescissions, tentative approvals, provisional determinations,
and unclassified letters are distinct source document types. A publication
date is NOT an independently verified effective FDA action date.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import re


CROSSWALK_STATUS = "IDENTITY_LINKAGE_ONLY_NOT_A_REVIEW_CYCLE_OUTCOME_COHORT"
CRL_SOURCE_STATUS = "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT"

DOCUMENT_KIND = {
    "COMPLETE RESPONSE": "CRL_SOURCE_ACTION_UNADJUDICATED",
    "RESCIND COMPLETE RESPONSE": "RESCISSION_REQUIRES_PRIOR_ACTION",
    "CORRECTED PROVISIONAL DETERMINATION": "CORRECTION_REQUIRES_ORIGINAL_ACTION",
    "TENTATIVE APPROVAL": "TENTATIVE_APPROVAL_NOT_FINAL_APPROVAL",
    "PROVISIONAL DETERMINATION": "PROVISIONAL_DETERMINATION_NOT_FINAL_APPROVAL",
    "REFUSAL TO FILE": "REFUSAL_TO_FILE_NOT_CR_L_OR_APPROVAL",
    "UNCLASSIFIED": "UNCLASSIFIED_REQUIRES_PRIMARY_DOCUMENT",
}
HIGH_PRIORITY_TYPES = {"RESCIND COMPLETE RESPONSE", "CORRECTED PROVISIONAL DETERMINATION"}


def _letter_date(value: object, as_of: date) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", value):
        raise ValueError("published FDA letter date is missing or invalid")
    try:
        month, day, year = (int(v) for v in value.split("/"))
        parsed = date(year, month, day)
    except ValueError as exc:
        raise ValueError("published FDA letter date is invalid") from exc
    if parsed > as_of:
        raise ValueError("FDA letter publication date is in the future")
    return parsed.isoformat()


def build_fda_action_review_worklist(
    crosswalk: dict, letter_snapshot: dict, as_of: date
) -> tuple[dict, dict]:
    """Reconcile the complete publication-selected archive into an evidence queue.

    The source letter date is not necessarily the original regulatory action date.
    This does not classify application-level review cycles or authorize model
    training, regardless of how convincing the published source may appear.
    """
    if crosswalk.get("status") != CROSSWALK_STATUS or letter_snapshot.get("status") != CRL_SOURCE_STATUS:
        raise ValueError("action review requires quarantined FDA source inventories")
    source = letter_snapshot.get("records")
    links = crosswalk.get("records")
    if not isinstance(source, list) or not isinstance(links, list) or len(source) != len(links):
        raise ValueError("FDA letter and crosswalk counts must reconcile")
    source_by_digest = {}
    for row in source:
        if not isinstance(row, dict) or row.get("model_eligible") is not False:
            raise ValueError("FDA source row must be quarantined")
        digest = row.get("source_record_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("invalid FDA source digest")
        if digest in source_by_digest:
            raise ValueError("duplicate FDA source digest")
        source_by_digest[digest] = row
    linked_digests = set()
    counts = Counter()
    candidate_groups = defaultdict(int)
    staged = []
    for link in links:
        if (not isinstance(link, dict) or link.get("model_eligible") is not False
                or link.get("complete_cohort_verified") is not False
                or link.get("point_in_time_outcome_verified") is not False):
            raise ValueError("crosswalk review evidence cannot be model-eligible")
        digest = link.get("letter_record_sha256")
        if digest not in source_by_digest or digest in linked_digests:
            raise ValueError("unknown or repeated crosswalk evidence digest")
        linked_digests.add(digest)
        source_row = source_by_digest[digest]
        if link.get("source_application_identifiers_as_published") != source_row.get("application_numbers"):
            raise ValueError("published application IDs do not reconcile")
        if (link.get("letter_type_as_published") != source_row.get("letter_type_as_published")
                or link.get("letter_date_as_published") != source_row.get("letter_date_as_published")):
            raise ValueError("letter source date or type does not reconcile")
        link_status = link.get("identity_link_status")
        if link_status not in {
            "APPLICATION_ID_UNRESOLVED", "MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS",
            "NOT_FOUND_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT",
            "PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT",
        }:
            raise ValueError("unexpected FDA identity status")
        letter_type = source_row["letter_type_as_published"]
        if letter_type not in DOCUMENT_KIND:
            raise ValueError("unrecognized official FDA published letter type")
        as_published = source_row.get("application_numbers")
        if not isinstance(as_published, list):
            raise ValueError("application identifiers must be an array")
        candidates = link.get("canonical_application_candidates")
        if not isinstance(candidates, list) or any(
                not isinstance(c, str) or not re.fullmatch(r"(NDA|BLA|ANDA)[0-9]{6}", c)
                for c in candidates):
            raise ValueError("invalid crosswalk canonical applications")
        if len(candidates) == 1:
            candidate_groups[candidates[0]] += 1
        publication_date = _letter_date(source_row.get("letter_date_as_published"), as_of)
        counts[letter_type] += 1
        staged.append({
            "source_record_sha256": digest,
            "source_partition": source_row.get("source_partition"),
            "source_record_index": source_row.get("source_record_index"),
            "company_as_published": source_row.get("company_name_as_published"),
            "file_name_as_published": source_row.get("file_name_as_published"),
            "application_ids_as_published": as_published,
            "canonical_application_candidates": candidates,
            "identity_link_status": link.get("identity_link_status"),
            "letter_type_as_published": letter_type,
            "source_letter_date_as_published": source_row.get("letter_date_as_published"),
            "letter_date_as_published": source_row.get("letter_date_as_published"),
            "normalized_source_letter_date": publication_date,
            "published_document_category": DOCUMENT_KIND[letter_type],
            "prior_action_must_be_checked": letter_type in HIGH_PRIORITY_TYPES,
            "effective_fda_action_date_candidate": None,
            "effective_fda_action_date_independently_verified": False,
            "identity_verified": False,
            "review_cycle_verified": False,
            "original_fda_action_document_verified": False,
            "review_cycle_number_verified": False,
            "fda_review_cycle_outcome": None,
            "public_features_as_of": None,
            "independent_reviewer_one": None,
            "independent_reviewer_two": None,
            "independent_review_complete": False,
            "complete_denominator_verified": False,
            "model_eligible": False,
            "review_status": "AWAITING_SOURCE_EVIDENCE_ADJUDICATION",
        })
    if linked_digests != set(source_by_digest):
        raise ValueError("FDA crosswalk does not cover all published letters")
    repeated_candidates = 0
    for row in staged:
        applications = row["canonical_application_candidates"]
        repeated = len(applications) == 1 and candidate_groups[applications[0]] > 1
        row["same_application_multiple_published_letters"] = repeated
        repeated_candidates += int(repeated)
        letter_type = row["letter_type_as_published"]
        if letter_type in HIGH_PRIORITY_TYPES:
            row["source_review_priority"] = 1
        elif letter_type != "COMPLETE RESPONSE":
            row["source_review_priority"] = 2
        elif row["identity_link_status"] in (
                "APPLICATION_ID_UNRESOLVED", "MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS"):
            row["source_review_priority"] = 3
        elif repeated:
            row["source_review_priority"] = 4
        else:
            row["source_review_priority"] = 5
    staged.sort(key=lambda r: (
        r["source_review_priority"], r["normalized_source_letter_date"],
        r["source_record_sha256"]
    ))
    audit = {
        "status": "PUBLISHED_FDA_ACTION_REVIEW_ONLY_NO_VALIDATED_OUTCOMES",
        "source_export_date": letter_snapshot.get("source_export_date"),
        "published_letter_records": len(staged),
        "published_letter_type_counts": dict(sorted(counts.items())),
        "same_application_repeated_letter_candidates": repeated_candidates,
        "source_actions_requiring_original_or_prior_action": sum(
            counts[x] for x in HIGH_PRIORITY_TYPES
        ),
        "effective_fda_action_dates_independently_verified": 0,
        "independently_adjudicated_review_cycle_outcomes": 0,
        "independently_verified_predecision_features": 0,
        "complete_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "limitations": [
            "A CRL publication is not a representative sample of all FDA applications.",
            "The letter's publication date may differ from its effective FDA action date.",
            "Corrected, rescinded, tentative, provisional, RTF and unclassified actions are not interchangeable labels.",
            "A repeated published letter does not establish a distinct FDA review cycle.",
            "An approved registry match does not prove the historical CRL cycle was approved.",
        ],
    }
    return {"schema_version": 1, "status": audit["status"], "records": staged}, audit
