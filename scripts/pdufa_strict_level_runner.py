#!/usr/bin/env python3
"""Strict PDUFA Level 4 -> 20 development sequencer, review-first and draft-only.

Runs the previously approved source/engineering tasks for ONE level at a time.
It never treats exhausted tasks or a draft PR as a completed scientific level.
The next level is eligible only after independent code/science reviewer receipts
for every acceptance item are verified against their GitHub issue comments.

This is an orchestration/review gate, NOT a universal code-writing AI agent:
new level-specific implementation tasks still require separately reviewed code.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

import pdufa_level_completion as base

ROOT = Path(__file__).resolve().parents[1]
DATA = base.DATA
SEQUENCE = DATA / "sequential_level_status.json"
REVIEW_DIR = DATA / "independent-level-acceptance"
MONITOR_ISSUE = 1096
REPO = "pdufa/pdufa-command-center"
NCT = re.compile(r"NCT[0-9]{8}\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")
COMMENT = re.compile(r"^https://github\.com/pdufa/pdufa-command-center/issues/([0-9]+)#issuecomment-([0-9]+)$")
MAX_LEVEL = 20

def utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_sequence() -> dict:
    return {"schema_version": 1, "mode": "STRICT_LEVEL_BY_LEVEL",
            "accepted_levels": [], "updated_utc": utc(), "active_level": 4,
            "last_review_blocker": None}

def load_sequence() -> dict:
    if not SEQUENCE.exists():
        seq = new_sequence()
        base.safe_json(SEQUENCE, seq)
        return seq
    seq = json.loads(SEQUENCE.read_text(encoding="utf-8"))
    levels = seq.get("accepted_levels")
    if (seq.get("schema_version") != 1 or seq.get("mode") != "STRICT_LEVEL_BY_LEVEL"
            or not isinstance(levels, list)
            or [x.get("level") for x in levels] != list(range(4, 4 + len(levels)))
            or len(levels) > 17
            or any(type(x.get("level")) is not int
                   or not isinstance(x.get("review_evidence_sha256"), str)
                   or not HEX.fullmatch(x["review_evidence_sha256"])
                   or not isinstance(x.get("verified_reviewers"), list)
                   or len(set(x["verified_reviewers"])) < 2
                   for x in levels)):
        raise ValueError("Unsafe or unrecognized sequential acceptance state")
    expected = min(4 + len(levels), 20)
    if seq.get("active_level") != expected:
        raise ValueError("Sequential level was moved without verified acceptance")
    return seq

def save_sequence(seq: dict) -> None:
    seq["updated_utc"] = utc()
    base.safe_json(SEQUENCE, seq)

def level(seq: dict) -> int | None:
    return 4 + len(seq["accepted_levels"]) if len(seq["accepted_levels"]) < 17 else None

def candidate(state: dict, n: int) -> str | None:
    """Never select any later level while n lacks independent acceptance."""
    for name in base.STEPS:
        item = state["levels"][str(n)]["steps"][name]
        if item["status"] == "RUNNING":
            item["status"] = ("PENDING" if item["attempts"] < base.MAX_ATTEMPTS
                              else "BLOCKED")
            item["blocker"] = ("INTERRUPTED_PREVIOUS_ATTEMPT"
                                if item["status"] == "BLOCKED" else None)
        if item["status"] == "PENDING":
            return name
    return None

def completed_work(state: dict, n: int) -> list[str]:
    return [name for name in base.STEPS
            if state["levels"][str(n)]["steps"][name]["status"] == "DONE"]

def blockers(state: dict, n: int) -> list[dict]:
    return [{"step": name, "reason": state["levels"][str(n)]["steps"][name].get("blocker")}
            for name in base.STEPS
            if state["levels"][str(n)]["steps"][name]["status"] == "BLOCKED"]

def heartbeat(seq: dict, state: dict, active_task: str | None, mode: str) -> None:
    n = level(seq)
    base.safe_json(base.HEARTBEAT, {
        "queue": "LEVEL_COMPLETION", "mode": mode, "level": n,
        "task": active_task, "updated_utc": utc(), "pid": __import__("os").getpid(),
        "accepted_scientific_levels": len(seq["accepted_levels"]),
        "next_action": f"L{n:02d}:{active_task}" if n is not None and active_task else
                       ("PROJECT_REVIEWED_END" if n is None else "AWAIT_REVIEW_OR_APPROVED_WORK"),
        "counts": base.counts(state),
    })

def monitor_text(seq: dict, state: dict, task: str | None) -> str:
    n = level(seq)
    done = completed_work(state, n) if n is not None else []
    held = blockers(state, n) if n is not None else []
    tests = (state["levels"][str(n)]["steps"]["RUN_REGRESSION_TESTS"]
             ["evidence"].get("tests", []) if n is not None else [])
    sources = (state["levels"][str(n)]["steps"]["COLLECT_ORIGINAL_SOURCE"]
               ["evidence"] if n is not None else {})
    return (
        "# PDUFA continuous-development monitor\n\n"
        "**Mode:** STRICT LEVEL-BY-LEVEL COMPLETION (draft only)\n\n"
        f"**Updated UTC:** {utc()}\n\n"
        f"**Current level:** {n if n is not None else '20 REVIEWED END'}\n\n"
        f"**Active task:** {task or 'none'}\n\n"
        f"**Reviewed levels accepted for advancement:** {len(seq['accepted_levels'])}/17\n\n"
        f"**Requirements completed at current level:** {', '.join(done) or 'none'}\n\n"
        f"**Local tests:** {json.dumps(tests, sort_keys=True)}\n\n"
        f"**Original-source results:** {json.dumps(sources, sort_keys=True)}\n\n"
        f"**Current-level blockers:** {json.dumps(held, sort_keys=True)}\n\n"
        "**Next action:** " + (
            "No further levels" if n is None else
            (f"Complete L{n} {candidate(state, n)}" if candidate(state, n) else
             f"Await independently reviewed L{n} acceptance and approved implementation work")) +
        "\n\n**Non-negotiable:** Draft PRs only. No auto-merge, deploy, "
        "live FDA forecasts or trades. A local receipt cannot substitute for "
        "independent scientific review.\n"
    )

def publish(seq: dict, state: dict, task: str | None) -> bool:
    # A failed GitHub write cannot falsely count a level as complete.
    import os
    import tempfile
    DATA.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=DATA, prefix=".strict-monitor-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(monitor_text(seq, state, task))
        r = base.cmd(["gh", "issue", "edit", str(MONITOR_ISSUE), "--repo", REPO,
                      "--body-file", name], timeout=45)
        return r.returncode == 0
    finally:
        Path(name).unlink(missing_ok=True)

def github_comment(url: str) -> dict:
    match = COMMENT.fullmatch(url) if isinstance(url, str) else None
    if not match or int(match.group(1)) != MONITOR_ISSUE:
        raise ValueError("Reviewer comment must belong to PDUFA monitor issue")
    result = base.cmd(["gh", "api", f"repos/{REPO}/issues/comments/{match.group(2)}"],
                      timeout=45)
    if result.returncode:
        raise RuntimeError("CANNOT_VERIFY_GITHUB_REVIEW_COMMENT")
    obj = json.loads(result.stdout)
    if (obj.get("id") != int(match.group(2)) or
            obj.get("issue_url") != f"https://api.github.com/repos/{REPO}/issues/{MONITOR_ISSUE}" or
            not isinstance(obj.get("body"), str) or
            not isinstance(obj.get("user"), dict)):
        raise ValueError("GitHub reviewer identity cannot be authenticated")
    return obj

def verify_review(seq: dict, state: dict, manifest: dict, *, lookup=github_comment) -> dict | None:
    n = level(seq)
    if n is None:
        return None
    path = REVIEW_DIR / f"level_{n:02d}.json"
    if not path.exists():
        return None
    receipt = json.loads(path.read_text(encoding="utf-8"))
    criteria = manifest["levels"][n-4]["scientific_acceptance_criteria"]
    if (not isinstance(receipt, dict) or receipt.get("level") != n
            or receipt.get("schema_version") != 1
            or receipt.get("scientific_review") is not True
            or receipt.get("independent_code_review") is not True
            or receipt.get("all_acceptance_criteria_met") is not True
            or receipt.get("criteria") != criteria
            or not isinstance(receipt.get("evidence_file"), str)):
        raise ValueError("Incomplete independent Level acceptance receipt")
    evidence = Path(receipt["evidence_file"])
    if not evidence.is_absolute():
        evidence = DATA / evidence
    if (not evidence.is_file() or not evidence.resolve().is_relative_to(DATA.resolve())
            or evidence.is_symlink()):
        raise ValueError("Invalid independently reviewed evidence file")
    raw = evidence.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if not HEX.fullmatch(str(receipt.get("evidence_sha256", ""))) or digest != receipt["evidence_sha256"]:
        raise ValueError("Reviewed evidence hash mismatch")
    if not isinstance(receipt.get("review_comments"), list) or len(receipt["review_comments"]) != 2:
        raise ValueError("Separate scientific/code reviewer comments required")
    if any(state["levels"][str(n)]["steps"][step]["status"] != "DONE"
           for step in base.STEPS if step != "INDEPENDENT_REVIEW"):
        raise ValueError("Cannot accept level before engineering checkpoints finish")
    comments = []
    for role, item in zip(("SCIENTIFIC", "CODE"), receipt["review_comments"]):
        if not isinstance(item, dict) or item.get("role") != role:
            raise ValueError("Independent reviewer roles missing")
        comment = lookup(item.get("url"))
        login = comment["user"].get("login")
        if not isinstance(login, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", login):
            raise ValueError("Reviewer GitHub login missing")
        stamp = f"PDUFA-L{n:02d}-{role}-ACCEPTED SHA256:{digest}"
        if stamp not in comment["body"]:
            raise ValueError("Reviewer has not explicitly accepted this evidence fingerprint")
        comments.append(login.casefold())
    if len(set(comments)) != 2:
        raise ValueError("Scientific and code review must have independent commenters")
    return {"level": n, "review_evidence_sha256": digest,
            "verified_reviewers": comments, "verified_utc": utc(),
            "review_comment_urls": [x["url"] for x in receipt["review_comments"]]}

def perform(state: dict, seq: dict, manifest: dict, task: str) -> None:
    n = level(seq)
    if n is None:
        return
    item = state["levels"][str(n)]["steps"][task]
    item.update(status="RUNNING", attempts=item["attempts"]+1, blocker=None)
    state["active"] = {"level": n, "task": task, "started_utc": utc()}
    state["mode"] = "LEVEL_COMPLETION_WORKING"
    base.save(state)
    heartbeat(seq, state, task, "WORKING")
    publish(seq, state, task)
    try:
        result = base.execute(n, task, manifest)
    except (OSError, ValueError, RuntimeError, TimeoutError, json.JSONDecodeError) as exc:
        key = str(exc) if isinstance(exc, RuntimeError) and base.ERROR_CODE.fullmatch(str(exc)) else type(exc).__name__.upper()
        permanent = key in {
            "DOMAIN_SOURCE_COLLECTION_NOT_REVIEWED",
            "DOMAIN_IMPLEMENTATION_NOT_APPROVED",
            "DOMAIN_REGRESSION_SUITE_NOT_APPROVED",
            "DOMAIN_IMPLEMENTATION_PR_NOT_AVAILABLE",
            "INDEPENDENT_REVIEW_NOT_APPROVED",
            "LEVEL4_IMPLEMENTATION_NOT_INSTALLED",
        }
        item["status"] = ("BLOCKED" if permanent or item["attempts"] >= base.MAX_ATTEMPTS
                          else "PENDING")
        item["blocker"] = key
        item["evidence"] = {"last_attempt_utc": utc(), "scientific_signoff": False}
    else:
        item["status"] = "DONE"
        item["evidence"] = {"observed_at_utc": utc(), **result, "scientific_signoff": False}
    finally:
        state["active"] = None
        base.save(state)
    heartbeat(seq, state, None, "RUNNING")
    publish(seq, state, None)

def one_cycle(seq: dict, state: dict, manifest: dict, *, lookup=github_comment) -> str:
    n = level(seq)
    if n is None:
        return "PROJECT_REVIEWED_END"
    # A reviewer event is never simulated by a model. Only actual GitHub
    # comments by two distinct people on an exact evidence hash may advance.
    try:
        receipt = verify_review(seq, state, manifest, lookup=lookup)
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        seq["last_review_blocker"] = type(exc).__name__
        save_sequence(seq)
        receipt = None
    if receipt is not None:
        seq["accepted_levels"].append(receipt)
        seq["active_level"] = min(n+1, MAX_LEVEL)
        seq["last_review_blocker"] = None
        save_sequence(seq)
        heartbeat(seq, state, None, "RUNNING")
        publish(seq, state, None)
        return "INDEPENDENT_REVIEW_ACCEPTED_NEXT_LEVEL"
    task = candidate(state, n)
    if task is None:
        heartbeat(seq, state, None, "AWAITING_APPROVED_WORK_OR_REVIEW")
        return "BLOCKED_AWAITING_APPROVED_WORK_OR_REVIEW"
    perform(state, seq, manifest, task)
    return "ENGINEERING_CHECKPOINT_PROCESSED"

def run(*, once: bool = False, sleep_seconds: int = 60) -> int:
    if base.STOP.exists():
        print("OWNER_STOP_IS_ACTIVE")
        return 0
    base.acquire_lock()
    try:
        manifest = base.plan()
        state = base.load(manifest)
        seq = load_sequence()
        print(f"STRICT_LEVEL_BY_LEVEL_START level={level(seq)}")
        heartbeat(seq, state, None, "RUNNING")
        publish(seq, state, None)
        while not base.STOP.exists():
            result = one_cycle(seq, state, manifest)
            print(result, "level=", level(seq), flush=True)
            if result == "PROJECT_REVIEWED_END" or once:
                break
            deadline = time.monotonic() + (2 if result == "ENGINEERING_CHECKPOINT_PROCESSED" else sleep_seconds)
            while time.monotonic() < deadline and not base.STOP.exists():
                time.sleep(min(10, max(0.01, deadline-time.monotonic())))
                heartbeat(seq, state, None, "AWAITING_APPROVED_WORK_OR_REVIEW"
                          if result == "BLOCKED_AWAITING_APPROVED_WORK_OR_REVIEW" else "RUNNING")
        if base.STOP.exists():
            heartbeat(seq, state, None, "STOPPED_BY_OWNER")
        return 0
    finally:
        try:
            current = json.loads(base.LOCK.read_text(encoding="utf-8"))
            if current.get("pid") == __import__("os").getpid():
                base.LOCK.unlink()
        except (OSError, ValueError):
            pass

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    x = p.add_mutually_exclusive_group(required=True)
    x.add_argument("--run", action="store_true")
    x.add_argument("--once", action="store_true")
    x.add_argument("--status", action="store_true")
    x.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    try:
        if args.self_test:
            manifest = base.plan()
            seq = new_sequence()
            state = base.new_ledger(manifest)
            assert level(seq) == 4
            assert candidate(state, 4) == "AUDIT_EXISTING_DRAFTS"
            state["levels"]["4"]["steps"]["AUDIT_EXISTING_DRAFTS"]["status"] = "BLOCKED"
            assert candidate(state, 4) == "COLLECT_ORIGINAL_SOURCE"
            for item in state["levels"]["4"]["steps"].values():
                item["status"] = "BLOCKED"
            assert candidate(state, 4) is None
            assert level(seq) == 4
            assert "STRICT LEVEL-BY-LEVEL" in monitor_text(seq, state, None)
            print("PASS: strict stage sequencing; no automatic scientific signoff")
            return 0
        if args.status:
            if not SEQUENCE.exists():
                print("NOT_INSTALLED: sequential worker has no ledger")
                return 2
            seq = load_sequence()
            state = base.load(base.plan())
            print(json.dumps({
                "mode": seq["mode"], "active_level": level(seq),
                "reviewed_levels": len(seq["accepted_levels"]),
                "completed_engineering_requirements":
                    completed_work(state, level(seq)) if level(seq) is not None else [],
                "blockers": blockers(state, level(seq)) if level(seq) is not None else [],
                "next_step": candidate(state, level(seq)) if level(seq) is not None else None
            }, indent=2))
            return 0
        return run(once=args.once)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        key = str(exc) if isinstance(exc, RuntimeError) and base.ERROR_CODE.fullmatch(str(exc)) else type(exc).__name__.upper()
        print("STOP:", key)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
