"""Application-identifier crosswalk between published FDA letters and approved products.

Joining by application identity is NOT outcome ascertainment. In particular a
later approval is not evidence the earlier CRL review cycle was approved.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import re


def canonical_application_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"\s*(NDA|ANDA|BLA)[\s#:\-]*([0-9]{1,6})\s*", value.upper())
    if match is None:
        return None
    return match.group(1).upper() + match.group(2).zfill(6)


def crosswalk_public_fda_sources(crl_snapshot: dict, drugsfda_snapshot: dict) -> tuple[dict, dict]:
    """Build publication-selected, read-only application links with abstention."""
    if (crl_snapshot.get("status") != "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT"
            or drugsfda_snapshot.get("status") != "APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT"):
        raise ValueError("source snapshots must remain quarantined")
    letters = crl_snapshot.get("records")
    registry = drugsfda_snapshot.get("records")
    if not isinstance(letters, list) or not isinstance(registry, list):
        raise ValueError("source records missing")
    index = defaultdict(list)
    for row in registry:
        if not isinstance(row, dict) or row.get("model_eligible") is not False:
            raise ValueError("registry cannot promote model-eligible records")
        canonical = canonical_application_id(row.get("application_number_as_published"))
        if canonical is not None:
            index[canonical].append(row["record_sha256"])
    statuses = Counter()
    qualified_letter_count = 0
    legacy_bl_unresolved_count = 0
    missing_identifier_count = 0
    results = []
    for row in letters:
        if not isinstance(row, dict) or row.get("model_eligible") is not False:
            raise ValueError("letter cannot promote model-eligible records")
        source_ids = row.get("application_numbers")
        if not isinstance(source_ids, list):
            source_ids = []
        parsed_ids = [canonical_application_id(value) for value in source_ids]
        canonical_ids = sorted(set(value for value in parsed_ids if value is not None))
        unresolved_source_ids = [value for value, normalized in zip(source_ids, parsed_ids)
                                 if normalized is None]
        qualified_references = [value for value in source_ids
                                if isinstance(value, str) and "/" in value]
        if qualified_references:
            qualified_letter_count += 1
        if not source_ids:
            missing_identifier_count += 1
        if not canonical_ids and any(isinstance(value, str) and value.upper().startswith("BL ")
                                     for value in source_ids):
            legacy_bl_unresolved_count += 1
        matched_ids = [x for x in canonical_ids if x in index]
        if not canonical_ids:
            status = "APPLICATION_ID_UNRESOLVED"
        elif len(canonical_ids) != 1 or unresolved_source_ids or len(matched_ids) > 1 or (
                matched_ids and len(index[matched_ids[0]]) != 1):
            status = "MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS"
        elif matched_ids:
            status = "PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT"
        else:
            status = "NOT_FOUND_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT"
        statuses[status] += 1
        results.append({
            "letter_record_sha256": row.get("source_record_sha256"),
            "letter_type_as_published": row.get("letter_type_as_published"),
            "letter_date_as_published": row.get("letter_date_as_published"),
            "source_application_identifiers_as_published": source_ids,
            "qualified_source_references_as_published": qualified_references,
            "unresolved_source_identifiers_as_published": unresolved_source_ids,
            "canonical_application_candidates": canonical_ids,
            "matched_registry_application_candidates": matched_ids,
            "identity_link_status": status,
            "registry_presence_is_not_review_cycle_approval": True,
            "complete_cohort_verified": False,
            "point_in_time_outcome_verified": False,
            "model_eligible": False,
        })
    audit = {
        "status": "IDENTITY_LINKAGE_ONLY_NOT_A_REVIEW_CYCLE_OUTCOME_COHORT",
        "crl_source_export_date": crl_snapshot.get("source_export_date"),
        "approved_registry_source_export_date": drugsfda_snapshot.get("source_export_date"),
        "published_letter_records": len(letters),
        "approved_registry_source_application_records": len(registry),
        "identity_link_status_counts": dict(sorted(statuses.items())),
        "qualified_reference_letter_records": qualified_letter_count,
        "unresolved_legacy_bl_letter_records": legacy_bl_unresolved_count,
        "letters_without_application_identifiers": missing_identifier_count,
        "complete_application_denominator_verified": False,
        "verified_review_cycle_outcomes": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "limitations": [
            "Matching an application to a currently approved product does not prove approval at the letter date",
            "A missing registry link does not establish that an application was never approved",
            "Distinct published letters do not necessarily represent distinct review cycles",
            "Stripping an Original or S-number suffix recovers application identity only; submission numbers remain unverified",
            "Legacy BL identifiers remain unresolved unless an independently sourced official type crosswalk exists",
            "FDA published CRLs are selectively disclosed and do not define an unbiased denominator",
        ],
    }
    return {"schema_version": 1, "status": audit["status"], "records": results}, audit
