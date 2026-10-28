"""Read-only adapter for actual workspace candidate records.

No summary-count synthesis. Only explicitly identified GEM JR, GEM, WT rows
are admitted. Ambiguous membership or absent Phase 3 evidence remains unknown.
"""
from collections.abc import Mapping
from typing import Any
from scripts.build_priority_prediction_queue import build_initial_queue

STAGE_NAMES = {"GEM_JR": "GEM JR", "GEM": "GEM", "WT": "WT"}


def workspace_to_priority_queue(payload: Mapping[str, Any]) -> dict:
    """Accept explicit list arrays from a workspace export; fail closed otherwise.

    Expected input: {"lists": {"GEM_JR": [...], "GEM": [...], "WT": [...]}}.
    Each row needs program_id or id. Never infer list membership from score.
    """
    lists = payload.get("lists")
    # Actual Next.js /api/workspace response stores list members in
    # members.GEM_JR.rows and members.GEM.rows; WT is a separate saved tag set.
    if not isinstance(lists, Mapping):
        members = payload.get("members")
        if isinstance(members, Mapping):
            lists = {}
            for stage in ("GEM_JR", "GEM"):
                member = members.get(stage)
                if isinstance(member, Mapping) and isinstance(member.get("rows"), list):
                    lists[stage] = member["rows"]
    if not isinstance(lists, Mapping):
        return {"status": "SOURCE_SCHEMA_UNVERIFIED", "reason": "Missing explicit lists or members mapping",
                "queue": [], "trading_ready": False}
    # WT is a separate saved watch/trade collection; match exact identities.
    wt = payload.get("program_watch_trade")
    if isinstance(wt, Mapping):
        identities = wt.get("identities")
        watch, trade = wt.get("watch"), wt.get("trade")
        if isinstance(identities, list) and isinstance(watch, list) and isinstance(trade, list):
            identity_map = {x["id"]: x["programId"] for x in identities
                            if isinstance(x, Mapping) and isinstance(x.get("id"), str)
                            and isinstance(x.get("programId"), str)}
            records = {}
            for stage in ("GEM_JR", "GEM"):
                for row in lists.get(stage, []):
                    if isinstance(row, Mapping):
                        program = row.get("programId") or row.get("program_id")
                        if isinstance(program, str):
                            records[program] = row
            selected = {identity_map[x] for x in watch + trade
                        if isinstance(x, str) and x in identity_map}
            lists = {**lists, "WT": [records[p] for p in sorted(selected) if p in records]}
    rows = []
    missing_groups = []
    for stage, label in STAGE_NAMES.items():
        members = lists.get(stage)
        if not isinstance(members, list):
            missing_groups.append(stage)
            continue
        for item in members:
            if not isinstance(item, Mapping):
                continue
            key = item.get("program_id") or item.get("programId") or item.get("id")
            if not isinstance(key, str) or not key.strip():
                continue
            # phase3Status is a development-stage label, not proof that
            # results have been publicly released. Accept only a separately
            # attested evidence status with a source citation.
            evidence = str(item.get("phase3_evidence_status") or "").strip().lower()
            evidence_url = item.get("phase3_evidence_url")
            verified = (evidence in {"phase3_results_released", "phase3_results_published"}
                        and isinstance(evidence_url, str)
                        and evidence_url.startswith(("https://", "http://")))
            normalized = {**item, "program_id": key.strip(), "list_name": label}
            if not verified:
                normalized["phase3_evidence_status"] = "source_verification_required"
            rows.append(normalized)
    result = build_initial_queue(rows)
    result["source_groups_missing"] = missing_groups
    result["status"] = "SOURCE_PARTIAL" if missing_groups else "CLASSIFICATION_QUEUE_BUILT"
    result["source_records_accepted"] = len(rows)
    result["source_verification_required"] = True
    return result
