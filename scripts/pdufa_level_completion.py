#!/usr/bin/env python3
"""Persistent, review-gated Level 4-20 PDUFA completion worker (draft work only).

Unlike the finished intake/provenance generators, this worker tracks scientific
acceptance requirements, original-source retrieval, functional implementation,
regression tests, independent review, blockers, and next approved action.
It NEVER marks a scientific level complete automatically.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "automation/scientific-level-completion-queue.json"
DATA = Path.home() / "PDUFA-Agent-Continuous"
LEDGER = DATA / "level_completion_ledger.json"
HEARTBEAT = DATA / "heartbeat.json"
STOP = DATA / "STOP"
LOCK = DATA / "RUNNING.lock"
REPO = "pdufa/pdufa-command-center"
ISSUE = "1096"
STATES = {"PENDING", "RUNNING", "DONE", "BLOCKED"}
STEPS = ("AUDIT_EXISTING_DRAFTS", "COLLECT_ORIGINAL_SOURCE", "IMPLEMENT_FUNCTIONAL_GATES",
         "RUN_REGRESSION_TESTS", "PREPARE_REVIEW_PR", "INDEPENDENT_REVIEW")
ERROR_CODE = re.compile(r"[A-Z][A-Z0-9_]{2,80}\Z")
MAX_ATTEMPTS = 2

def utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def safe_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Unsafe local completion ledger path")
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".pdufa-stage-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)

def plan() -> dict:
    value = json.loads(PLAN.read_text(encoding="utf-8"))
    safety = value.get("safety")
    levels = value.get("levels")
    if (value.get("schema_version") != 1 or
            value.get("queue_id") != "PDUFA_LEVEL_COMPLETION_V1" or
            value.get("steps") != list(STEPS) or
            not isinstance(levels, list) or len(levels) != 17 or
            [v.get("level") for v in levels] != list(range(4, 21)) or
            not isinstance(safety, dict) or
            any(safety.get(flag) is not False for flag in
                ("automatic_merges", "production_deployments", "automatic_predictions",
                 "trades", "scientific_level_completion_by_agent",
                 "raas_dependency", "allow_automatic_execution_of_unreviewed_generated_python"))):
        raise ValueError("Unapproved or unsafe level-completion plan")
    for row in levels:
        n = row["level"]
        if (row.get("completed_scientific_level") is not False or
                row.get("original_intake_draft_pr") != 1121 + n - 4 or
                row.get("provenance_draft_pr") != 1139 + n - 4 or
                row.get("implementation_draft_pr") != ({4: 1156, 5: 1161, 6: 1163, 7: 1169}.get(n)) or
                not isinstance(row.get("scientific_acceptance_criteria"), list) or
                len(row["scientific_acceptance_criteria"]) < 5):
            raise ValueError("Incomplete or inconsistent scientific review manifest")
    return value

def new_ledger(manifest: dict) -> dict:
    return {"schema_version": 1, "queue_id": manifest["queue_id"],
            "created_utc": utc(), "updated_utc": utc(),
            "mode": "LEVEL_COMPLETION_PENDING", "scientifically_completed_levels": 0,
            "production_modified": False, "active": None, "levels": {
                str(row["level"]): {
                    "name": row["name"], "scientific_complete": False,
                    "acceptance": {criterion: False for criterion in row["scientific_acceptance_criteria"]},
                    "steps": {step: {"status": "PENDING", "attempts": 0,
                                     "blocker": None, "evidence": {}}
                              for step in STEPS}
                } for row in manifest["levels"]
            }}

def load(manifest: dict) -> dict:
    if not LEDGER.exists():
        result = new_ledger(manifest)
        safe_json(LEDGER, result)
        return result
    result = json.loads(LEDGER.read_text(encoding="utf-8"))
    if (result.get("schema_version") != 1 or result.get("queue_id") != manifest["queue_id"]
            or result.get("scientifically_completed_levels") != 0
            or result.get("production_modified") is not False
            or set(result.get("levels", {})) != {str(n) for n in range(4, 21)}):
        raise ValueError("Invalid persistent level-completion state")
    for row in manifest["levels"]:
        level = result["levels"][str(row["level"])]
        if (level.get("name") != row["name"] or level.get("scientific_complete") is not False
                or set(level.get("acceptance", {})) != set(row["scientific_acceptance_criteria"])
                or any(flag is not False for flag in level["acceptance"].values())
                or set(level.get("steps", {})) != set(STEPS)):
            raise ValueError("Scientific-level acceptance was altered without review")
        for item in level["steps"].values():
            if (item.get("status") not in STATES or type(item.get("attempts")) is not int
                    or not 0 <= item["attempts"] <= MAX_ATTEMPTS
                    or not isinstance(item.get("evidence"), dict)):
                raise ValueError("Invalid completion task state")
    return result

def save(state: dict) -> None:
    state["updated_utc"] = utc()
    safe_json(LEDGER, state)

def counts(state: dict) -> dict:
    jobs = [row for level in state["levels"].values() for row in level["steps"].values()]
    return {"tasks_done": sum(x["status"] == "DONE" for x in jobs),
            "tasks_pending": sum(x["status"] == "PENDING" for x in jobs),
            "tasks_blocked": sum(x["status"] == "BLOCKED" for x in jobs),
            "tasks_total": len(jobs), "scientifically_completed_levels": 0}

def next_step(state: dict) -> tuple[int, str] | None:
    for number in range(4, 21):
        for step in STEPS:
            item = state["levels"][str(number)]["steps"][step]
            if item["status"] == "RUNNING":
                item["status"] = "PENDING" if item["attempts"] < MAX_ATTEMPTS else "BLOCKED"
                item["blocker"] = ("INTERRUPTED_PREVIOUS_ATTEMPT"
                                   if item["status"] == "BLOCKED" else None)
            if item["status"] == "PENDING":
                return number, step
    return None

def heartbeat(mode: str, state: dict, level: int | None = None,
              task: str | None = None) -> None:
    safe_json(HEARTBEAT, {"mode": mode, "queue": "LEVEL_COMPLETION",
                           "level": level, "task": task, "updated_utc": utc(),
                           "pid": os.getpid(), "counts": counts(state),
                           "next_action": next_label(state)})

def next_label(state: dict) -> str:
    for n in range(4, 21):
        for step in STEPS:
            if state["levels"][str(n)]["steps"][step]["status"] == "PENDING":
                return f"L{n:02d}:{step}"
    return "AWAIT_REVIEW_OR_NEW_APPROVED_IMPLEMENTATION"

def cmd(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["GH_PROMPT_DISABLED"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(args, cwd=ROOT, timeout=timeout, env=env,
                          capture_output=True, text=True, errors="replace")

def confirmed_pr(pr_number: int) -> dict:
    result = cmd(["gh", "pr", "view", str(pr_number), "--repo", REPO, "--json",
                  "number,url,isDraft,state,baseRefName,headRefName"], timeout=35)
    if result.returncode:
        raise RuntimeError("GITHUB_PR_LOOKUP_FAILED")
    data = json.loads(result.stdout)
    if (data.get("number") != pr_number or data.get("state") != "OPEN"
            or data.get("isDraft") is not True
            or data.get("baseRefName") != "automation/windows-local-agent-monitor"
            or not isinstance(data.get("headRefName"), str)
            or not re.fullmatch(r"https://github\.com/pdufa/pdufa-command-center/pull/[0-9]+",
                                str(data.get("url", "")))):
        raise RuntimeError("REVIEW_PR_NOT_APPROVED_DRAFT")
    return {"pr_number": pr_number, "draft_url": data["url"]}

def confirmed_level5_pr() -> dict:
    """Verify only the known, draft Level 5 implementation PR, never a random PR."""
    result = cmd(["gh", "pr", "view", "1161", "--repo", REPO, "--json",
                  "number,url,isDraft,state,baseRefName,headRefName"], timeout=35)
    if result.returncode:
        raise RuntimeError("LEVEL5_REVIEW_PR_LOOKUP_FAILED")
    data = json.loads(result.stdout)
    if (data.get("number") != 1161 or data.get("state") != "OPEN"
            or data.get("isDraft") is not True
            or data.get("baseRefName") != "automation/engineering-lane-review-pending-20261112"
            or data.get("headRefName") != "feature/level5-contradictory-evidence-20261112"
            or data.get("url") != "https://github.com/pdufa/pdufa-command-center/pull/1161"):
        raise RuntimeError("LEVEL5_REVIEW_PR_NOT_APPROVED_DRAFT")
    return {"pr_number": 1161, "draft_url": data["url"]}


def verified_level5_candidate_ids() -> tuple[list[str], dict]:
    """Read research candidates, never rewrite canonical POOL or FOCUS membership."""
    from level4_scientific_evidence import NCT
    frozen = ROOT / "automation" / "level5-candidate-roster-20261111.json"
    doc = json.loads(frozen.read_text(encoding="utf-8"))
    rows = doc.get("records")
    if (doc.get("purpose") != "READ_ONLY_RESEARCH_CANDIDATE_LEADS_NOT_CANONICAL_FOCUS"
            or doc.get("asOf") != "2026-11-11"
            or doc.get("canonical_focus_verified") is not False
            or doc.get("source_repo_path") != "new-platform/frontend/data/p3PostDataActive.json"
            or doc.get("source_git_blob_sha1") != "b1b79b632ff6a87d6533f6135d4204cb5931e23c"
            or not isinstance(rows, list) or len(rows) != 32
            or any(not isinstance(row, dict) or
                   not isinstance(row.get("nct"), str) or
                   not NCT.fullmatch(row["nct"]) or
                   not isinstance(row.get("ticker"), str) or
                   not re.fullmatch(r"[A-Z0-9]{1,6}", row["ticker"])
                   for row in rows)):
        raise RuntimeError("LEVEL5_CANDIDATE_ROSTER_NOT_VERIFIED")
    ncts = [row["nct"] for row in rows]
    if len(set(ncts)) != 32:
        raise RuntimeError("LEVEL5_DUPLICATE_NCT")
    return ncts, doc


def confirmed_level6_pr() -> dict:
    result = cmd(["gh", "pr", "view", "1163", "--repo", REPO, "--json",
                  "number,url,isDraft,state,baseRefName,headRefName"], timeout=35)
    if result.returncode:
        raise RuntimeError("LEVEL6_REVIEW_PR_LOOKUP_FAILED")
    data = json.loads(result.stdout)
    if (data.get("number") != 1163 or data.get("state") != "OPEN"
            or data.get("isDraft") is not True
            or data.get("baseRefName") != "automation/level5-checkpoints-one-command-20261112"
            or data.get("headRefName") != "feature/level6-cross-disciplinary-evidence-20261112"
            or data.get("url") != "https://github.com/pdufa/pdufa-command-center/pull/1163"):
        raise RuntimeError("LEVEL6_REVIEW_PR_NOT_APPROVED_DRAFT")
    return {"pr_number": 1163, "draft_url": data["url"]}


def confirmed_level7_pr() -> dict:
    """Verify Level7 draft #1169 on its exact approved branch/base."""
    result = cmd(["gh", "pr", "view", "1169", "--repo", REPO, "--json",
                  "number,url,isDraft,state,baseRefName,headRefName"], timeout=35)
    if result.returncode:
        raise RuntimeError("LEVEL7_REVIEW_PR_LOOKUP_FAILED")
    data = json.loads(result.stdout)
    if (data.get("number") != 1169 or data.get("state") != "OPEN"
            or data.get("isDraft") is not True
            or data.get("baseRefName") != "automation/predictive-preflight-all-levels-20261112"
            or data.get("headRefName") != "automation/level7-engineering-readiness-20261112"
            or data.get("url") != "https://github.com/pdufa/pdufa-command-center/pull/1169"):
        raise RuntimeError("LEVEL7_REVIEW_PR_NOT_APPROVED_DRAFT")
    return {"pr_number": 1169, "draft_url": data["url"]}


