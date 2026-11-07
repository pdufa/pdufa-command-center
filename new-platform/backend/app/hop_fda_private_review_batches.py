"""Prioritize blank FDA source-review work in bounded, privately paired batches.

Both source streams stay independent, source-locked, and unadjudicated.
This module neither authenticates human reviewers nor labels FDA decisions.
"""
from __future__ import annotations

import copy
import json
import re
from collections import Counter, defaultdict

from .hop_fda_identity_gap_dual_review import (
    CLAIM_FIELDS, LOCKED, REVIEW_STATUS, ROLE, SOURCE_STATUS, _lock,
)

SHA = re.compile(r"[a-f0-9]{64}\Z")
AMBIGUOUS = "AMBIGUOUS_APPLICATION_ID_RESEARCH"
APPLICATION = "APPLICATION_IDENTITY_RESEARCH"
KINDS = (AMBIGUOUS, APPLICATION)
REVIEW_BLOCK = {
    AMBIGUOUS: "AMBIGUOUS_ID",
    APPLICATION: "APPLICATION_ID",
}


def prepare_private_review_batches(
    first: list[dict], second: list[dict], *, max_references: int = 20,
    expected_references: int | None = None,
    expected_groups: int | None = None,
) -> tuple[list[dict], dict]:
    """Construct A/B source-only review batches without splitting an application.

    Return private paired full-source batch objects and one public-safe
    numerical summary. No reviewer tokens, source fingerprints, URLs, or
    individual application IDs are emitted into that summary.
    """
    if (type(max_references) is not int or not 1 <= max_references <= 25
            or not isinstance(first, list) or not isinstance(second, list)
            or not first or len(first) != len(second)):
        raise ValueError("Invalid FDA source review input or bounded batch limit")

    def index(rows: list[dict], role: str) -> dict[str, dict]:
        result = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Malformed FDA reviewer source row")
            sid = row.get("published_letter_source_sha256")
            if (not isinstance(sid, str) or not SHA.fullmatch(sid)
                    or sid in result or row.get("packet_role") != role
                    or row.get("review_packet_status") != REVIEW_STATUS
                    or row.get("reviewer_token") != ""
                    or row.get("reviewer_authentication_verified") is not False
                    or row.get("independent_regulatory_adjudication_verified") is not False
                    or row.get("model_eligible") is not False
                    or any(row.get(k) != "" for k in CLAIM_FIELDS)
                    or not all(key in row for key in LOCKED)
                    or row.get("source_lock_sha256") != _lock(row)
                    or row.get("packet_kind") not in KINDS
                    or not isinstance(row.get("packet_id"), str)
                    or not row["packet_id"]
                    or row.get("historical_pdf_not_revalidated_now") is not True
                    or row.get("prior_pdf_source_status") not in SOURCE_STATUS):
                raise ValueError("FDA review row not blank, source-locked, or quarantined")
            if row["packet_kind"] == AMBIGUOUS:
                if (row.get("application_id_candidate") is not None
                        or row["packet_id"] != "LETTER_" + sid):
                    raise ValueError("Unresolved FDA application identity was promoted")
            elif row.get("application_id_candidate") != row["packet_id"]:
                raise ValueError("Application packet identity mismatch")
            if row["prior_pdf_source_status"] == SOURCE_STATUS[1]:
                if (row.get("historical_fda_pdf_url") is not None
                        or row.get("historical_fda_pdf_sha256") is not None):
                    raise ValueError("Missing source cannot contain published PDF claim")
            else:
                if (not isinstance(row.get("historical_fda_pdf_sha256"), str)
                        or not SHA.fullmatch(row["historical_fda_pdf_sha256"])):
                    raise ValueError("Existing PDF lead missing source fingerprint")
            result[sid] = row
        return result

    left = index(first, ROLE[0])
    right = index(second, ROLE[1])
    if left.keys() != right.keys():
        raise ValueError("FDA A/B paired source set incomplete")
    for sid in left:
        a = {k: v for k, v in left[sid].items() if k != "packet_role"}
        b = {k: v for k, v in right[sid].items() if k != "packet_role"}
        if a != b:
            raise ValueError("FDA A/B source identity or evidence differs")

    grouped: dict[str, list[str]] = defaultdict(list)
    packet_kinds: dict[str, str] = {}
    for sid, row in left.items():
        pid = row["packet_id"]
        kind = row["packet_kind"]
        if pid in packet_kinds and packet_kinds[pid] != kind:
            raise ValueError("FDA packet switches research identity class")
        packet_kinds[pid] = kind
        grouped[pid].append(sid)
    if (expected_references is not None and len(left) != expected_references
            or expected_groups is not None and len(grouped) != expected_groups):
        raise ValueError("FDA research batch disagrees with pinned private source count")

    batches = []
    counters = Counter()
    for kind in KINDS:
        relevant = sorted(pid for pid in grouped if packet_kinds[pid] == kind)
        active_ids = []
        active_refs = 0
        seq = 0

        def flush():
            nonlocal active_ids, active_refs, seq
            if not active_ids:
                return
            seq += 1
            batch_id = f"{REVIEW_BLOCK[kind]}-{seq:02d}"
            sources = sorted(sid for pid in active_ids for sid in grouped[pid])
            batches.append({
                "batch_id": batch_id,
                "review_category": REVIEW_BLOCK[kind],
                "first_blank_reviewer_sources": [copy.deepcopy(left[s]) for s in sources],
                "second_blank_reviewer_sources": [copy.deepcopy(right[s]) for s in sources],
                "research_groups": len(active_ids),
                "source_references": len(sources),
                "reviewer_identity_authenticated": False,
                "independently_adjudicated_fda_actions": 0,
                "model_eligible_records": 0,
                "prediction_probability": None,
            })
            counters[REVIEW_BLOCK[kind] + "_batches"] += 1
            counters[REVIEW_BLOCK[kind] + "_source_references"] += len(sources)
            counters[REVIEW_BLOCK[kind] + "_groups"] += len(active_ids)
            active_ids = []
            active_refs = 0

        for pid in relevant:
            size = len(grouped[pid])
            if size > max_references:
                raise ValueError("A single FDA application packet exceeds review batch limit")
            if active_ids and active_refs + size > max_references:
                flush()
            active_ids.append(pid)
            active_refs += size
        flush()

    if (sum(b["source_references"] for b in batches) != len(left)
            or sum(b["research_groups"] for b in batches) != len(grouped)
            or any(b["source_references"] > max_references for b in batches)):
        raise ValueError("FDA private review batch references lost or duplicated")
    counts = [{
        "batch": batch["batch_id"],
        "category": batch["review_category"],
        "reference_count": batch["source_references"],
        "research_group_count": batch["research_groups"],
        "reviewer_pairs_completed": 0,
        "verified_original_review_cycles": 0,
    } for batch in batches]
    return batches, {
        "status": "UNREVIEWED_FDA_SOURCE_BATCHES_PREPARED_ONLY",
        "published_letter_references": len(left),
        "application_research_groups": len(grouped),
        "batch_size_limit": max_references,
        "total_batches": len(batches),
        "category_counts": dict(sorted(counters.items())),
        "per_batch_aggregate_counts": counts,
        "reviewer_identities_authenticated": False,
        "independently_completed_reviewer_pairs": 0,
        "original_fda_review_cycles_verified": 0,
        "complete_nda_bla_decision_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "individual_source_records_not_exported": True,
    }
