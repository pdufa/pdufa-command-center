"""Triage repeated letters, not FDA review cycles, in the published CRL corpus.

The openFDA archive is publication-selected. This module groups *candidate*
application identities and dated letters for further evidence review, without
asserting that two letters imply two distinct review cycles or outcome labels.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import re


LINKABLE = {
    "PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT",
    "NOT_FOUND_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT",
}


def _dated_letter(raw: object, as_of: date) -> str | None:
    if not isinstance(raw, str) or not re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", raw):
        return None
    try:
        month, day, year = map(int, raw.split("/"))
        parsed = date(year, month, day)
    except ValueError:
        return None
    if parsed > as_of:
        return None
    return parsed.isoformat()


def triage_published_letter_cycles(crosswalk: dict, as_of: date) -> tuple[dict, dict]:
    if crosswalk.get("status") != "IDENTITY_LINKAGE_ONLY_NOT_A_REVIEW_CYCLE_OUTCOME_COHORT":
        raise ValueError("source must be a quarantined identity-only crosswalk")
    rows = crosswalk.get("records")
    if not isinstance(rows, list):
        raise ValueError("source records must be a list")
    grouped = defaultdict(list)
    exclusions = Counter()
    seen = set()
    for position, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("model_eligible") is not False:
            raise ValueError("cannot triage model-eligible or malformed letters")
        if row.get("complete_cohort_verified") is not False or row.get("point_in_time_outcome_verified") is not False:
            raise ValueError("cannot promote published letters to adjudicated outcomes")
        digest = row.get("letter_record_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("source letter digest is missing or invalid")
        if digest in seen:
            raise ValueError("duplicate source record digest in crosswalk")
        seen.add(digest)
        candidates = row.get("canonical_application_candidates")
        status = row.get("identity_link_status")
        if not isinstance(candidates, list) or len(candidates) != 1 or status not in LINKABLE:
            exclusions["unresolved_or_ambiguous_identity"] += 1
            continue
        app_id = candidates[0]
        if not isinstance(app_id, str) or not re.fullmatch(r"(NDA|BLA|ANDA)[0-9]{6}", app_id):
            exclusions["invalid_application_identity"] += 1
            continue
        letter_date = _dated_letter(row.get("letter_date_as_published"), as_of)
        if letter_date is None:
            exclusions["missing_invalid_or_future_date"] += 1
            continue
        letter_type = row.get("letter_type_as_published")
        if not isinstance(letter_type, str) or not letter_type.strip():
            exclusions["missing_letter_type"] += 1
            continue
        grouped[app_id].append({
            "source_record_sha256": digest,
            "letter_date": letter_date,
            "letter_type_as_published": letter_type,
            "qualified_source_references_as_published":
                row.get("qualified_source_references_as_published", []),
            "potential_same_day_type_duplicate": False,
            "review_cycle_verified": False,
            "model_eligible": False,
        })
    repeated = []
    single = 0
    same_day_type_groups = 0
    letter_records_in_repeats = 0
    for application, events in sorted(grouped.items()):
        if len(events) == 1:
            single += 1
            continue
        counts = Counter((x["letter_date"], x["letter_type_as_published"]) for x in events)
        repeated_keys = {k for k, count in counts.items() if count > 1}
        same_day_type_groups += len(repeated_keys)
        for event in events:
            event["potential_same_day_type_duplicate"] = (
                event["letter_date"], event["letter_type_as_published"]
            ) in repeated_keys
        letter_records_in_repeats += len(events)
        repeated.append({
            "canonical_application_id": application,
            "published_letter_records": len(events),
            "distinct_letter_dates": len({x["letter_date"] for x in events}),
            "potential_same_day_type_duplicate_groups": len(repeated_keys),
            "letters": sorted(events, key=lambda r: (r["letter_date"], r["letter_type_as_published"], r["source_record_sha256"])),
            "independently_verified_review_cycles": 0,
            "model_eligible": False,
            "status": "REPEATED_LETTER_SOURCE_ONLY_REQUIRES_REVIEW",
        })
    audit = {
        "status": "REVIEW_CYCLE_TRIAGE_ONLY_NO_INDEPENDENT_OUTCOME_LABELS",
        "published_letter_records": len(rows),
        "single_letter_application_groups": single,
        "repeated_letter_application_groups": len(repeated),
        "letter_records_in_repeated_groups": letter_records_in_repeats,
        "potential_same_day_type_duplicate_groups": same_day_type_groups,
        "excluded_letter_records": dict(sorted(exclusions.items())),
        "grouped_letter_records": single + letter_records_in_repeats,
        "independently_verified_review_cycles": 0,
        "complete_application_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "limitations": [
            "Repeated published letters are not necessarily repeated review cycles",
            "Same-date same-type letters may reflect separate FDA actions or duplicate releases",
            "Missing or ambiguous application identities are excluded from group analysis, not assigned outcomes",
            "Publication-selected FDA CRLs cannot supply the complete application denominator",
        ],
    }
    if audit["grouped_letter_records"] + sum(exclusions.values()) != len(rows):
        raise ValueError("source triage counts do not reconcile")
    return {"schema_version": 1, "status": audit["status"], "applications_for_review": repeated}, audit
