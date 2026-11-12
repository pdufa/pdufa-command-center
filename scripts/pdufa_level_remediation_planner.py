#!/usr/bin/env python3
"""PDUFA Level 4-20 fail-closed SERIAL engineering remediation planner.

This module does not alter the worker or scientific review, manufacture a
prediction, generate/execute unreviewed code, or install from GitHub.
It produces concrete, per-level engineering tasks so a connected coding agent
can be given the next *reviewable* slice without skipping an earlier blocker.
The engineering controller remains the authority for completed checkpoints.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

MIN_LEVEL = 4
MAX_LEVEL = 20
STEPS = (
    "AUDIT_EXISTING_DRAFTS", "COLLECT_ORIGINAL_SOURCE",
    "IMPLEMENT_FUNCTIONAL_GATES", "RUN_REGRESSION_TESTS", "PREPARE_REVIEW_PR",
)
ACTIONS = {
    "AUDIT_EXISTING_DRAFTS": "Verify exact trial/application identity, original intake PR, provenance PR, and phase.",
    "COLLECT_ORIGINAL_SOURCE": "Collect original phase-appropriate sources with exact NCT, date, SHA256 and missing-vs-not-yet-expected classifications.",
    "IMPLEMENT_FUNCTIONAL_GATES": "Implement the level-specific domain module in a draft PR, without inferring outcomes or publishing predictions.",
    "RUN_REGRESSION_TESTS": "Run offline regression tests and permanently retired-dependency audit; repair actual failures rather than clearing status flags.",
    "PREPARE_REVIEW_PR": "Create or verify a draft implementation PR with scope, provenance, review requirements and passing CI.",
}
BLOCKER_CATEGORIES = {
    "DOMAIN_SOURCE_COLLECTION_NOT_REVIEWED": "SOURCE_EVIDENCE",
    "DOMAIN_IMPLEMENTATION_NOT_APPROVED": "MISSING_DOMAIN_IMPLEMENTATION",
    "DOMAIN_REGRESSION_SUITE_NOT_APPROVED": "MISSING_TEST_COVERAGE",
    "DOMAIN_IMPLEMENTATION_PR_NOT_AVAILABLE": "MISSING_REVIEW_PR",
}
SCIENCE_NOTE = (
    "Engineering advancement confirms only the approved implementation slice; "
    "independent scientific/statistical approval remains separate."
)
MAX_TEXT = 220


def _object(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _steps(level_data: dict | None) -> dict:
    """Snapshot reported worker states; unknown stays unknown."""
    if not isinstance(level_data, dict):
        return {}
    value = level_data.get("steps")
    return _object(value)


def validate_manifest(manifest: dict) -> list[dict]:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("Unsupported/unsafe manifest schema")
    levels = manifest.get("levels")
    safety = manifest.get("safety")
    if not isinstance(levels, list) or len(levels) != 17:
        raise ValueError("Expected exactly 17 explicitly named levels")
    if [x.get("level") if isinstance(x, dict) else None for x in levels] != list(range(4, 21)):
        raise ValueError("Level order or identity changed")
    if not isinstance(safety, dict) or not safety or any(v is not False for v in safety.values()):
        raise ValueError("Unexpected or enabled unsafe automation setting")
    for row in levels:
        if (not isinstance(row.get("name"), str) or not row["name"].strip() or
                not isinstance(row.get("required_evidence_fields"), list) or
                not row["required_evidence_fields"] or
                not isinstance(row.get("scientific_acceptance_criteria"), list) or
                len(row["scientific_acceptance_criteria"]) < 5 or
                row.get("completed_scientific_level") is not False):
            raise ValueError("Incomplete level domain and independent acceptance criteria")
    return levels


def _check_complete_ledger(ledger: dict, levels: list[dict]) -> int:
    """Do not accept nonsequential, manually flipped, or invented engineering progress.

    The engineering controller independently verifies evidence hashes and remote
    PRs. This viewer only trusts the contiguous *structural* count; it makes no
    claim that any completed evidence has been independently validated here.
    """
    completed = ledger.get("engineering_completed_levels", [])
    if not isinstance(completed, list) or len(completed) > len(levels):
        raise ValueError("Invalid engineering completion list")
    for index, row in enumerate(completed):
        wanted = levels[index]
        if (not isinstance(row, dict) or row.get("level") != wanted["level"] or
                row.get("scope") != wanted.get("implementation_scope") or
                not isinstance(row.get("evidence_sha256"), str) or
                len(row["evidence_sha256"]) != 64 or
                any(c not in "0123456789abcdef" for c in row["evidence_sha256"])):
            raise ValueError("Incomplete, noncontiguous or scope-mismatched engineering receipt")
    return len(completed)


def plan_work(manifest: dict, *, completion_state: dict | None = None,
              engineering_state: dict | None = None,
              focus_level: int | None = None) -> dict:
    levels = validate_manifest(manifest)
    engineering = _object(engineering_state)
    if engineering and engineering.get("mode") != "ENGINEERING_ADVANCE_REVIEW_SEPARATE":
        raise ValueError("Unrecognized engineering lane state")
    done_count = _check_complete_ledger(engineering, levels)
    pending_level = MIN_LEVEL + done_count if done_count < len(levels) else None
    if focus_level is not None and (type(focus_level) is not int or
                                    focus_level < MIN_LEVEL or focus_level > MAX_LEVEL):
        raise ValueError("Invalid level")
    ledgers = _object(_object(completion_state).get("levels"))
    tasks = []
    for idx, row in enumerate(levels):
        level = row["level"]
        checkpoint = _steps(ledgers.get(str(level)))
        completed = idx < done_count
        current = (level == pending_level)
        if completed:
            state = "ENGINEERING_SCOPE_RECORDED_COMPLETE_REQUIRES_CONTROLLER_VERIFICATION"
        elif current:
            state = "ACTIVE_ENGINEERING_LEVEL"
        else:
            state = "FUTURE_LEVEL_WAITING_FOR_PREVIOUS_ENGINEERING_LEVEL"
        blockers = []
        for step in STEPS:
            original = _object(checkpoint.get(step))
            value = original.get("status") if original.get("status") in {
                "PENDING", "RUNNING", "BLOCKED", "DONE"} else "UNKNOWN"
            if not completed and value != "DONE":
                reason = original.get("blocker")
                if not isinstance(reason, str) or len(reason) > MAX_TEXT:
                    reason = "NOT_YET_EXECUTED_OR_RECEIPT_UNAVAILABLE"
                blockers.append({
                    "checkpoint": step,
                    "observed_status": value,
                    "blocker": reason,
                    "category": BLOCKER_CATEGORIES.get(reason, "CHECKPOINT_PENDING_OR_UNCLASSIFIED"),
                    "repair": ACTIONS[step],
                })
        tasks.append({
            "level": level,
            "name": row["name"],
            "state": state,
            "required_domain_evidence": row["required_evidence_fields"],
            "implementation_draft_pr": row.get("implementation_draft_pr"),
            "implementation_scope": row.get("implementation_scope"),
            "checkpoints_to_repair": blockers,
            "engineering_completion_recorded": completed,
            "scientific_completion_verified": False,
            "can_start_engineering_now": current,
        })
    selected = next((x for x in tasks if x["level"] == focus_level), None) \
        if focus_level is not None else None
    active = next((x for x in tasks if x["can_start_engineering_now"]), None)
    return {
        "status": "READ_ONLY_SERIAL_REMEDIATION_PLAN",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "active_level": pending_level,
        "engineering_levels_recorded_complete": done_count,
        "engineering_ledger_verified_by_authoritative_controller": False,
        "next_repair": (active["checkpoints_to_repair"][0] if active and
                        active["checkpoints_to_repair"] else None),
        "selected_level": selected,
        "levels": tasks,
        "automatic_coding_agent_connected": False,
        "automatic_installation_proven": False,
        "no_merges_or_deployments": True,
        "scientific_review_separate": True,
        "notice": SCIENCE_NOTE,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1] /
                        "automation/scientific-level-completion-queue.json")
    parser.add_argument("--completion-ledger", type=Path)
    parser.add_argument("--engineering-ledger", type=Path)
    parser.add_argument("--level", type=int)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    def read_file(path: Path | None) -> dict | None:
        return json.loads(path.read_text(encoding="utf-8")) if path is not None else None
    report = plan_work(read_file(args.manifest), completion_state=read_file(args.completion_ledger),
                       engineering_state=read_file(args.engineering_ledger),focus_level=args.level)
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
