#!/usr/bin/env python3
"""PDUFA engineering progression independent of scientific acceptance.

Engineering milestone advancement is based on five verified engineering
checkpoints for the *approved implementation scope* of each level. Scientific
signoff remains in the existing strict independent-review ledger, allowing
review to occur later. A milestone is NOT full clinical/statistical validation.
No merges, deployments, published forecasts, trades or invented reviews.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import threading
import time

import pdufa_level_completion as base
import pdufa_strict_level_runner as strict

STATE = base.DATA / "engineering_lane_ledger.json"
HEARTBEAT = base.HEARTBEAT
STEPS = tuple(x for x in base.STEPS if x != "INDEPENDENT_REVIEW")
BLOCKERS = {
    "DOMAIN_SOURCE_COLLECTION_NOT_REVIEWED",
    "DOMAIN_IMPLEMENTATION_NOT_APPROVED",
    "DOMAIN_REGRESSION_SUITE_NOT_APPROVED",
    "DOMAIN_IMPLEMENTATION_PR_NOT_AVAILABLE",
    "LEVEL4_IMPLEMENTATION_NOT_INSTALLED",
}
SHA256 = re.compile(r"[a-f0-9]{64}\Z")

def utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def first_uncompleted(seq: dict) -> int | None:
    count = len(seq["engineering_completed_levels"])
    return (4 + count) if count < 17 else None

def initial() -> dict:
    return {
        "schema_version": 1, "mode": "ENGINEERING_ADVANCE_REVIEW_SEPARATE",
        "engineering_completed_levels": [], "updated_utc": utc(),
        "last_error": None, "engineering_scope_notice":
            "Only the explicitly approved implementation slice is complete; "
            "not a full scientific level or an FDA readiness claim."
    }

def save(seq: dict) -> None:
    seq["updated_utc"] = utc()
    base.safe_json(STATE, seq)

def load(state: dict, manifest: dict) -> dict:
    if not STATE.exists():
        seq = initial()
        save(seq)
        return seq
    seq = json.loads(STATE.read_text(encoding="utf-8"))
    completed = seq.get("engineering_completed_levels")
    if (seq.get("schema_version") != 1
            or seq.get("mode") != "ENGINEERING_ADVANCE_REVIEW_SEPARATE"
            or not isinstance(completed, list) or len(completed) > 17):
        raise ValueError("Invalid engineering lane state")
    for idx, item in enumerate(completed):
        n = idx + 4
        if (not isinstance(item, dict) or item.get("level") != n
                or item.get("scope") != manifest["levels"][idx]["implementation_scope"]
                or not isinstance(item.get("evidence_sha256"), str)
                or not SHA256.fullmatch(item["evidence_sha256"])
                or not isinstance(item.get("completed_at_utc"), str)):
            raise ValueError("Noncontiguous or unapproved engineering advancement")
        # Never permit a manually flipped boolean or deleted evidence to preserve
        # an engineering acceptance claim.
        check = engineering_evidence(state, manifest, n, verify_remote=False)
        if not check or check["evidence_sha256"] != item["evidence_sha256"]:
            raise ValueError("Previously approved engineering checkpoint evidence changed")
    return seq

def engineering_evidence(state: dict, manifest: dict, n: int, *,
                         verify_remote: bool = True) -> dict | None:
    row = manifest["levels"][n-4]
    if row["implementation_scope"] == "AUDIT_ONLY_UNTIL_DOMAIN_IMPLEMENTATION_REVIEWED":
        return None
    steps = state["levels"][str(n)]["steps"]
    if any(steps[s]["status"] != "DONE" or
           not isinstance(steps[s].get("evidence"), dict) or
           steps[s]["evidence"].get("scientific_signoff") is not False
           for s in STEPS):
        return None
    evidence = {s: steps[s]["evidence"] for s in STEPS}
    if n == 4:
        sources = evidence["COLLECT_ORIGINAL_SOURCE"]
        tests = evidence["RUN_REGRESSION_TESTS"].get("tests", [])
        gates = evidence["IMPLEMENT_FUNCTIONAL_GATES"]
        review = evidence["PREPARE_REVIEW_PR"]
        if (sources.get("retrieved_original_source_count") != 29
                or sources.get("snapshot_nct_count") != 29
                or sources.get("unavailable_or_invalid_count") != 0
                or sources.get("current_canonical_focus_verified") is not False
                or sources.get("independently_reviewed") is not False
                or len(tests) != 2
                or tests[0].get("suite") != "level4_original_source"
                or type(tests[0].get("passed")) is not int
                or tests[0]["passed"] < 6
                or tests[1] != {"suite": "permanent_retirement", "passed": True}
                or gates.get("implementation_pr", {}).get("pr_number") != 1156
                or review.get("implementation_pr", {}).get("pr_number") != 1156
                or row.get("implementation_draft_pr") != 1156):
            return None
    else:
        # Future domain modules remain blocked until explicitly implemented,
        # tested and approved in the immutable manifest. No blanket level pass.
        if not isinstance(row.get("implementation_draft_pr"), int):
            return None
        if not evidence["RUN_REGRESSION_TESTS"].get("tests"):
            return None
        if (evidence["PREPARE_REVIEW_PR"].get("implementation_pr", {})
                .get("pr_number") != row["implementation_draft_pr"]):
            return None
        if n == 5:
            source = evidence["COLLECT_ORIGINAL_SOURCE"]
            tests = evidence["RUN_REGRESSION_TESTS"].get("tests", [])
            gates = evidence["IMPLEMENT_FUNCTIONAL_GATES"]
            if (row.get("implementation_draft_pr") != 1161
                    or source.get("snapshot_nct_count") != 32
                    or source.get("retrieved_original_source_count") != 32
                    or source.get("unavailable_or_invalid_count") != 0
                    or source.get("source_git_blob_sha1") != "b1b79b632ff6a87d6533f6135d4204cb5931e23c"
                    or source.get("current_canonical_focus_verified") is not False
                    or source.get("independently_reviewed") is not False
                    or source.get("negative_evidence_adjudicated") is not False
                    or len(tests) != 2
                    or tests[0].get("suite") != "level5_source_challenge"
                    or type(tests[0].get("passed")) is not int
                    or tests[0]["passed"] < 8
                    or tests[1] != {"suite": "permanent_retirement", "passed": True}
                    or gates.get("implementation_pr", {}).get("pr_number") != 1161):
                return None
        elif n == 6:
            # Only the phase-first registry-source *gap inventory* slice is
            # approved, NOT full clinical/preclinical/regulatory integration.
            source = evidence["COLLECT_ORIGINAL_SOURCE"]
            tests = evidence["RUN_REGRESSION_TESTS"].get("tests", [])
            gates = evidence["IMPLEMENT_FUNCTIONAL_GATES"]
            if (row.get("implementation_draft_pr") != 1163
                    or source.get("snapshot_nct_count") != 32
                    or source.get("retrieved_original_source_count") != 32
                    or source.get("unavailable_or_invalid_count") != 0
                    or source.get("source_git_blob_sha1") != "b1b79b632ff6a87d6533f6135d4204cb5931e23c"
                    or source.get("preclinical_primary_sources_verified") != 0
                    or source.get("regulatory_primary_sources_verified") != 0
                    or source.get("cross_domain_scientific_integration_complete") is not False
                    or source.get("current_canonical_focus_verified") is not False
                    or source.get("independently_reviewed") is not False
                    or len(tests) != 2
                    or tests[0].get("suite") != "level6_cross_domain_source_gaps"
                    or type(tests[0].get("passed")) is not int
                    or tests[0]["passed"] < 9
                    or tests[1] != {"suite": "permanent_retirement", "passed": True}
                    or gates.get("implementation_pr", {}).get("pr_number") != 1163):
                return None
        elif n == 7:
            # Read-only temporal/model-validation gap inventory for original
            # registry receipts. This does NOT approve a trained model or
            # regulatory prediction probability.
            source = evidence["COLLECT_ORIGINAL_SOURCE"]
            tests = evidence["RUN_REGRESSION_TESTS"].get("tests", [])
            gates = evidence["IMPLEMENT_FUNCTIONAL_GATES"]
            if (row.get("implementation_draft_pr") != 1169
                    or source.get("snapshot_nct_count") != 32
                    or source.get("original_registry_receipts_audited") != 32
                    or source.get("exact_nct_identity_matched") != 32
                    or source.get("source_roster_git_blob_sha1") !=
                       "b1b79b632ff6a87d6533f6135d4204cb5931e23c"
                    or source.get("source_publication_dates_independently_verified") != 0
                    or source.get("historical_pre_cutoff_source_freezes_verified") != 0
                    or source.get("outcome_blind_historical_validations_performed") != 0
                    or source.get("predictive_model_trained") is not False
                    or source.get("calibration_evidence_verified") is not False
                    or source.get("approval_probabilities_generated") is not False
                    or source.get("current_canonical_focus_verified") is not False
                    or source.get("independently_reviewed") is not False
                    or len(tests) != 3
                    or tests[0].get("suite") != "level7_temporal_model_readiness"
                    or type(tests[0].get("passed")) is not int
                    or tests[0]["passed"] < 13
                    or tests[1].get("suite") != "level7_source_gap_inventory"
                    or type(tests[1].get("passed")) is not int
                    or tests[1]["passed"] < 12
                    or tests[2] != {"suite": "permanent_retirement", "passed": True}
                    or gates.get("implementation_pr", {}).get("pr_number") != 1169
                    or gates.get("trained_model") is not False
                    or gates.get("probability_calibrated") is not False):
                return None
        else:
            return None
    pr = row["implementation_draft_pr"]
    if verify_remote:
        if n == 5:
            base.confirmed_level5_pr()
        elif n == 6:
            base.confirmed_level6_pr()
        elif n == 7:
            base.confirmed_level7_pr()
        else:
            base.confirmed_pr(pr)
    body = json.dumps({"level": n, "scope": row["implementation_scope"],
                       "implementation_draft_pr": pr, "steps": evidence},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {"level": n, "scope": row["implementation_scope"],
            "evidence_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "implementation_pr": pr, "scientifically_complete": False}

def select_task(state: dict, n: int, *, recover: bool) -> str | None:
    for key in STEPS:
        row = state["levels"][str(n)]["steps"][key]
        if row["status"] == "RUNNING" and recover:
            row["status"] = ("PENDING" if row["attempts"] < base.MAX_ATTEMPTS
                             else "BLOCKED")
            row["blocker"] = ("INTERRUPTED_PREVIOUS_ATTEMPT" if row["status"] == "BLOCKED"
                               else None)
        if row["status"] == "PENDING":
            return key
    return None

def review_sync(state: dict, manifest: dict) -> tuple[dict, str | None]:
    """Independent review still functions for earlier engineering milestones."""
    seq = strict.load_sequence()
    try:
        receipt = strict.verify_review(seq, state, manifest)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        reason = type(exc).__name__
        if seq.get("last_review_blocker") != reason:
            seq["last_review_blocker"] = reason
            strict.save_sequence(seq)
        return seq, reason
    if receipt:
        n = receipt["level"]
        seq["accepted_levels"].append(receipt)
        seq["active_level"] = min(20, n+1)
        seq["last_review_blocker"] = None
        strict.save_sequence(seq)
    return seq, None

def heartbeat(engineering: dict, scientific: dict, state: dict,
              task: str | None, mode: str) -> None:
    n = first_uncompleted(engineering)
    base.safe_json(HEARTBEAT, {
        "queue": "LEVEL_COMPLETION", "mode": mode, "level": n,
        "task": task, "pid": os.getpid(), "updated_utc": utc(),
        "accepted_engineering_slices": len(engineering["engineering_completed_levels"]),
        "independently_reviewed_scientific_levels": len(scientific["accepted_levels"]),
        "next_action": (f"L{n:02d}:{task}" if n is not None and task else
                        ("ENGINEERING_SLICES_DONE" if n is None else
                         "AWAIT_APPROVED_DOMAIN_IMPLEMENTATION_OR_EVIDENCE")),
        "counts": base.counts(state),
    })

def monitor(engineering: dict, scientific: dict, state: dict, *,
            task: str | None = None, review_issue: str | None = None) -> str:
    n = first_uncompleted(engineering)
    completed = (sum(state["levels"][str(n)]["steps"][s]["status"] == "DONE"
                     for s in STEPS) if n is not None else 0)
    blocked = ([
        {"step": key, "reason": state["levels"][str(n)]["steps"][key].get("blocker")}
        for key in STEPS if state["levels"][str(n)]["steps"][key]["status"] == "BLOCKED"
    ] if n is not None else [])
    sources = (state["levels"][str(n)]["steps"]["COLLECT_ORIGINAL_SOURCE"]["evidence"]
               if n is not None else {})
    tests = (state["levels"][str(n)]["steps"]["RUN_REGRESSION_TESTS"]["evidence"].get("tests", [])
             if n is not None else [])
    return (
        "# PDUFA continuous-development monitor\n\n"
        "**Mode:** ENGINEERING PROGRESSION; SCIENTIFIC REVIEW INDEPENDENT\n\n"
        f"**Updated UTC:** {utc()}\n\n"
        f"**Current engineering level:** {n if n is not None else 'all approved slices checked'}\n\n"
        f"**Active task:** {task or 'none'}\n\n"
        f"**Engineering implementation slices completed:** "
        f"{len(engineering['engineering_completed_levels'])}/17\n\n"
        f"**Independent scientific levels reviewed:** "
        f"{len(scientific['accepted_levels'])}/17\n\n"
        f"**Current engineering checkpoints passed:** {completed}/5\n\n"
        f"**Current engineering blockers:** {json.dumps(blocked, sort_keys=True)}\n\n"
        f"**Current original-source receipts:** {json.dumps(sources, sort_keys=True)}\n\n"
        f"**Current tests:** {json.dumps(tests, sort_keys=True)}\n\n"
        f"**Scientific review verification blocker:** {review_issue or 'none'}\n\n"
        "**Previously completed engineering slices are NOT complete scientific "
        "or statistical assessments. Level 4 only implements registry evidence "
        "inventory, not final SAP/multiplicity review or verified current FOCUS membership.**\n\n"
        "**Next action:** " + (
            "No remaining approved engineering slices" if n is None else
            f"Complete L{n} {select_task(state,n,recover=False)}" if select_task(state,n,recover=False)
            else f"Await reviewed implementation and source evidence for Level {n}") +
        "\n\n**Safeguards:** No automatic merge, deployment, published predictions, "
        "trades or independent review fabrication. Scientific acceptance ledger "
        "remains unchanged until external reviewers verify full criteria.\n"
    )

def publish(eng: dict, sci: dict, state: dict,
            task: str | None, review_issue: str | None) -> bool:
    import tempfile
    base.DATA.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=base.DATA, prefix=".engineering-monitor-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(monitor(eng,sci,state,task=task,review_issue=review_issue))
        result = base.cmd(["gh", "issue", "edit", "1096", "--repo", "pdufa/pdufa-command-center",
                           "--body-file", tmp], timeout=45)
        return result.returncode == 0
    finally:
        Path(tmp).unlink(missing_ok=True)

def perform(eng: dict, sci: dict, state: dict, manifest: dict, task: str) -> None:
    n = first_uncompleted(eng)
    if n is None:
        return
    row = state["levels"][str(n)]["steps"][task]
    row["attempts"] += 1
    row["status"] = "RUNNING"
    row["blocker"] = None
    state["active"] = {"level": n, "task": task, "started_utc": utc()}
    base.save(state)
    heartbeat(eng,sci,state,task,"ENGINEERING_WORKING")
    publish(eng,sci,state,task,None)
    stop = threading.Event()
    def ping() -> None:
        while not stop.wait(10):
            heartbeat(eng,sci,state,task,"ENGINEERING_WORKING")
    thread = threading.Thread(target=ping,daemon=True)
    thread.start()
    try:
        try:
            evidence = base.execute(n,task,manifest)
        except (OSError, ValueError, RuntimeError, TimeoutError,
                json.JSONDecodeError) as exc:
            code = (str(exc) if isinstance(exc, RuntimeError) and
                    base.ERROR_CODE.fullmatch(str(exc))
                    else type(exc).__name__.upper())
            row["status"] = ("BLOCKED" if code in BLOCKERS or
                             row["attempts"] >= base.MAX_ATTEMPTS else "PENDING")
            row["blocker"] = code
            row["evidence"] = {"last_attempt_utc":utc(),"scientific_signoff":False}
        else:
            row["status"] = "DONE"
            row["evidence"] = {"observed_at_utc": utc(), **evidence,
                               "scientific_signoff": False}
    finally:
        stop.set()
        thread.join(timeout=3)
        state["active"] = None
        base.save(state)
    heartbeat(eng,sci,state,None,"ENGINEERING_RUNNING")
    publish(eng,sci,state,None,None)

LEVEL5_REARM_ID = "LEVEL5_SOURCE_CHALLENGE_PR1161_INTEGRATION_V1"
LEVEL5_REARMABLE = {
    "COLLECT_ORIGINAL_SOURCE": "DOMAIN_SOURCE_COLLECTION_NOT_REVIEWED",
    "IMPLEMENT_FUNCTIONAL_GATES": "DOMAIN_IMPLEMENTATION_NOT_APPROVED",
    "RUN_REGRESSION_TESTS": "DOMAIN_REGRESSION_SUITE_NOT_APPROVED",
    "PREPARE_REVIEW_PR": "DOMAIN_IMPLEMENTATION_PR_NOT_AVAILABLE",
}


def rearm_level5_after_real_implementation(state: dict, manifest: dict) -> bool:
    """Retry ONLY the old L5 domain placeholders after approved new code exists.

    Never erases scientific history, never edits a completed step, never rearms
    failures from a new test/source run, and never resets other level blockers.
    A durable old-blocker receipt prevents repeated resets on every restart.
    """
    row = manifest["levels"][1]
    if (row.get("level") != 5 or row.get("implementation_draft_pr") != 1161
            or row.get("implementation_scope") !=
            "Read-only original-registry candidate challenge inventory; 32 dated source leads, not complete clinical adjudication"):
        return False
    receipt_path = base.DATA / "level5" / "approved-retry-receipt.json"
    if receipt_path.exists():
        record = json.loads(receipt_path.read_text(encoding="utf-8"))
        if record.get("scope") != LEVEL5_REARM_ID:
            raise ValueError("Level5 retry receipt from different code scope")
        return False
    if not (base.ROOT / "scripts" / "level5_contradictory_evidence.py").is_file():
        return False
    ncts, _ = base.verified_level5_candidate_ids()
    if len(ncts) != 32:
        return False
    base.confirmed_level5_pr()
    level = state["levels"]["5"]["steps"]
    to_rearm = {
        step: {
            "prior_status": item["status"],
            "prior_blocker": item["blocker"],
            "prior_attempts": item["attempts"],
            "prior_evidence": item["evidence"],
        }
        for step, code in LEVEL5_REARMABLE.items()
        if (item := level[step])["status"] == "BLOCKED"
        and item.get("blocker") == code
    }
    if not to_rearm:
        return False
    backup = base.DATA / "level5" / "prior-placeholder-blockers.json"
    if backup.exists():
        raise ValueError("Level5 placeholder-blocker backup already exists")
    base.safe_json(backup, {
        "scope": LEVEL5_REARM_ID, "recorded_utc": utc(),
        "restored_steps": to_rearm, "scientific_review_not_modified": True,
    })
    for step in to_rearm:
        item = level[step]
        item["status"] = "PENDING"
        item["attempts"] = 0
        item["blocker"] = None
        item["evidence"] = {}
    base.save(state)
    base.safe_json(receipt_path, {
        "scope": LEVEL5_REARM_ID,
        "recorded_utc": utc(),
        "reset_only_legacy_domain_placeholders": sorted(to_rearm),
        "historical_blockers_preserved_at": str(backup),
        "scientific_level_completed": False,
    })
    return True


def cycle(eng: dict, state: dict, manifest: dict, *,
          check_review: bool = True, remote: bool = True) -> str:
    # Scientific reviews are polled separately; later engineering does not
    # invalidate their acceptance and email notifier reads the same ledger.
    if check_review:
        scientific, review_issue = review_sync(state, manifest)
    else:
        scientific = strict.load_sequence()
        review_issue = None
    n = first_uncompleted(eng)
    if n is None:
        heartbeat(eng,scientific,state,None,"ENGINEERING_SCOPE_FINISHED")
        publish(eng,scientific,state,None,review_issue)
        return "ALL_APPROVED_ENGINEERING_SLICES_DONE"
    evidence = engineering_evidence(state,manifest,n,verify_remote=remote)
    if evidence is not None:
        eng["engineering_completed_levels"].append({
            "level":n,"scope":evidence["scope"],
            "evidence_sha256":evidence["evidence_sha256"],
            "completed_at_utc":utc(),
            "scientifically_complete":False,
        })
        eng["last_error"] = None
        save(eng)
        heartbeat(eng,scientific,state,None,"ENGINEERING_RUNNING")
        publish(eng,scientific,state,None,review_issue)
        return "ENGINEERING_SCOPE_ACCEPTED_ADVANCE_NEXT"
    task = select_task(state,n,recover=True)
    base.save(state)
    if task is None:
        heartbeat(eng,scientific,state,None,"ENGINEERING_AWAITING_APPROVED_WORK")
        publish(eng,scientific,state,None,review_issue)
        return "BLOCKED_AWAITING_IMPLEMENTATION_OR_SOURCE"
    perform(eng,scientific,state,manifest,task)
    return "ENGINEERING_CHECKPOINT_ATTEMPTED"

LEVEL6_REARM_ID = "LEVEL6_CROSS_DOMAIN_GAP_PR1163_INTEGRATION_V1"


def rearm_level6_after_real_implementation(state: dict, manifest: dict) -> bool:
    """Once per approved version, re-execute only the four OLD Level 6 stubs.

    Retain full prior error metadata; new source/test errors remain blockers.
    Preserve engineering levels 4-5 and all independent-science history.
    """
    row = manifest["levels"][2]
    if (row.get("level") != 6 or row.get("implementation_draft_pr") != 1163
            or row.get("implementation_scope") !=
            "Read-only phase-first cross-disciplinary original-registry source and missing-domain gap inventory for 32 dated NCT research leads; no preclinical/regulatory source adjudication"):
        return False
    receipt_path = base.DATA / "level6" / "approved-retry-receipt.json"
    if receipt_path.exists():
        record = json.loads(receipt_path.read_text(encoding="utf-8"))
        if record.get("scope") != LEVEL6_REARM_ID:
            raise ValueError("Unexpected Level6 rearm version; must review")
        return False
    if not (base.ROOT / "scripts" / "level6_cross_disciplinary_inventory.py").is_file():
        return False
    ncts, _ = base.verified_level5_candidate_ids()
    if len(ncts) != 32:
        return False
    base.confirmed_level6_pr()
    level = state["levels"]["6"]["steps"]
    to_rearm = {
        step: {"prior_status": item["status"], "prior_attempts": item["attempts"],
               "prior_blocker": item.get("blocker"), "prior_evidence": item.get("evidence")}
        for step, code in LEVEL5_REARMABLE.items()
        if (item := level[step])["status"] == "BLOCKED" and item.get("blocker") == code
    }
    if not to_rearm:
        return False
    backup = base.DATA / "level6" / "prior-placeholder-blockers.json"
    if backup.exists():
        raise ValueError("Old Level6 blocker backup exists; no overwrite")
    base.safe_json(backup, {"scope": LEVEL6_REARM_ID, "recorded_utc": utc(),
                            "restored_steps": to_rearm,
                            "scientific_review_not_modified": True})
    for step in to_rearm:
        item = level[step]
        item.update(status="PENDING", attempts=0, blocker=None, evidence={})
    base.save(state)
    base.safe_json(receipt_path, {"scope": LEVEL6_REARM_ID,
                                   "recorded_utc": utc(),
                                   "reset_only_old_domain_placeholders": sorted(to_rearm),
                                   "historical_blockers_preserved_at": str(backup),
                                   "scientific_level_completed": False})
    return True


LEVEL7_REARM_ID = "LEVEL7_READ_ONLY_MODEL_READINESS_PR1169_INTEGRATION_V1"


def rearm_level7_after_real_implementation(state: dict, manifest: dict) -> bool:
    """Retry exactly the four original Level 7 placeholder blockers once.

    This is a bounded engineering retry, not scientific signoff; preserves
    prior evidence in a durable backup, does not reset new/unrecognized errors.
    """
    row = manifest["levels"][3]
    if (row.get("level") != 7 or row.get("implementation_draft_pr") != 1169 or
            row.get("implementation_scope") !=
            "Read-only phase-first model-validation evidence-gap inventory from 32 original registry receipts; no fitted model, historical backtest, calibration or PDUFA prediction"):
        return False
    receipt = base.DATA / "level7" / "approved-retry-receipt.json"
    if receipt.exists():
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        if saved.get("scope") != LEVEL7_REARM_ID:
            raise ValueError("Unrecognized Level7 historical retry receipt")
        return False
    for name in ("level7_model_validation_readiness.py",
                 "level7_source_readiness_inventory.py"):
        if not (base.ROOT / "scripts" / name).is_file():
            return False
    if not (base.DATA / "level6" / "dated-cross-domain-source-gap-inventory.json").is_file():
        return False
    ncts, _ = base.verified_level5_candidate_ids()
    if len(ncts) != 32:
        return False
    base.confirmed_level7_pr()
    steps = state["levels"]["7"]["steps"]
    to_rearm = {
        step: {"prior_status": item["status"], "prior_attempts": item["attempts"],
               "prior_blocker": item.get("blocker"), "prior_evidence": item.get("evidence")}
        for step, code in LEVEL5_REARMABLE.items()
        if (item := steps[step])["status"] == "BLOCKED" and item.get("blocker") == code
    }
    if not to_rearm:
        return False
    backup = base.DATA / "level7" / "prior-placeholder-blockers.json"
    if backup.exists():
        raise ValueError("Old Level7 blocker backup exists; no overwrite")
    base.safe_json(backup, {"scope": LEVEL7_REARM_ID, "recorded_utc": utc(),
                            "restored_steps": to_rearm, "scientific_review_not_modified": True})
    for step in to_rearm:
        steps[step].update(status="PENDING", attempts=0, blocker=None, evidence={})
    base.save(state)
    base.safe_json(receipt, {"scope": LEVEL7_REARM_ID, "recorded_utc": utc(),
                             "reset_only_old_domain_placeholders": sorted(to_rearm),
                             "historical_blockers_preserved_at": str(backup),
                             "scientific_level_completed": False})
    return True


def run(*, once: bool = False, sleep_seconds: int = 60) -> int:
    if base.STOP.exists():
        print("STOPPED_BY_OWNER")
        return 0
    base.acquire_lock()
    try:
        manifest = base.plan()
        state = base.load(manifest)
        eng = load(state,manifest)
        if first_uncompleted(eng) == 5:
            if rearm_level5_after_real_implementation(state,manifest):
                print("LEVEL5_OLD_PLACEHOLDER_RETRIED_AFTER_VERIFIED_CODE; pending checkpoints will execute",flush=True)
        if first_uncompleted(eng) == 6:
            if rearm_level6_after_real_implementation(state,manifest):
                print("LEVEL6_OLD_PLACEHOLDER_RETRIED_AFTER_VERIFIED_CODE; pending checkpoints will execute",flush=True)
        if first_uncompleted(eng) == 7:
            if rearm_level7_after_real_implementation(state,manifest):
                print("LEVEL7_OLD_PLACEHOLDER_RETRIED_AFTER_VERIFIED_CODE; pending checkpoints will execute",flush=True)
        while not base.STOP.exists():
            result = cycle(eng,state,manifest)
            print(result,"engineering_level=",first_uncompleted(eng),flush=True)
            if once:
                break
            timeout = 2 if result in {"ENGINEERING_SCOPE_ACCEPTED_ADVANCE_NEXT",
                                      "ENGINEERING_CHECKPOINT_ATTEMPTED"} else sleep_seconds
            deadline = time.monotonic()+timeout
            while not base.STOP.exists() and time.monotonic()<deadline:
                time.sleep(min(10,max(0.02,deadline-time.monotonic())))
                heartbeat(eng,strict.load_sequence(),state,None,
                          "ENGINEERING_AWAITING_APPROVED_WORK" if timeout>2
                          else "ENGINEERING_RUNNING")
        if base.STOP.exists():
            heartbeat(eng,strict.load_sequence(),state,None,"STOPPED_BY_OWNER")
        return 0
    finally:
        try:
            lock = json.loads(base.LOCK.read_text(encoding="utf-8"))
            if lock.get("pid")==os.getpid():
                base.LOCK.unlink()
        except (OSError,ValueError):
            pass

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    exclusive=parser.add_mutually_exclusive_group(required=True)
    for action in ("run","once","status","self-test"):
        exclusive.add_argument("--"+action,action="store_true")
    args=parser.parse_args()
    try:
        manifest=base.plan()
        if args.self_test:
            seq=initial()
            state=base.new_ledger(manifest)
            assert first_uncompleted(seq)==4
            assert engineering_evidence(state,manifest,4,verify_remote=False) is None
            assert select_task(state,4,recover=False)==STEPS[0]
            assert len(STEPS)==5
            assert "scientific" in monitor(seq,strict.new_sequence(),state).lower()
            print("PASS: separate engineering progression and independent scientific gate")
            return 0
        if args.status:
            if not STATE.exists():
                print("ENGINEERING_LANE_NOT_INSTALLED")
                return 2
            state=base.load(manifest)
            eng=load(state,manifest)
            sci=strict.load_sequence()
            print(json.dumps({"engineering_level":first_uncompleted(eng),
                              "engineering_scopes_done":len(eng["engineering_completed_levels"]),
                              "scientifically_reviewed":len(sci["accepted_levels"]),
                              "next_task":(select_task(state,first_uncompleted(eng),recover=False)
                                           if first_uncompleted(eng) is not None else None)},indent=2))
            return 0
        return run(once=args.once)
    except (OSError,ValueError,RuntimeError,json.JSONDecodeError) as exc:
        print("ENGINEERING_LANE_STOP:",type(exc).__name__)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
