"""Join two official FDA source families by *application identity only*.

This compares Drugs@FDA original NDA/BLA submission-history references with
selectively published openFDA response letters. It never establishes distinct
FDA review cycles, a complete decision denominator, or an FDA approval rate.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date

from .hop_fda_application_crosswalk import canonical_application_id

STATES = (
    "NDA_BLA_APPLICATION_IN_ORIGINAL_SUBMISSION_SPINE",
    "NDA_BLA_APPLICATION_NOT_IN_ORIGINAL_SUBMISSION_SPINE",
    "ANDA_OUT_OF_STUDY_SCOPE",
    "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION",
)
ORIG_QUALIFIER = re.compile(
    r"\s*(?:NDA|BLA)[\s#:\-]*[0-9]{1,6}/Original[ ]+([1-9][0-9]*)\s*\Z",
    re.IGNORECASE,
)


def crosswalk_original_submissions_to_published_letters(
    original_spine: dict, crl_snapshot: dict, *, as_of: date,
) -> dict:
    if not isinstance(as_of, date):
        raise ValueError("Explicit controlled source comparison date required")
    if (not isinstance(original_spine, dict)
            or original_spine.get("status") !=
            "DRUGSFDA_ORIGINAL_SUBMISSION_SPINE_RESEARCH_ONLY"
            or original_spine.get("model_eligible_records") != 0
            or original_spine.get("prediction_probability") is not None
            or original_spine.get("complete_original_nda_bla_application_denominator_verified")
               is not False
            or original_spine.get("independently_verified_fda_review_cycles") != 0
            or original_spine.get("submission_number_is_not_review_cycle") is not True
            or original_spine.get("raw_status_not_a_verified_decision_label") is not True
            or not isinstance(original_spine.get("candidate_original_submissions"), list)):
        raise ValueError("Drugs@FDA original-submission cohort source is not quarantined")
    if (not isinstance(crl_snapshot, dict)
            or crl_snapshot.get("status") !=
            "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT"
            or not isinstance(crl_snapshot.get("records"), list)):
        raise ValueError("Published FDA letters have not remained quarantined")
    if crl_snapshot.get("source_export_date") is None:
        raise ValueError("FDA CRL published export date is required")
    try:
        export = date.fromisoformat(crl_snapshot["source_export_date"])
    except (ValueError, TypeError):
        raise ValueError("FDA CRL source export date invalid") from None
    if export > as_of:
        raise ValueError("FDA CRL export postdates research cutoff")

    original_entries = original_spine["candidate_original_submissions"]
    if len(original_entries) != original_spine.get("original_nda_bla_submission_rows"):
        raise ValueError("FDA original submission inventory row counts are inconsistent")
    by_app = defaultdict(set)
    for item in original_entries:
        if (not isinstance(item, dict)
                or item.get("independently_verified") is not False
                or item.get("model_eligible") is not False
                or item.get("review_cycle") is not None
                or item.get("fda_action_outcome") is not None
                or item.get("submission_kind") != "ORIG"):
            raise ValueError("Original submission record falsely claims FDA action")
        app = item.get("application_id")
        if (not isinstance(app, str)
                or not re.fullmatch(r"(?:NDA|BLA)[0-9]{6}", app)
                or item.get("application_type") != app[:3]
                or type(item.get("original_submission_number")) is not int
                or item["original_submission_number"] < 1):
            raise ValueError("Original NDA/BLA source identity is invalid")
        number = item["original_submission_number"]
        if number in by_app[app]:
            raise ValueError("Duplicate original submission for same application and number")
        by_app[app].add(number)
    if len(by_app) != original_spine.get(
        "distinct_nda_bla_applications_in_original_submission_inventory"
    ):
        raise ValueError("Distinct original-source application count is inconsistent")

    letter_states = Counter()
    letter_types = Counter()
    qualifiers = Counter()
    matched_per_app = Counter()
    source_ids_seen = set()
    matches_with_multiple_submissions = 0
    for letter in crl_snapshot["records"]:
        if not isinstance(letter, dict):
            raise ValueError("Malformed published letter row")
        if (letter.get("model_eligible") is not False
                or letter.get("independently_verified") is not False
                or letter.get("cohort_complete_verified") is not False
                or letter.get("review_cycle") is not None):
            raise ValueError("Unadjudicated published letter was promoted")
        sid = letter.get("source_record_sha256")
        if (not isinstance(sid, str) or not re.fullmatch(r"[0-9a-f]{64}", sid)
                or sid in source_ids_seen):
            raise ValueError("Duplicate or invalid published FDA source digest")
        source_ids_seen.add(sid)
        raw = letter.get("application_numbers")
        if not isinstance(raw, list):
            raise ValueError("Published FDA application identity list missing")
        resolved = [canonical_application_id(value) for value in raw]
        unique = set(value for value in resolved if value is not None)
        unresolved = len(raw) != len(resolved) or any(v is None for v in resolved)
        if len(unique) != 1 or unresolved:
            state = "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION"
        else:
            application = next(iter(unique))
            if application.startswith("ANDA"):
                state = "ANDA_OUT_OF_STUDY_SCOPE"
            elif application in by_app:
                state = "NDA_BLA_APPLICATION_IN_ORIGINAL_SUBMISSION_SPINE"
                matched_per_app[application] += 1
                if len(by_app[application]) > 1:
                    matches_with_multiple_submissions += 1
                original_numbers = set()
                for source_id in raw:
                    found = ORIG_QUALIFIER.fullmatch(source_id)
                    if found:
                        original_numbers.add(int(found.group(1)))
                if original_numbers:
                    if original_numbers.issubset(by_app[application]):
                        qualifiers["ORIGINAL_QUALIFIER_MATCHES_SUBMISSION_NUMBER_TEXT_ONLY"] += 1
                    else:
                        qualifiers["ORIGINAL_QUALIFIER_NOT_IN_SPINE_REQUIRES_REVIEW"] += 1
            else:
                state = "NDA_BLA_APPLICATION_NOT_IN_ORIGINAL_SUBMISSION_SPINE"
        letter_states[state] += 1
        letter_type = letter.get("letter_type_as_published")
        letter_types[letter_type if isinstance(letter_type, str) and letter_type
                     else "UNCLASSIFIED"] += 1

    n = len(crl_snapshot["records"])
    if not n or sum(letter_states.values()) != n:
        raise ValueError("FDA published-letter references were not reconciled")
    matched = letter_states["NDA_BLA_APPLICATION_IN_ORIGINAL_SUBMISSION_SPINE"]
    repeated_apps = sum(v > 1 for v in matched_per_app.values())
    unique_matched = len(matched_per_app)
    if not (0 <= unique_matched <= matched <= n
            and matches_with_multiple_submissions <= matched):
        raise ValueError("Impossible source-linkage population")
    return {
        "status": "NDA_BLA_ORIGINAL_SUBMISSION_LETTER_IDENTITY_CROSSWALK_ONLY",
        "comparison_cutoff": as_of.isoformat(),
        "drugsfda_source_applications_sha256":
            original_spine.get("source_application_tsv_sha256"),
        "drugsfda_source_submissions_sha256":
            original_spine.get("source_submission_tsv_sha256"),
        "fda_published_letter_export_date": crl_snapshot["source_export_date"],
        "published_letter_references": n,
        "original_nda_bla_submission_history_rows": len(original_entries),
        "distinct_nda_bla_applications_in_approval_centric_spine": len(by_app),
        "published_letter_reference_link_states": {
            key: letter_states[key] for key in STATES
        },
        "published_letter_type_counts": dict(sorted(letter_types.items())),
        "distinct_original_spine_applications_referenced_by_published_letters":
            unique_matched,
        "matched_original_spine_applications_with_repeated_letter_references":
            repeated_apps,
        "matched_letter_references_with_multiple_original_submission_numbers":
            matches_with_multiple_submissions,
        "textual_original_qualifier_comparison_counts":
            dict(sorted(qualifiers.items())),
        "published_crl_corpus_selectively_released": True,
        "original_drugsfda_source_approval_centric": True,
        "unmatched_record_does_not_prove_never_approved": True,
        "application_link_does_not_establish_same_review_cycle": True,
        "independently_verified_fda_review_cycles": 0,
        "complete_nda_bla_decision_denominator_verified": False,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "prediction_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
    }
