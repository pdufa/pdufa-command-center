#!/usr/bin/env python3
"""Owner-approved follow-on development: phase-first provenance validation drafts.

This module is deliberately independent of the model's generated text. It uses
reviewed templates and synthetic tests; no FDA outcome or scientific score is
inferred. It runs only after the original Stage 4-20 engineering queue finishes.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.error

LEVELS = tuple(range(4, 21))
STATES = frozenset({"PENDING", "RUNNING", "DRAFT_PR_CREATED", "BLOCKED"})
MAX_ATTEMPTS = 2
REVIEW_KIND = "PROVENANCE_GATE_V1"

SOURCE_TEMPLATE = '''"""Research-only source metadata gate; never validates clinical findings."""
from datetime import date
import re
from urllib.parse import urlsplit

LEVEL = <<LEVEL>>
LEVEL_NAME = <<NAME>>
REQUIRED_FIELDS = <<FIELDS>>
NCT = re.compile(r"NCT[0-9]{8}\\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\\Z")


def inspect_metadata(record: dict) -> dict:
    """Identify missing/invalid receipts; cannot certify a source or outcome."""
    if not isinstance(record, dict):
        raise ValueError("Metadata record must be an object")
    nct = record.get("nct")
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        raise ValueError("Exact NCT identifier is required")
    phase = record.get("trial_phase")
    if phase not in (1, 2, 3, 4) or type(phase) is not int:
        raise ValueError("Use the actually documented trial phase")
    cutoff = record.get("knowledge_cutoff")
    try:
        as_of = date.fromisoformat(cutoff) if isinstance(cutoff, str) else None
    except ValueError:
        as_of = None
    if as_of is None or as_of.isoformat() != cutoff:
        raise ValueError("An exact knowledge cutoff date is required")
    observed = record.get("source_metadata", {})
    if not isinstance(observed, dict):
        raise ValueError("Source metadata must be keyed by evidence field")
    missing, invalid = [], []
    for key in REQUIRED_FIELDS:
        receipt = observed.get(key)
        if receipt is None:
            missing.append(key)
            continue
        if not isinstance(receipt, dict):
            invalid.append(key)
            continue
        url = receipt.get("url")
        try:
            parsed = urlsplit(url) if isinstance(url, str) else None
            good_url = (parsed is not None and parsed.scheme == "https"
                        and bool(parsed.hostname) and not parsed.username
                        and not parsed.password and not parsed.fragment)
        except ValueError:
            good_url = False
        excerpt = receipt.get("excerpt")
        digest = receipt.get("sha256")
        date_str = receipt.get("published_on")
        try:
            published = date.fromisoformat(date_str) if isinstance(date_str, str) else None
        except ValueError:
            published = None
        if (not good_url or not isinstance(excerpt, str)
                or len(excerpt.strip()) < 20
                or not isinstance(digest, str) or not DIGEST.fullmatch(digest)
                or published is None or published.isoformat() != date_str
                or published > as_of):
            invalid.append(key)
    return {
        "nct": nct, "trial_phase": phase, "level": LEVEL,
        "status": "MANUAL_SOURCE_REVIEW_REQUIRED",
        "missing_receipts": missing, "invalid_receipts": invalid,
        "source_facts_independently_verified": False,
        "scientific_stage_complete": False,
        "approval_probability": None, "clinical_score": None,
        "fda_prediction": None,
    }
'''

TEST_TEMPLATE = '''"""Synthetic evidence metadata validation; no real clinical source assertions."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/continuous_provenance/level_<<NN>>_provenance.py"
SPEC = importlib.util.spec_from_file_location("level_provenance", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def record():
    return {"nct": "NCT00000001", "trial_phase": 2,
            "knowledge_cutoff": "2026-01-01", "source_metadata": {}}


class ProvenanceGateTests(unittest.TestCase):
    def test_missing_evidence_does_not_imply_trial_failure(self):
        result = MODULE.inspect_metadata(record())
        self.assertEqual(set(result["missing_receipts"]), set(MODULE.REQUIRED_FIELDS))
        self.assertEqual(result["invalid_receipts"], [])
        self.assertFalse(result["scientific_stage_complete"])
        self.assertFalse(result["source_facts_independently_verified"])
        self.assertIsNone(result["approval_probability"])
        self.assertIsNone(result["fda_prediction"])

    def test_complete_receipts_remain_unverified(self):
        value = record()
        value["source_metadata"] = {key: {
            "url": "https://clinicaltrials.gov/study/NCT00000001",
            "excerpt": "A synthetic description of the supporting source.",
            "sha256": "a" * 64,
            "published_on": "2025-12-01",
        } for key in MODULE.REQUIRED_FIELDS}
        result = MODULE.inspect_metadata(value)
        self.assertEqual(result["missing_receipts"], [])
        self.assertEqual(result["invalid_receipts"], [])
        self.assertFalse(result["source_facts_independently_verified"])
        self.assertFalse(result["scientific_stage_complete"])
        self.assertIsNone(result["clinical_score"])

    def test_future_receipts_and_non_https_are_flagged(self):
        value = record()
        key = MODULE.REQUIRED_FIELDS[0]
        value["source_metadata"][key] = {
            "url": "http://localhost/private", "excerpt": "x" * 32,
            "sha256": "a" * 64, "published_on": "2026-02-01",
        }
        result = MODULE.inspect_metadata(value)
        self.assertIn(key, result["invalid_receipts"])

    def test_invalid_nct_phase_and_cutoff_fail_closed(self):
        value = record()
        for field, bad in (("nct", "NCT1"), ("trial_phase", "Phase 3"),
                           ("knowledge_cutoff", "not-a-date")):
            altered = dict(value)
            altered[field] = bad
            with self.assertRaises(ValueError):
                MODULE.inspect_metadata(altered)


if __name__ == "__main__":
    unittest.main()
'''


def ensure_jobs(state: dict) -> bool:
    """Append only this fixed, owner-approved follow-on queue to existing ledger."""
    prior = state.get("validation_jobs")
    if prior is None:
        state["validation_jobs"] = {
            str(n): {"stage": n, "kind": REVIEW_KIND, "status": "PENDING",
                     "attempts": 0, "draft_pr": None, "blocker": None,
                     "scientific_stage_complete": False}
            for n in LEVELS
        }
        prior = state["validation_jobs"]
        created = True
    else:
        created = False
    if not isinstance(prior, dict) or set(prior) != {str(n) for n in LEVELS}:
        raise ValueError("Approved follow-on queue shape was changed")
    for n in LEVELS:
        row = prior[str(n)]
        if (not isinstance(row, dict) or row.get("stage") != n
                or row.get("kind") != REVIEW_KIND
                or row.get("status") not in STATES
                or type(row.get("attempts")) is not int
                or row["attempts"] < 0 or row["attempts"] > MAX_ATTEMPTS
                or row.get("scientific_stage_complete") is not False):
            raise ValueError("Unsafe or corrupted follow-on task")
        if row["status"] == "DRAFT_PR_CREATED":
            if not isinstance(row.get("draft_pr"), str) or not re.fullmatch(
                    r"https://github\.com/pdufa/pdufa-command-center/pull/[1-9][0-9]*",
                    row["draft_pr"]):
                raise ValueError("Unverified follow-on draft record")
    return created


def select_job(state: dict) -> int | None:
    ensure_jobs(state)
    for n in LEVELS:
        row = state["validation_jobs"][str(n)]
        if row["status"] == "RUNNING":
            row["status"] = "PENDING" if row["attempts"] < MAX_ATTEMPTS else "BLOCKED"
            row["blocker"] = None if row["status"] == "PENDING" else "INTERRUPTED_ATTEMPT"
        if row["status"] == "PENDING":
            return n
    return None


def counts(state: dict) -> dict:
    jobs = state.get("validation_jobs", {})
    return {
        "completed": sum(x["status"] == "DRAFT_PR_CREATED" for x in jobs.values()),
        "pending": sum(x["status"] == "PENDING" for x in jobs.values()),
        "blocked": sum(x["status"] == "BLOCKED" for x in jobs.values()),
        "running": next((x["stage"] for x in jobs.values()
                         if x["status"] == "RUNNING"), None),
        "total": len(LEVELS),
    }


def paths(level: int) -> tuple[str, str]:
    slug = f"level_{level:02d}_provenance"
    return (f"scripts/continuous_provenance/{slug}.py",
            f"tests/continuous_provenance/test_{slug}.py")


def render(level: int, name: str, fields: tuple[str, ...]) -> tuple[str, str]:
    if level not in LEVELS or not fields or any(
            not isinstance(f, str) or not re.fullmatch(r"[a-z][a-z0-9_]{2,60}", f)
            for f in fields):
        raise ValueError("Invalid approved provenance task")
    source = (SOURCE_TEMPLATE.replace("<<LEVEL>>", str(level))
              .replace("<<NAME>>", repr(name))
              .replace("<<FIELDS>>", repr(tuple(fields))))
    checks = TEST_TEMPLATE.replace("<<NN>>", f"{level:02d}")
    return source, checks


def create_review_pr(core, level: int, name: str, source: str, checks: str) -> str:
    """Create and verify one reviewed-template, draft-only PR in an isolated worktree."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    branch = f"automation/continuous-provenance-l{level:02d}-{stamp}"
    working = core.WORKTREES / branch.rsplit("/", 1)[-1]
    files = paths(level)
    if working.exists() or working.is_symlink():
        raise RuntimeError("UNEXPECTED_WORKTREE_EXISTS")
    core.WORKTREES.mkdir(parents=True, exist_ok=True)
    core.require_ok(core.cmd(["git", "fetch", "--no-tags", "origin",
                 "+refs/heads/" + core.REVIEW_BASE + ":refs/remotes/origin/" + core.REVIEW_BASE],
                 timeout=180), "FETCH_REVIEW_BASE")
    core.require_ok(core.cmd(["git", "worktree", "add", "-b", branch, str(working),
                              "origin/" + core.REVIEW_BASE], timeout=90),
                    "CREATE_VALIDATION_WORKTREE")
    try:
        core.require_ok(core.cmd([sys.executable, "-B", "scripts/audit_raas_retirement.py",
                                  "--check"], cwd=working, timeout=240),
                        "REVIEW_BASE_RETIREMENT_POLICY")
        for rel, body in zip(files, (source, checks)):
            target = working / rel
            if target.exists() or target.is_symlink():
                raise RuntimeError("APPROVED_FILE_ALREADY_EXISTS")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8", newline="\n")
        core.require_ok(core.cmd([sys.executable, "-B", "scripts/audit_raas_retirement.py",
                                  "--check"], cwd=working, timeout=240),
                        "RETIREMENT_POLICY")
        tested = core.cmd([sys.executable, "-B", "-I", "-m", "unittest", "discover",
                           "-s", "tests/continuous_provenance", "-p", Path(files[1]).name,
                           "-v"], cwd=working, timeout=120)
        if tested.returncode or not re.search(
                r"Ran 4 tests? in ", tested.stderr + tested.stdout):
            raise RuntimeError("PROVENANCE_REGRESSION_FAILED")
        core.require_ok(core.cmd(["git", "add", "--", *files], cwd=working, timeout=30),
                        "STAGE_VALIDATION_FILES")
        staged = core.require_ok(core.cmd(["git", "diff", "--cached", "--name-only"],
                                         cwd=working, timeout=30),
                                 "CHECK_VALIDATION_SCOPE").splitlines()
        if sorted(staged) != sorted(files):
            raise RuntimeError("UNEXPECTED_FILE_MUTATION")
        core.require_ok(core.cmd(["git", "diff", "--cached", "--check"],
                                 cwd=working, timeout=30), "DIFF_WHITESPACE")
        hooks = core.DATA / "empty-hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        core.require_ok(core.cmd(["git", "-c", f"core.hooksPath={hooks}", "commit", "-m",
                                  f"Add Level {level} phase-first source provenance gate"],
                                 cwd=working, timeout=45), "COMMIT_VALIDATION_DRAFT")
        core.require_ok(core.cmd(["git", "-c", f"core.hooksPath={hooks}", "push",
                                  "--set-upstream", "origin", branch], cwd=working,
                                 timeout=180), "PUSH_VALIDATION_BRANCH")
        body = (
            f"## Level {level}: {name}\n\n"
            "AUTOMATED RESEARCH-ONLY PROVENANCE GATE — DRAFT PR.\n\n"
            "Validates synthetic document-receipt metadata, as-of cutoffs, NCT and "
            "trial phase, and missing/invalid fields. Does NOT fetch or verify "
            "source facts, score a trial, estimate FDA approval, or complete "
            "a scientific stage. Never requires Phase 3 data from Phase 1/2 "
            "records. No FOCUS/POOL membership or production state is changed.\n\n"
            "Only trusted local templates and four offline tests are executed. "
            "Retirement policy is checked in the exact draft worktree. "
            "Human code/scientific review is required. No merge or deployment.\n"
            f"Review base: {core.REVIEW_BASE}.\n"
        )
        core.require_ok(core.cmd(["gh", "pr", "create", "--repo", core.REPO,
                                  "--base", core.REVIEW_BASE, "--head", branch,
                                  "--draft", "--title",
                                  f"Level {level} phase-first evidence provenance gate",
                                  "--body", body], cwd=working, timeout=100),
                        "CREATE_VALIDATION_DRAFT_PR")
        detail = core.require_ok(core.cmd(["gh", "pr", "view", branch, "--repo",
                                           core.REPO, "--json",
                                           "isDraft,url,baseRefName,headRefName"],
                                          cwd=working, timeout=45),
                                 "VERIFY_VALIDATION_DRAFT_PR")
        item = json.loads(detail)
        if (item.get("isDraft") is not True
                or item.get("baseRefName") != core.REVIEW_BASE
                or item.get("headRefName") != branch
                or not isinstance(item.get("url"), str)
                or not re.fullmatch(
                    r"https://github\.com/pdufa/pdufa-command-center/pull/[1-9][0-9]*",
                    item["url"])):
            raise RuntimeError("VALIDATION_PR_NOT_VERIFIED_DRAFT")
        return item["url"]
    finally:
        cleanup = core.cmd(["git", "worktree", "remove", "--force", str(working)],
                           cwd=core.ROOT, timeout=90)
        if cleanup.returncode:
            print("WARNING: Isolated validation worktree cleanup needs attention")


def one_attempt(core, state: dict, level: int, levels: list[dict]) -> bool:
    """Bounded, independently reviewable template development task."""
    row = state["validation_jobs"][str(level)]
    row["attempts"] += 1
    row["status"] = "RUNNING"
    row["blocker"] = None
    row["last_attempt_utc"] = core.utc()
    core.save_ledger(state)
    core.heartbeat("WORKING", state, level)
    try:
        source, tests = render(level, levels[level - 1]["name"], core.SCOPES[level])
        pr = create_review_pr(core, level, levels[level - 1]["name"], source, tests)
        row["status"] = "DRAFT_PR_CREATED"
        row["draft_pr"] = pr
        core.save_ledger(state)
        return True
    except (OSError, TimeoutError, urllib.error.URLError, ValueError,
            RuntimeError, subprocess.TimeoutExpired) as error:
        code = type(error).__name__
        if isinstance(error, (RuntimeError, ValueError)):
            safe = str(error)
            if re.fullmatch(r"[A-Z][A-Z0-9_]{2,80}", safe):
                code = safe
        row["blocker"] = code
        row["status"] = "PENDING" if row["attempts"] < MAX_ATTEMPTS else "BLOCKED"
        core.save_ledger(state)
        return False
