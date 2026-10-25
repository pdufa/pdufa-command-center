"""Prioritize *unverified* FDA source-review claims using a pinned source index.

This module cannot verify a PDF, authenticate reviewer identities, adjudicate
an FDA action, certify a complete denominator, or authorize a prediction.
All workflow statuses are unresolved review tasks, even for matching text.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path

from .hop_fda_dual_review_packets import SOURCE_FIELDS
from .hop_fda_reviewer_reconciliation import COMPLETE_FIELDS

INDEX_STATUS = "FDA_PDF_PAGE_WORKSHEET_UNADJUDICATED"
TRIAGE_FIELDS = (
    "review_queue_priority", "triage_status", "source_record_sha256",
    "fda_pdf_sha256", "fda_pdf_url", "provisional_page_link",
    "claimed_first_review_complete", "claimed_second_review_complete",
    "disputed_fields", "review_reason",
)
REVIEW_STATES = (
    "REVIEWER_FINDINGS_CONFLICT",
    "REVIEW_SUBMISSIONS_INCOMPLETE",
    "MATCHING_TEXT_STILL_UNVERIFIED",
)
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def load_source_index(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("Source index must be an object")
    return data


def audit_worksheet_inventory(original: list[dict], index: dict) -> dict:
    """Reconcile counts and hashes against a nonadjudicated published index.

    This is an index/worksheet *structure* check, NOT a byte-wise re-hash of
    original PDF files. The index does not attest to reviewers or outcomes.
    """
    if (not isinstance(index, dict) or index.get("schema_version") != 1
            or index.get("status") != INDEX_STATUS
            or index.get("all_reviewer_fields_initially_blank") is not True
            or index.get("source_record_reconciled") is not True
            or index.get("complete_application_denominator_verified") is not False
            or index.get("prediction_probability") is not None
            or any(type(index.get(k)) is not int or index[k] != 0 for k in (
                "independently_verified_page_ranges",
                "independently_verified_action_dates",
                "independently_verified_review_cycle_outcomes",
                "model_eligible_records",
            ))):
        raise ValueError("Source index cannot attest verified regulatory outcomes")
    counts = index.get("review_priority_counts")
    total = index.get("published_letter_rows")
    groups = index.get("shared_pdf_groups")
    if (not isinstance(counts, dict)
            or not isinstance(original, list)
            or any(type(v) is not int or v < 0 for v in counts.values())
            or type(total) is not int or total <= 0
            or type(groups) is not int or groups <= 0
            or sum(counts.values()) != total
            or len(original) != total
            or type(index.get("candidate_status_counts")) is not dict
            or any(type(v) is not int or v < 0
                   for v in index["candidate_status_counts"].values())
            or sum(index["candidate_status_counts"].values()) != total
            or not isinstance(index.get("source_archive_sha256"), str)
            or not DIGEST.fullmatch(index["source_archive_sha256"])):
        raise ValueError("Unreconciled FDA page worksheet source index")

    source_ids: set[str] = set()
    documents: set[str] = set()
    priorities: Counter[str] = Counter()
    candidate_statuses: Counter[str] = Counter()
    canonical_rows: list[dict[str, str]] = []
    for row in original:
        if not isinstance(row, dict) or any(k not in row for k in SOURCE_FIELDS):
            raise ValueError("Worksheet source fields are missing")
        source_id, pdf_id = row["source_record_sha256"], row["fda_pdf_sha256"]
        if (not isinstance(source_id, str) or not DIGEST.fullmatch(source_id)
                or source_id in source_ids or not isinstance(pdf_id, str)
                or not DIGEST.fullmatch(pdf_id)):
            raise ValueError("Invalid or repeated original FDA source hash")
        source_ids.add(source_id)
        documents.add(pdf_id)
        priorities[str(row["review_priority"])] += 1
        candidate_statuses[row["candidate_status"]] += 1
        canonical_rows.append({k: str(row[k]) for k in SOURCE_FIELDS})

    if (len(documents) != groups
            or dict(priorities) != counts
            or dict(candidate_statuses) != index["candidate_status_counts"]):
        raise ValueError("FDA worksheet does not reconcile to published source index")

    # This is a local reproducibility fingerprint, not an official signature.
    serialized = json.dumps(
        sorted(canonical_rows, key=lambda r: r["source_record_sha256"]),
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return {
        "source_reference_rows": total,
        "shared_pdf_groups": groups,
        "source_archive_sha256_from_index_unverified_here":
            index["source_archive_sha256"],
        "worksheet_source_fingerprint_sha256":
            hashlib.sha256(serialized).hexdigest(),
        "status": "INDEX_COUNTS_RECONCILED_NO_SOURCE_ADJUDICATION",
    }


def build_review_triage(
    original: list[dict],
    first: list[dict],
    second: list[dict],
    comparison: dict,
    source_index: dict,
) -> tuple[list[dict[str, str]], dict]:
    """Create a private-data-minimized human-review queue, never a release."""
    inventory = audit_worksheet_inventory(original, source_index)
    if (not isinstance(comparison, dict)
            or comparison.get("status") !=
            "REVIEW_CLAIMS_COMPARED_NO_INDEPENDENT_ADJUDICATION"
            or comparison.get("source_reference_rows") != len(original)
            or comparison.get("reviewer_identity_authenticated") is not False
            or comparison.get("reviewer_independence_confirmed") is not False
            or comparison.get("independently_verified_review_cycles") != 0
            or comparison.get("complete_application_denominator_verified") is not False
            or comparison.get("model_eligible_records") != 0
            or comparison.get("prediction_probability") is not None
            or comparison.get("approval_rate") is not None):
        raise ValueError("Reviewer comparison is not a quarantined source audit")

    first_by_id = {r["source_record_sha256"]: r for r in first}
    second_by_id = {r["source_record_sha256"]: r for r in second}
    if (len(first_by_id) != len(original) or len(second_by_id) != len(original)):
        raise ValueError("Reviewer/source identities do not reconcile")
    disputes = comparison.get("disagreements_needing_human_resolution")
    if not isinstance(disputes, list):
        raise ValueError("Invalid reviewer discrepancy worklist")
    disputed_by_id = {}
    for dispute in disputes:
        if (not isinstance(dispute, dict)
                or set(dispute) != {"source_record_sha256", "disputed_fields"}
                or dispute["source_record_sha256"] in disputed_by_id
                or not isinstance(dispute["disputed_fields"], list)
                or not dispute["disputed_fields"]):
            raise ValueError("Invalid duplicate or empty source discrepancy")
        disputed_by_id[dispute["source_record_sha256"]] = dispute["disputed_fields"]

    output: list[dict[str, str]] = []
    outcomes: Counter[str] = Counter()
    for row in original:
        identity = row["source_record_sha256"]
        if identity not in first_by_id or identity not in second_by_id:
            raise ValueError("Missing original FDA source review")
        a, b = first_by_id[identity], second_by_id[identity]
        has_a = bool(a["reviewer_id"] and all(a[k].strip() for k in COMPLETE_FIELDS))
        has_b = bool(b["reviewer_id"] and all(b[k].strip() for k in COMPLETE_FIELDS))
        dispute = disputed_by_id.get(identity, [])
        if dispute and not (has_a and has_b):
            raise ValueError("Dispute cannot arise from incomplete reviewer claims")
        state = (
            "REVIEWER_FINDINGS_CONFLICT" if dispute
            else "MATCHING_TEXT_STILL_UNVERIFIED" if has_a and has_b
            else "REVIEW_SUBMISSIONS_INCOMPLETE"
        )
        outcomes[state] += 1
        # Worklist priority: conflicts, incomplete, then matches; preserve source
        # worksheet priority within each queue tier.
        tier = REVIEW_STATES.index(state) + 1
        output.append({
            "review_queue_priority": str(tier),
            "triage_status": state,
            "source_record_sha256": identity,
            "fda_pdf_sha256": row["fda_pdf_sha256"],
            "fda_pdf_url": row["fda_pdf_url"],
            "provisional_page_link": row["provisional_page_link"],
            "claimed_first_review_complete": str(has_a).lower(),
            "claimed_second_review_complete": str(has_b).lower(),
            "disputed_fields": "; ".join(dispute),
            "review_reason": row["review_reason"],
            "_source_priority": int(row["review_priority"]),
        })
    output.sort(key=lambda r: (int(r["review_queue_priority"]),
                               r["_source_priority"], r["source_record_sha256"]))
    for row in output:
        del row["_source_priority"]
    if (len(output) != sum(outcomes.values())
            or outcomes["REVIEWER_FINDINGS_CONFLICT"] != comparison.get(
                "disagreeing_unverified_claims")
            or outcomes["REVIEW_SUBMISSIONS_INCOMPLETE"] != comparison.get(
                "incomplete_or_missing_reviewer_claims")
            or outcomes["MATCHING_TEXT_STILL_UNVERIFIED"] != comparison.get(
                "matching_unverified_claims")):
        raise ValueError("Review queue conflicts with source comparison")
    return output, {
        "status": "UNVERIFIED_REVIEW_QUEUE_ONLY",
        **inventory,
        "queue_status_counts": {k: outcomes[k] for k in REVIEW_STATES},
        "reviewer_identity_authenticated": False,
        "independently_verified_review_cycles": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "human_adjudication_required": True,
    }


def review_triage_csv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TRIAGE_FIELDS,
                            extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if (row.get("triage_status") not in REVIEW_STATES
                or row.get("review_queue_priority") not in {"1", "2", "3"}):
            raise ValueError("Only unverified FDA source-review queue items permitted")
        writer.writerow(row)
    return output.getvalue()
