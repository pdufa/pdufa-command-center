"""Quarantined review queue for FDA letters absent from ORIGINAL NDA/BLA spine.

This compares the *publication-selected* official FDA letter archive to both
the tabular FDA application roster and original-submission entries. No letter
is an adjudicated review cycle or a validated nonapproval. Nothing is model
eligible. Private letter-level worklist stays outside public CI artifacts.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import date
from pathlib import Path

from .hop_drugsfda_submission_spine import _read_tsv, APPLICATION_COLUMNS
from .hop_fda_application_crosswalk import canonical_application_id
from .hop_fda_original_letter_bridge import (
    STATES, crosswalk_original_submissions_to_published_letters,
)

REVIEW_REASONS = (
    "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION",
    "APPLICATION_IN_TABLE_BUT_NO_ORIGINAL_SUBMISSION",
    "APPLICATION_NOT_IN_TABULAR_APPROVAL_CENTRIC_SOURCE",
)
HEX = re.compile(r"[0-9a-f]{64}\Z")
ALLOWED_TYPES = {
    "COMPLETE RESPONSE", "TENTATIVE APPROVAL", "PROVISIONAL DETERMINATION",
    "CORRECTED PROVISIONAL DETERMINATION", "REFUSAL TO FILE",
    "RESCIND COMPLETE RESPONSE", "UNCLASSIFIED",
}


def build_letter_identity_gap_triage(
    original_spine: dict,
    published_letters: dict,
    *,
    applications_tsv: str | Path,
    as_of: date,
) -> tuple[list[dict], dict]:
    """Produce application-identity work, without inferring FDA outcomes."""
    bridge = crosswalk_original_submissions_to_published_letters(
        original_spine, published_letters, as_of=as_of,
    )
    if (not isinstance(original_spine.get("source_application_tsv_sha256"), str)
            or not HEX.fullmatch(original_spine["source_application_tsv_sha256"])
            or original_spine.get("research_cutoff") != as_of.isoformat()
            or published_letters.get("retrieved_on") != as_of.isoformat()):
        raise ValueError("Missing controlled source provenance or research cutoff")
    path = Path(applications_tsv)
    if hashlib.sha256(path.read_bytes()).hexdigest() != original_spine[
        "source_application_tsv_sha256"
    ]:
        raise ValueError("FDA application roster differs from original-submission audit")
    application_rows, _ = _read_tsv(path, APPLICATION_COLUMNS)
    if len(application_rows) != original_spine.get("application_rows_in_extract"):
        raise ValueError("FDA application table changed since source audit")
    all_apps: set[str] = set()
    bad_apps = 0
    for row in application_rows:
        number, typ = row["ApplNo"].strip(), row["ApplType"].strip().upper()
        if not re.fullmatch(r"[0-9]{6}", number) or number == "000000":
            bad_apps += 1
            continue
        if not re.fullmatch(r"[A-Z]{2,8}", typ):
            bad_apps += 1
            continue
        app = typ + number
        if app in all_apps:
            raise ValueError("Duplicate FDA application identity in tabular roster")
        all_apps.add(app)
    if (len(all_apps) != original_spine.get("validated_application_identity_rows")
            or sum(original_spine.get("quarantined_application_row_reason_counts", {}).values())
               != bad_apps):
        raise ValueError("FDA application roster quarantine counts disagree")

    original_apps = {
        x["application_id"] for x in original_spine["candidate_original_submissions"]
    }
    if len(original_apps) != original_spine.get(
        "distinct_nda_bla_applications_in_original_submission_inventory"
    ):
        raise ValueError("Incomplete original-submission source census")

    raw_letters = published_letters["records"]
    recognized = Counter()
    app_freq = Counter()
    for letter in raw_letters:
        ids = letter.get("application_numbers")
        if not isinstance(ids, list):
            raise ValueError("Missing original FDA published application IDs")
        candidates = [canonical_application_id(id_) for id_ in ids]
        valid = sorted({v for v in candidates if v is not None})
        ambiguous = not ids or any(v is None for v in candidates) or len(valid) != 1
        if ambiguous:
            reason, app = REVIEW_REASONS[0], None
        else:
            app = valid[0]
            if app.startswith("ANDA"):
                recognized["ANDA_OUT_OF_SCOPE"] += 1
                continue
            if app in original_apps:
                recognized["MATCHED_ORIGINAL_APPLICATION"] += 1
                continue
            if app in all_apps:
                reason = REVIEW_REASONS[1]
            else:
                reason = REVIEW_REASONS[2]
            app_freq[app] += 1
        recognized[reason] += 1

    queue = []
    seen_source_ids = set()
    for letter in raw_letters:
        ids = letter["application_numbers"]
        candidates = [canonical_application_id(id_) for id_ in ids]
        valid = sorted({v for v in candidates if v is not None})
        ambiguous = not ids or any(v is None for v in candidates) or len(valid) != 1
        if ambiguous:
            reason, app = REVIEW_REASONS[0], None
        else:
            app = valid[0]
            if app.startswith("ANDA") or app in original_apps:
                continue
            reason = REVIEW_REASONS[1] if app in all_apps else REVIEW_REASONS[2]
        digest = letter.get("source_record_sha256")
        if not isinstance(digest, str) or not HEX.fullmatch(digest) or digest in seen_source_ids:
            raise ValueError("FDA source digest invalid or duplicated")
        seen_source_ids.add(digest)
        if (letter.get("model_eligible") is not False
                or letter.get("independently_verified") is not False
                or letter.get("review_cycle") is not None
                or letter.get("cohort_complete_verified") is not False):
            raise ValueError("Published FDA letter promoted to clinical decision")
        published_type = letter.get("letter_type_as_published")
        if published_type not in ALLOWED_TYPES:
            raise ValueError("Unknown letter publication type requires manual schema review")
        queue.append({
            "source_record_sha256": digest,
            "application_candidate": app,
            "review_reason": reason,
            "review_priority": str(REVIEW_REASONS.index(reason) + 1),
            "published_letter_type": published_type,
            "repeated_published_letter_references_for_candidate": app_freq[app] if app else None,
            "review_task": (
                "IDENTIFY_ORIGINAL_FDA_APPLICATION_AND_ACTION_DOCUMENT"
                if app is None else
                "CHECK_ORIGINAL_SUBMISSION_HISTORY_AND_INDEPENDENT_FDA_ACTIONS"
            ),
            "original_application_review_cycle": None,
            "fda_action_outcome": None,
            "evidence_independently_adjudicated": False,
            "model_eligible": False,
        })
    queue.sort(key=lambda row: (
        int(row["review_priority"]),
        -(row["repeated_published_letter_references_for_candidate"] or 0),
        row["source_record_sha256"],
    ))
    breakdown = Counter(row["review_reason"] for row in queue)
    if (len(queue) != sum(breakdown.values())
            or len(queue) != (
                bridge["published_letter_reference_link_states"][STATES[1]]
                + bridge["published_letter_reference_link_states"][STATES[3]]
            )
            or sum(recognized.values()) != len(raw_letters)
            or recognized["MATCHED_ORIGINAL_APPLICATION"] !=
               bridge["published_letter_reference_link_states"][STATES[0]]
            or recognized["ANDA_OUT_OF_SCOPE"] !=
               bridge["published_letter_reference_link_states"][STATES[2]]
            or recognized[REVIEW_REASONS[0]] !=
               bridge["published_letter_reference_link_states"][STATES[3]]
            or recognized[REVIEW_REASONS[1]] + recognized[REVIEW_REASONS[2]]
               != bridge["published_letter_reference_link_states"][STATES[1]]):
        raise ValueError("FDA letter-level gap queue does not reconcile to pinned bridge")
    return queue, {
        "status": "PUBLISHED_FDA_LETTER_IDENTITY_GAPS_UNVERIFIED",
        "research_cutoff": as_of.isoformat(),
        "published_letter_references": len(raw_letters),
        "matched_original_application_letter_references":
            recognized["MATCHED_ORIGINAL_APPLICATION"],
        "nda_bla_no_original_spine_letter_references":
            recognized[REVIEW_REASONS[1]] + recognized[REVIEW_REASONS[2]],
        "ambiguous_or_unparseable_letter_references": recognized[REVIEW_REASONS[0]],
        "anda_out_of_scope_letter_references": recognized["ANDA_OUT_OF_SCOPE"],
        "review_queue_references": len(queue),
        "review_queue_reasons": {key: breakdown[key] for key in REVIEW_REASONS},
        "distinct_candidate_applications_needing_source_research": len(app_freq),
        "candidate_applications_with_repeated_published_letters":
            sum(n > 1 for n in app_freq.values()),
        "maximum_published_letter_references_for_one_missing_application":
            max(app_freq.values(), default=0),
        "source_applications_tsv_sha256":
            original_spine["source_application_tsv_sha256"],
        "source_submissions_tsv_sha256":
            original_spine["source_submission_tsv_sha256"],
        "published_letter_export_date": published_letters["source_export_date"],
        "fda_original_actions_independently_verified": 0,
        "complete_original_nda_bla_decision_denominator_verified": False,
        "nonmatch_does_not_prove_never_approved": True,
        "publication_selected_letters_not_complete_outcome_population": True,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "predictive_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
    }