def execute(number: int, step: str, manifest: dict) -> dict:
    definition = manifest["levels"][number - 4]
    if step == "AUDIT_EXISTING_DRAFTS":
        checks = [confirmed_pr(definition["original_intake_draft_pr"]),
                  confirmed_pr(definition["provenance_draft_pr"])]
        return {"result": "EXISTING_DRAFTS_AUDITED_NOT_SCIENTIFICALLY_COMPLETE",
                "drafts": checks, "required_evidence": definition["required_evidence_fields"],
                "scientific_review_required": True}
    if step == "COLLECT_ORIGINAL_SOURCE":
        if number == 7:
            from level7_source_readiness_inventory import inventory
            ncts, roster = verified_level5_candidate_ids()
            original = DATA / "level6" / "dated-cross-domain-source-gap-inventory.json"
            if not original.is_file():
                raise RuntimeError("LEVEL7_PRIOR_SOURCE_RECEIPTS_NOT_AVAILABLE")
            source = json.loads(original.read_text(encoding="utf-8"))
            report = inventory(source, ncts=ncts, freeze_as_of=roster["asOf"],
                               source_roster_blob_sha1=roster["source_git_blob_sha1"])
            dest = DATA / "level7" / "model-validation-source-and-timing-gaps.json"
            safe_json(dest, report)
            return {
                "result": "ORIGINAL_SOURCE_TIMING_GAPS_INVENTORIED_NOT_VALIDATION",
                "snapshot_nct_count": report["total"],
                "original_registry_receipts_audited": report["original_registry_receipts_audited"],
                "exact_nct_identity_matched": report["exact_nct_identity_matched"],
                "source_roster_git_blob_sha1": report["source_roster_git_blob_sha1"],
                "source_publication_dates_independently_verified": 0,
                "historical_pre_cutoff_source_freezes_verified": 0,
                "outcome_blind_historical_validations_performed": 0,
                "predictive_model_trained": False,
                "calibration_evidence_verified": False,
                "approval_probabilities_generated": False,
                "current_canonical_focus_verified": False,
                "independently_reviewed": False,
                "source_report": str(dest),
            }
        if number == 6:
            from level6_cross_disciplinary_inventory import process_ncts
            ncts, roster = verified_level5_candidate_ids()
            batch = process_ncts(ncts)
            dest = DATA / "level6" / "dated-cross-domain-source-gap-inventory.json"
            safe_json(dest, batch)
            if batch["retrieved"] != len(ncts):
                raise RuntimeError("LEVEL6_SOURCE_RETRIEVAL_PARTIAL")
            return {
                "result": "PHASE_FIRST_CROSS_DOMAIN_GAP_INVENTORY_REGISTRY_ONLY",
                "snapshot_as_of": roster["asOf"],
                "source_git_blob_sha1": roster["source_git_blob_sha1"],
                "snapshot_nct_count": len(ncts),
                "retrieved_original_source_count": batch["retrieved"],
                "unavailable_or_invalid_count": len(ncts)-batch["retrieved"],
                "preclinical_primary_sources_verified": 0,
                "regulatory_primary_sources_verified": 0,
                "cross_domain_scientific_integration_complete": False,
                "source_report": str(dest),
                "current_canonical_focus_verified": False,
                "independently_reviewed": False,
            }
        if number == 5:
            from level5_contradictory_evidence import process_ncts
            ncts, roster = verified_level5_candidate_ids()
            batch = process_ncts(ncts)
            dest = DATA / "level5" / "dated-source-challenge-inventory.json"
            safe_json(dest, batch)
            if batch["retrieved"] != len(ncts):
                raise RuntimeError("LEVEL5_SOURCE_RETRIEVAL_PARTIAL")
            return {
                "result": "DATED_CANDIDATE_ORIGINAL_REGISTRY_CHALLENGE_LEADS_INVENTORIED",
                "snapshot_as_of": roster["asOf"],
                "source_git_blob_sha1": roster["source_git_blob_sha1"],
                "snapshot_nct_count": len(ncts),
                "retrieved_original_source_count": batch["retrieved"],
                "unavailable_or_invalid_count": len(ncts)-batch["retrieved"],
                "source_report": str(dest),
                "current_canonical_focus_verified": False,
                "independently_reviewed": False,
                "negative_evidence_adjudicated": False,
            }
        if number != 4:
            raise RuntimeError("DOMAIN_SOURCE_COLLECTION_NOT_REVIEWED")
        # The dated local FOCUS research snapshot is an NCT acquisition LEAD,
        # not proof of current canonical membership. Never write to POOL/FOCUS.
        from level4_scientific_evidence import process_ncts, NCT
        snapshot = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
        doc = json.loads(snapshot.read_text(encoding="utf-8"))
        rows = doc.get("records")
        if (not isinstance(rows, list) or not 1 <= len(rows) <= 32
                or any(not isinstance(r, dict) or
                       not isinstance(r.get("nct"), str) or
                       not NCT.fullmatch(r["nct"]) for r in rows)):
            raise RuntimeError("FOCUS_SNAPSHOT_INVALID")
        ncts = [r["nct"] for r in rows]
        if len(ncts) != len(set(ncts)):
            raise RuntimeError("FOCUS_SNAPSHOT_DUPLICATE_NCT")
        batch = process_ncts(ncts)
        dest = DATA / "level4" / "dated-focus-source-inventory.json"
        safe_json(dest, batch)
        if batch["retrieved"] == 0:
            raise RuntimeError("ORIGINAL_SOURCE_RETRIEVAL_UNAVAILABLE")
        return {"result": "DATED_SNAPSHOT_ORIGINAL_REGISTRY_RECORDS_INVENTORIED",
                "snapshot_as_of": doc.get("asOf"), "snapshot_nct_count": len(ncts),
                "retrieved_original_source_count": batch["retrieved"],
                "unavailable_or_invalid_count": len(ncts) - batch["retrieved"],
                "source_report": str(dest), "current_canonical_focus_verified": False,
                "independently_reviewed": False}
    if step == "IMPLEMENT_FUNCTIONAL_GATES":
        if number == 7:
            for name in ("level7_model_validation_readiness.py",
                         "level7_source_readiness_inventory.py"):
                if not (ROOT / "scripts" / name).is_file():
                    raise RuntimeError("LEVEL7_READINESS_IMPLEMENTATION_NOT_INSTALLED")
            return {"result": "LEVEL7_READ_ONLY_VALIDATION_READINESS_CODE_PRESENT",
                    "implementation_pr": confirmed_level7_pr(),
                    "scope": definition["implementation_scope"],
                    "trained_model": False, "probability_calibrated": False}
        if number == 6:
            file = ROOT / "scripts" / "level6_cross_disciplinary_inventory.py"
            if not file.is_file():
                raise RuntimeError("LEVEL6_IMPLEMENTATION_NOT_INSTALLED")
            return {"result": "LEVEL6_CROSS_DOMAIN_GAP_INVENTORY_CODE_PRESENT_NOT_SCIENCE_SIGNOFF",
                    "implementation_pr": confirmed_level6_pr(),
                    "scope": definition["implementation_scope"]}
        if number == 5:
            file = ROOT / "scripts" / "level5_contradictory_evidence.py"
            if not file.is_file():
                raise RuntimeError("LEVEL5_IMPLEMENTATION_NOT_INSTALLED")
            return {"result": "LEVEL5_CHALLENGE_INVENTORY_CODE_PRESENT_NOT_SCIENCE_SIGNOFF",
                    "implementation_pr": confirmed_level5_pr(),
                    "scope": definition["implementation_scope"]}
        if number != 4:
            raise RuntimeError("DOMAIN_IMPLEMENTATION_NOT_APPROVED")
        file = ROOT / "scripts/level4_scientific_evidence.py"
        if not file.exists():
            raise RuntimeError("LEVEL4_IMPLEMENTATION_NOT_INSTALLED")
        return {"result": "LEVEL4_FUNCTIONAL_SOURCE_REVIEW_CODE_PRESENT_NOT_SCIENCE_SIGNOFF",
                "implementation_pr": confirmed_pr(1156)}
    if step == "RUN_REGRESSION_TESTS":
        if number == 7:
            checks = [
                ([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests",
                  "-p", "test_level7_model_validation_readiness.py", "-v"],
                 "level7_temporal_model_readiness", 13),
                ([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests",
                  "-p", "test_level7_source_readiness_inventory.py", "-v"],
                 "level7_source_gap_inventory", 12),
                ([sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
                 "permanent_retirement", None),
            ]
            reports = []
            for argv, suite, minimum in checks:
                result = cmd(argv, timeout=240)
                if result.returncode:
                    raise RuntimeError("LEVEL7_REGRESSION_OR_RETIREMENT_FAILED")
                if minimum is None:
                    reports.append({"suite": suite, "passed": True})
                else:
                    match = re.search(r"Ran (\d+) tests? in ", result.stderr + result.stdout)
                    if match is None or int(match.group(1)) < minimum:
                        raise RuntimeError("LEVEL7_TEST_COUNT_MISMATCH")
                    reports.append({"suite": suite, "passed": int(match.group(1))})
            return {"result": "LEVEL7_READINESS_OFFLINE_REGRESSIONS_PASS_NO_MODEL_TRAINED",
                    "tests": reports, "independent_review_required": True,
                    "model_validated": False, "calibrated_probabilities": False}
        if number == 6:
            checks = [
                [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests",
                 "-p", "test_level6_cross_disciplinary_inventory.py", "-v"],
                [sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
            ]
            reports = []
            for argv in checks:
                result = cmd(argv, timeout=240)
                if result.returncode:
                    raise RuntimeError("LEVEL6_REGRESSION_OR_RETIREMENT_FAILED")
                if "unittest" in argv:
                    match = re.search(r"Ran (\d+) tests? in ", result.stderr + result.stdout)
                    if match is None or int(match.group(1)) < 9:
                        raise RuntimeError("LEVEL6_TEST_COUNT_MISMATCH")
                    reports.append({"suite": "level6_cross_domain_source_gaps", "passed": int(match.group(1))})
                else:
                    reports.append({"suite": "permanent_retirement", "passed": True})
            return {"result": "LEVEL6_LOCAL_REGRESSIONS_PASS_NOT_SCIENCE_SIGNOFF",
                    "tests": reports, "independent_review_required": True}
        if number == 5:
            checks = [
                [sys.executable, "-B", "-m", "unittest", "discover",
                 "-s", "tests", "-p", "test_level5_contradictory_evidence.py", "-v"],
                [sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
            ]
            reports = []
            for argv in checks:
                result = cmd(argv, timeout=240)
                if result.returncode:
                    raise RuntimeError("LEVEL5_REGRESSION_OR_RETIREMENT_FAILED")
                if "unittest" in argv:
                    match = re.search(r"Ran (\d+) tests? in ", result.stderr + result.stdout)
                    if match is None or int(match.group(1)) < 8:
                        raise RuntimeError("LEVEL5_TEST_COUNT_MISMATCH")
                    reports.append({"suite": "level5_source_challenge", "passed": int(match.group(1))})
                else:
                    reports.append({"suite": "permanent_retirement", "passed": True})
            return {"result": "LEVEL5_LOCAL_REGRESSIONS_PASS_NOT_SCIENCE_SIGNOFF",
                    "tests": reports, "independent_review_required": True}
        if number != 4:
            raise RuntimeError("DOMAIN_REGRESSION_SUITE_NOT_APPROVED")
        commands = [
            [sys.executable, "-B", "-m", "unittest", "discover",
             "-s", "tests", "-p", "test_level4_scientific_evidence.py", "-v"],
            [sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
        ]
        reports = []
        for argv in commands:
            result = cmd(argv, timeout=240)
            if result.returncode:
                raise RuntimeError("LEVEL4_REGRESSION_OR_RETIREMENT_FAILED")
            if "unittest" in argv:
                match = re.search(r"Ran (\d+) tests? in ", result.stderr + result.stdout)
                if match is None or int(match.group(1)) < 6:
                    raise RuntimeError("LEVEL4_TEST_COUNT_MISMATCH")
                reports.append({"suite": "level4_original_source", "passed": int(match.group(1))})
            else:
                reports.append({"suite": "permanent_retirement", "passed": True})
        return {"result": "LOCAL_OFFLINE_REGRESSIONS_PASS_NOT_SCIENCE_SIGNOFF",
                "tests": reports, "independent_review_required": True}
    if step == "PREPARE_REVIEW_PR":
        if number == 7:
            return {"result": "LEVEL7_READ_ONLY_READINESS_DRAFT_VERIFIED",
                    "implementation_pr": confirmed_level7_pr()}
        if number == 6:
            return {"result": "LEVEL6_REVIEW_PR_VERIFIED_DRAFT_ONLY",
                    "implementation_pr": confirmed_level6_pr()}
        if number == 5:
            return {"result": "LEVEL5_REVIEW_PR_VERIFIED_DRAFT_ONLY",
                    "implementation_pr": confirmed_level5_pr()}
        if number != 4:
            raise RuntimeError("DOMAIN_IMPLEMENTATION_PR_NOT_AVAILABLE")
        return {"result": "EXISTING_REVIEW_PR_VERIFIED_DRAFT_ONLY",
                "implementation_pr": confirmed_pr(1156)}
    if step == "INDEPENDENT_REVIEW":
        # A level's engineering checkpoints alone are NOT its scientific
        # assessment. Every current FOCUS record must first have an actual
        # phase-first, source-backed level score; gap inventories do not count.
        # This is a necessary readiness gate, not independent signoff.
        report_path = DATA / "assessments" / "pdufa-cumulative-assessment-audit.json"
        if not report_path.is_file():
            raise RuntimeError("PDUFA_LEVEL_ASSESSMENTS_NOT_AVAILABLE")
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            stats = next(x for x in report["per_level"] if x["level"] == number)
            if (report.get("schema_version") != 1 or
                    report.get("focus_trials") != 32 or
                    report.get("assessment_records") != 32 * 17 or
                    stats["trials"] != 32 or
                    stats["provisional_numeric_scores"] != 32 or
                    stats["unscored"] != 0 or
                    stats["all_focus_trials_scored"] is not True or
                    report.get("scientific_acceptance_automated") is not False):
                raise ValueError("Missing reviewed score coverage")
        except (ValueError, TypeError, KeyError, StopIteration, json.JSONDecodeError):
            raise RuntimeError("PDUFA_LEVEL_ASSESSMENTS_NOT_READY") from None
        # Even complete provisional numerical coverage is not proof of actual
        # primary sources or an independent scientific reviewer. Never sign.
        raise RuntimeError("INDEPENDENT_REVIEW_NOT_APPROVED")
    raise ValueError("Unknown approved completion step")

def once(state: dict, manifest: dict, *, notify: bool = False) -> bool:
    selection = next_step(state)
    if selection is None:
        return False
    level, task_name = selection
    item = state["levels"][str(level)]["steps"][task_name]
    item["attempts"] += 1
    item["status"] = "RUNNING"
    item["blocker"] = None
    state["active"] = {"level": level, "task": task_name, "started_utc": utc()}
    state["mode"] = "LEVEL_COMPLETION_WORKING"
    save(state)
    heartbeat("WORKING", state, level, task_name)
    if notify:
        publish(state)
    ping_stop = threading.Event()
    def ping() -> None:
        while not ping_stop.wait(10):
            heartbeat("WORKING", state, level, task_name)
    ticker = threading.Thread(target=ping, daemon=True)
    ticker.start()
    try:
        try:
            result = execute(level, task_name, manifest)
        except (OSError, ValueError, RuntimeError, TimeoutError,
                subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            code = (str(exc) if isinstance(exc, RuntimeError) and ERROR_CODE.fullmatch(str(exc))
                    else type(exc).__name__.upper())
            item["blocker"] = code
            permanent = code in {"DOMAIN_SOURCE_COLLECTION_NOT_REVIEWED",
                                 "DOMAIN_IMPLEMENTATION_NOT_APPROVED",
                                 "DOMAIN_REGRESSION_SUITE_NOT_APPROVED",
                                 "DOMAIN_IMPLEMENTATION_PR_NOT_AVAILABLE",
                                 "INDEPENDENT_REVIEW_NOT_APPROVED",
                                 "LEVEL4_IMPLEMENTATION_NOT_INSTALLED"}
            item["status"] = ("BLOCKED" if permanent or item["attempts"] >= MAX_ATTEMPTS
                              else "PENDING")
            item["evidence"] = {"last_attempt_utc": utc(), "scientific_signoff": False}
        else:
            item["status"] = "DONE"
            item["evidence"] = {"observed_at_utc": utc(), **result,
                                "scientific_signoff": False}
    finally:
        ping_stop.set()
        ticker.join(timeout=3)
    state["active"] = None
    save(state)
    return True

def public_status(state: dict) -> str:
    active = state.get("active")
    last = None
    blockers = []
    for n in range(4, 21):
        for key, row in state["levels"][str(n)]["steps"].items():
            if row["status"] == "BLOCKED":
                blockers.append(f"L{n:02d} {key}: {row.get('blocker') or 'UNCLASSIFIED'}")
            if row["status"] == "DONE":
                last = f"L{n:02d} {key}"
    count = counts(state)
    focus_level = active["level"] if active else next(
        (n for n in range(4, 21) if any(
            x["status"] == "PENDING" for x in state["levels"][str(n)]["steps"].values())), 4)
    focus_steps = state["levels"][str(focus_level)]["steps"]
    done_keys = [key for key, x in focus_steps.items() if x["status"] == "DONE"]
    test_evidence = focus_steps["RUN_REGRESSION_TESTS"]["evidence"].get("tests", [])
    source_evidence = focus_steps["COLLECT_ORIGINAL_SOURCE"]["evidence"]
    test_line = ", ".join(
        f"{t.get('suite')}: {t.get('passed')}" for t in test_evidence
    ) if test_evidence else "not yet verified"
    source_line = (source_evidence.get("result") or
                   source_evidence.get("last_attempt_utc") or "not yet retrieved")
    visible = blockers[:12]
    if len(blockers) > 12:
        visible.append(f"... plus {len(blockers)-12} additional recorded blockers")
    return (
        "# PDUFA continuous-development monitor\n\n"
        "**Mode:** LEVEL COMPLETION, not research-intake draft generation\n\n"
        f"**Updated UTC:** {utc()}\n\n"
        f"**Current level/task:** {('L'+str(active['level'])+' '+active['task']) if active else 'none running'}\n\n"
        f"**Tasks completed (engineering checkpoints only):** {count['tasks_done']}/{count['tasks_total']}\n\n"
        "**Scientific levels independently completed:** 0/17\n\n"
        f"**Last engineering checkpoint:** {last or 'none'}\n\n"
        f"**Focus level:** {focus_level}\n\n"
        f"**Completed engineering requirements at this level:** {', '.join(done_keys) or 'none'}\n\n"
        f"**Test results:** {test_line}\n\n"
        f"**Original-source work:** {source_line}\n\n"
        f"**Next approved action:** {next_label(state)}\n\n"
        f"**Pending:** {count['tasks_pending']} | **Blocked:** {count['tasks_blocked']}\n\n"
        "**Blockers:**\n" + ("\n".join("- " + b for b in visible) if visible else "- none recorded") +
        "\n\n**Safeguards:** Review-only draft PRs; no merges, deployments, "
        "FDA prediction publishing, trading or automatic scientific signoff.\n"
        "Detailed source receipts and test results are in the local completion ledger.\n"
    )

def publish(state: dict) -> bool:
    DATA.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=DATA, prefix=".level-monitor-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(public_status(state))
        result = cmd(["gh", "issue", "edit", ISSUE, "--repo", REPO,
                      "--body-file", name], timeout=45)
        return result.returncode == 0
    finally:
        Path(name).unlink(missing_ok=True)

def process_alive(pid: int) -> bool:
    if type(pid) is not int or pid < 1:
        return True
    if os.name == "nt":
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x1000, 0, pid)
        if not handle:
            return ctypes.get_last_error() != 87
        try:
            result = ctypes.c_ulong(0)
            ok = kernel.GetExitCodeProcess(handle, ctypes.byref(result))
            return not ok or result.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

def acquire_lock() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if LOCK.is_symlink():
        raise RuntimeError("UNSAFE_LOCK")
    if LOCK.exists():
        try:
            old = json.loads(LOCK.read_text(encoding="utf-8"))
            started = datetime.fromisoformat(old["started_utc"])
            age = (datetime.now(timezone.utc) - started).total_seconds()
            if not 60 <= age <= 60 * 60 * 24 * 30 or process_alive(old["pid"]):
                raise RuntimeError("ACTIVE_OR_UNCERTAIN_WORKER_LOCK")
            if json.loads(LOCK.read_text(encoding="utf-8")) != old:
                raise RuntimeError("WORKER_LOCK_CHANGED")
            LOCK.unlink()
        except (KeyError, ValueError, TypeError, OSError) as exc:
            raise RuntimeError("WORKER_LOCK_UNVERIFIABLE") from exc
    fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump({"pid": os.getpid(), "started_utc": utc()}, stream)

def run(once_only: bool = False) -> int:
    if STOP.exists():
        print("STOPPED_BY_OWNER")
        return 0
    acquire_lock()
    try:
        manifest = plan()
        state = load(manifest)
        state["mode"] = "LEVEL_COMPLETION_RUNNING"
        save(state)
        heartbeat("RUNNING", state)
        while not STOP.exists():
            if not once(state, manifest, notify=True):
                state["mode"] = "AWAITING_INDEPENDENT_REVIEW_OR_APPROVED_WORK"
                save(state)
                heartbeat("IDLE", state)
                publish(state)
                if once_only:
                    break
                for _ in range(6):
                    if STOP.exists():
                        break
                    time.sleep(10)
                    heartbeat("IDLE", state)
                continue
            heartbeat("RUNNING", state)
            publish(state)
            if once_only:
                break
            time.sleep(2)
        if STOP.exists():
            state["mode"] = "STOPPED_BY_OWNER"
            save(state)
            heartbeat("STOPPED", state)
        return 0
    finally:
        try:
            current = json.loads(LOCK.read_text(encoding="utf-8"))
            if current.get("pid") == os.getpid():
                LOCK.unlink(missing_ok=True)
        except (OSError, ValueError):
            pass

def self_test() -> int:
    p = plan()
    state = new_ledger(p)
    assert len(state["levels"]) == 17
    assert counts(state)["tasks_total"] == 102
    assert next_step(state) == (4, "AUDIT_EXISTING_DRAFTS")
    assert state["levels"]["20"]["scientific_complete"] is False
    assert all(not any(l["acceptance"].values()) for l in state["levels"].values())
    assert "Scientific levels independently completed:** 0/17" in public_status(state)
    print("PASS: persistent fail-closed Level 4-20 queue, 102 review-gated tasks")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group(required=True)
    for name in ("run", "once", "status", "self-test", "plan"):
        actions.add_argument("--" + name, action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            return self_test()
        manifest = plan()
        if args.plan:
            print(json.dumps({"queue_id": manifest["queue_id"], "levels": 17,
                              "scientific_signoff_automatic": False, "tasks": 102}))
            return 0
        if args.status:
            if not LEDGER.exists():
                print("NOT_STARTED: completion ledger has not been initialized")
                return 2
            state = load(manifest)
            print(json.dumps({"mode": state["mode"], "active": state.get("active"),
                              "counts": counts(state), "next_action": next_label(state),
                              "heartbeat": str(HEARTBEAT)}, indent=2))
            return 0
        return run(once_only=args.once)
    except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as exc:
        code = str(exc) if isinstance(exc, RuntimeError) and ERROR_CODE.fullmatch(str(exc)) else type(exc).__name__.upper()
        print("STOP:", code)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
