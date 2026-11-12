#!/usr/bin/env python3
"""Continuous local PDUFA engineering worker: draft PRs, never merge or deploy.

Only a narrow, approved research-intake code scaffold can be generated and
executed. Ollama supplies *textual review questions* in JSON; trusted local
templates build Python modules and tests. Untrusted generated Python is never
executed. Each stage is an engineering DRAFT, not a scientific level signoff.
The worker must be started on the owner's Windows PC after a real pilot.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import tempfile
import time
import urllib.error
import urllib.request
from types import SimpleNamespace

import windows_local_agent_followon as followon

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "automation/scientific-20-level-development-queue.json"
HOME = Path.home()
DATA = HOME / "PDUFA-Agent-Continuous"
WORKTREES = HOME / "PDUFA-Agent-Worktrees"
STATE_FILE = DATA / "ledger.json"
HEARTBEAT = DATA / "heartbeat.json"
STOP_FILE = DATA / "STOP"
LOCK_FILE = DATA / "RUNNING.lock"
REPO = "pdufa/pdufa-command-center"
ISSUE = "1096"
# Draft engineering changes are reviewed against this independently audited
# development branch. main has a different retirement-audit state; never
# bypass the audit by testing one tree and changing another.
REVIEW_BASE = "automation/windows-local-agent-monitor"
MODEL = "qwen2.5-coder:1.5b"
OLLAMA = "http://127.0.0.1:11434/api/generate"
MAX_ATTEMPTS = 2
LEVELS = tuple(range(4, 21))
COOLDOWN_SECONDS = 2
# Single-thread, bounded-cpu/context workloads: max one model and one test run.
SCOPES = {
    4: ("trial_design", "prespecified_endpoints", "statistical_analysis_plan", "multiplicity"),
    5: ("negative_findings", "contradictory_sources", "study_limitations"),
    6: ("clinical_sources", "preclinical_sources", "regulatory_sources"),
    7: ("model_validation", "uncertainty_methods", "calibration_evidence"),
    8: ("efficacy_evidence", "safety_evidence", "benefit_risk_context"),
    9: ("causal_assumptions", "confounding", "counterfactual_support"),
    10: ("pathway_model", "computational_assumptions", "independent_replication"),
    11: ("adversarial_hypotheses", "falsification_tests", "unresolved_contradictions"),
    12: ("independent_model_outputs", "model_disagreements", "adjudication_protocol"),
    13: ("pharmacokinetics", "pharmacodynamics", "exposure_response"),
    14: ("subgroups", "biomarkers", "interaction_tests"),
    15: ("prior_sources", "likelihood_evidence", "sensitivity_analysis"),
    16: ("external_population", "trial_population", "transportability_assumptions"),
    17: ("historical_sources", "decision_cutoffs", "outcome_blinding"),
    18: ("regulatory_pathway", "alternative_actions", "application_cycle_provenance"),
    19: ("reproducibility_plan", "source_hashes", "independent_rerun"),
    20: ("red_team_challenges", "adjudication_record", "unresolved_risks"),
}
STATUS = frozenset(("PENDING", "RUNNING", "DRAFT_PR_CREATED", "BLOCKED"))


def public_blocker(stage: object) -> str:
    """Return only a predefined failure code, never secrets or command output."""
    raw = stage.get("blocker") if isinstance(stage, dict) else None
    if not isinstance(raw, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,80}", raw):
        return "UNCLASSIFIED_LOCAL_FAILURE" if raw else "NONE_RECORDED"
    return raw



def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Refusing unsafe state path")
    fd, tmp = tempfile.mkstemp(prefix=".pdufa-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def manifest() -> list[dict]:
    source = json.loads(MANIFEST.read_text(encoding="utf-8"))
    levels = source.get("levels")
    if (not isinstance(levels, list) or len(levels) != 20
            or [v.get("level") for v in levels] != list(range(1, 21))
            or source.get("automatic_merges") is not False
            or source.get("production_deployment") is not False
            or source.get("automatic_prediction_updates") is not False):
        raise ValueError("20-level approved queue is missing or unsafe")
    return levels


def initial_ledger(levels: list[dict]) -> dict:
    return {
        "schema_version": 1, "mode": "REQUIRES_WINDOWS_ACTIVATION",
        "created_utc": utc(), "updated_utc": utc(),
        "completed_scientific_levels": 0, "production_modified": False,
        "tasks": {
            str(n): {
                "stage": n, "name": levels[n - 1]["name"], "status": "PENDING",
                "attempts": 0, "draft_pr": None, "scientific_stage_complete": False,
                "blocker": None, "last_attempt_utc": None,
            } for n in LEVELS
        },
    }


def load_ledger(levels: list[dict]) -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        state = initial_ledger(levels)
        atomic_json(STATE_FILE, state)
        return state
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    if (state.get("schema_version") != 1 or state.get("production_modified") is not False
            or state.get("completed_scientific_levels") != 0
            or set(state.get("tasks", {})) != {str(n) for n in LEVELS}):
        raise ValueError("Persistent stage ledger does not match approved safeguards")
    for n in LEVELS:
        item = state["tasks"][str(n)]
        if (item.get("stage") != n or item.get("name") != levels[n - 1]["name"]
                or item.get("status") not in STATUS
                or type(item.get("attempts")) is not int
                or item["attempts"] < 0 or item["attempts"] > MAX_ATTEMPTS
                or item.get("scientific_stage_complete") is not False):
            raise ValueError("Stage ledger has an invalid task record")
    return state


def save_ledger(state: dict) -> None:
    state["updated_utc"] = utc()
    atomic_json(STATE_FILE, state)


def select_task(state: dict) -> int | None:
    for n in LEVELS:
        t = state["tasks"][str(n)]
        if t["status"] == "RUNNING":
            # On startup, an interrupted attempt is not falsely marked done.
            t["status"] = "PENDING" if t["attempts"] < MAX_ATTEMPTS else "BLOCKED"
            t["blocker"] = "INTERRUPTED_ATTEMPT" if t["status"] == "BLOCKED" else None
        if t["status"] == "PENDING":
            return n
    return None


def summarize(state: dict) -> dict:
    tasks = list(state["tasks"].values())
    return {
        "draft_prs_created": sum(t["status"] == "DRAFT_PR_CREATED" for t in tasks),
        "blocked": sum(t["status"] == "BLOCKED" for t in tasks),
        "pending": sum(t["status"] == "PENDING" for t in tasks),
        "currently_running": next((t["stage"] for t in tasks if t["status"] == "RUNNING"), None),
        "scientific_stages_complete": 0,
        "production_modified": False,
    }


def cmd(args: list[str], *, cwd: Path = ROOT, timeout: int = 180) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GH_PROMPT_DISABLED"] = "1"
    # No shell=True: never interpolate AI-authored instructions into a shell.
    return subprocess.run(args, cwd=cwd, timeout=timeout, capture_output=True,
                          text=True, errors="replace", env=env)


def require_ok(result: subprocess.CompletedProcess, label: str) -> str:
    if result.returncode:
        raise RuntimeError(label + "_FAILED")
    return result.stdout.strip()


def preflight(*, online: bool) -> None:
    if not (ROOT / "AGENTS.md").is_file() or not MANIFEST.is_file():
        raise RuntimeError("POLICY_OR_QUEUE_MISSING")
    manifest()
    for binary in ("git", "gh"):
        if shutil.which(binary) is None:
            raise RuntimeError(binary.upper() + "_NOT_INSTALLED")
    top = require_ok(cmd(["git", "rev-parse", "--show-toplevel"], timeout=15),
                     "GIT_REPOSITORY").replace("\\", "/").lower()
    if top != str(ROOT.resolve()).replace("\\", "/").lower():
        raise RuntimeError("REPOSITORY_ROOT_MISMATCH")
    remote = require_ok(cmd(["git", "remote", "get-url", "origin"], timeout=15),
                        "GIT_ORIGIN")
    if not (remote.rstrip("/").removesuffix(".git").endswith("github.com/" + REPO)
            or remote.rstrip("/").removesuffix(".git").endswith("github.com:" + REPO)):
        raise RuntimeError("UNEXPECTED_GIT_ORIGIN")
    policy = cmd([sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
                 timeout=240)
    require_ok(policy, "RETIREMENT_POLICY")
    if online:
        require_ok(cmd(["gh", "auth", "status"], timeout=35), "GITHUB_AUTH")
        # Local-host only. Never send owner research evidence to external AI.
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/tags", headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            models = json.load(response).get("models", [])
        if not any(x.get("name", "").startswith(MODEL) for x in models):
            raise RuntimeError("LOCAL_OLLAMA_MODEL_MISSING")


def verify_review_base() -> None:
    """Audit the exact remote draft-PR base in a clean isolated worktree.

    Does not change the task ledger or consume a Stage 4 pilot attempt.
    """
    WORKTREES.mkdir(parents=True, exist_ok=True)
    branch = "review-base-check-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    working = WORKTREES / branch
    if working.exists() or working.is_symlink():
        raise RuntimeError("UNEXPECTED_WORKTREE_EXISTS")
    require_ok(cmd(["git", "fetch", "--no-tags", "origin",
                    "+refs/heads/" + REVIEW_BASE + ":refs/remotes/origin/" + REVIEW_BASE],
                   timeout=180), "FETCH_AUDITED_REVIEW_BASE")
    require_ok(cmd(["git", "worktree", "add", "--detach", str(working),
                    "origin/" + REVIEW_BASE], timeout=90), "CREATE_REVIEW_BASE_CHECK")
    try:
        guard = cmd([sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
                    cwd=working, timeout=240)
        require_ok(guard, "REVIEW_BASE_RETIREMENT_POLICY")
    finally:
        cleanup = cmd(["git", "worktree", "remove", "--force", str(working)],
                      cwd=ROOT, timeout=90)
        require_ok(cleanup, "CLEANUP_REVIEW_BASE_CHECK")
    print("REVIEW_BASE_AUDIT_PASS: clean development review base verified")


def verify_local_commit(*, audit_base: bool = True) -> None:
    """Test a real local Git commit in a disposable detached worktree.

    Never pushes, edits the owner's checkout, creates PRs, or advances a stage.
    Do not expose Git identity, stderr, or credentials in the status output.
    """
    if audit_base:
        verify_review_base()
    for kind in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
        ident = cmd(["git", "var", kind], cwd=ROOT, timeout=20)
        if ident.returncode != 0:
            raise RuntimeError(kind + "_UNAVAILABLE")
    WORKTREES.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    working = WORKTREES / ("commit-check-" + stamp)
    if working.exists() or working.is_symlink():
        raise RuntimeError("UNEXPECTED_WORKTREE_EXISTS")
    require_ok(cmd(["git", "worktree", "add", "--detach", str(working),
                    "origin/" + REVIEW_BASE], cwd=ROOT, timeout=90),
               "CREATE_LOCAL_COMMIT_CHECK")
    try:
        # Test exactly the same commit environment and disabled hooks as a
        # real engineering PR, without publishing any diagnostic file.
        diagnostic = "scripts/continuous_stage_drafts/local-commit-diagnostic.txt"
        file = working / diagnostic
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("Isolated commit capability test only.\\n", encoding="utf-8")
        require_ok(cmd(["git", "add", "--", diagnostic], cwd=working, timeout=30),
                   "COMMIT_CHECK_STAGE")
        hooks = DATA / "empty-hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        result = cmd(["git", "-c", f"core.hooksPath={hooks}", "commit", "-m",
                      "Local isolated commit capability check"],
                     cwd=working, timeout=60)
        if result.returncode:
            detail = (result.stderr + " " + result.stdout).lower()
            if any(word in detail for word in
                   ("unable to auto-detect email", "author identity unknown",
                    "empty ident name", "no email was given")):
                raise RuntimeError("GIT_AUTHOR_IDENTITY_UNAVAILABLE")
            if any(word in detail for word in
                   ("gpg failed", "gpg: signing failed", "failed to sign",
                    "error: gpg", "signing failed")):
                raise RuntimeError("GIT_COMMIT_SIGNING_FAILED")
            if "permission denied" in detail or "access is denied" in detail:
                raise RuntimeError("GIT_COMMIT_ACCESS_DENIED")
            raise RuntimeError("LOCAL_GIT_COMMIT_FAILED")
    finally:
        cleanup = cmd(["git", "worktree", "remove", "--force", str(working)],
                      cwd=ROOT, timeout=90)
        require_ok(cleanup, "LOCAL_COMMIT_CHECK_CLEANUP")
    print("LOCAL_COMMIT_CHECK_PASS: isolated Git commit succeeded without push")


def reset_blocked_stage4_after_commit_check() -> None:
    """One targeted recovery for the reported Stage 4 Git commit blocker.

    Preserve both earlier failed attempts in the ledger's audit history.
    Never reset unrelated blockers or any scientific completion claim.
    """
    if LOCK_FILE.exists():
        raise RuntimeError("WORKER_LOCK_PRESENT")
    verify_local_commit()
    state = load_ledger(manifest())
    stage = state["tasks"]["4"]
    if (stage.get("status") == "PENDING"
            and stage.get("attempts") in (0, 1)
            and stage.get("draft_pr") is None):
        print("STAGE4_READY: no attempt reset required")
        return
    if (stage.get("status") != "BLOCKED"
            or stage.get("attempts") != MAX_ATTEMPTS
            or stage.get("blocker") != "COMMIT_DRAFT_BRANCH_FAILED"
            or stage.get("draft_pr") is not None
            or any(state["tasks"][str(n)]["status"] != "PENDING"
                   for n in LEVELS if n != 4)):
        raise RuntimeError("STAGE4_RESET_NOT_AUTHORIZED")
    stage.setdefault("recovery_history", []).append({
        "previous_blocker": stage["blocker"],
        "previous_attempts": stage["attempts"],
        "reset_utc": utc(),
        "verified_isolated_commit": True,
    })
    stage["attempts"] = 0
    stage["status"] = "PENDING"
    stage["blocker"] = None
    save_ledger(state)
    print("STAGE4_RETRY_READY: previous failures preserved; no pilot executed")


def review_questions(level: int, name: str, fields: tuple[str, ...], feedback: str = "") -> list[str]:
    prompt = (
        "Return STRICT JSON ONLY with a key review_questions containing EXACTLY "
        "four concise specific questions (each <=160 characters) for a "
        "research-only evidence intake about this scientific method. "
        "Do not state any trial has passed, FDA approval is likely, or any "
        "prediction, score, or independent signoff exists. This is an "
        "engineering scaffold; original sources remain unverified. "
        "No code, URLs, medical records, or instructions. "
        f"Level {level}: {name}. Expected source fields: {', '.join(fields)}. "
        f"Previous validation issue: {feedback[:120]}"
    )
    body = json.dumps({
        "model": MODEL, "prompt": prompt, "stream": False, "format": "json",
        "options": {"num_predict": 500, "num_ctx": 2048, "temperature": 0.1}
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as response:
        raw = json.load(response).get("response")
    if not isinstance(raw, str) or len(raw) > 8000:
        raise ValueError("MODEL_RESPONSE_INVALID")
    payload = json.loads(raw)
    questions = payload.get("review_questions") if isinstance(payload, dict) else None
    if (not isinstance(questions, list) or len(questions) != 4
            or any(not isinstance(q, str) or not 12 <= len(q.strip()) <= 160
                   or any(ord(ch) < 32 for ch in q) for q in questions)
            or len(set(questions)) != 4):
        raise ValueError("MODEL_QUESTIONS_NOT_VALIDATED")
    return [q.strip() for q in questions]


def render(level: int, name: str, fields: tuple[str, ...], questions: list[str]) -> tuple[str, str]:
    """Only this trusted template, never raw LLM code, reaches the test runner."""
    slug = f"level_{level:02d}_intake"
    source = (
        '# Research-only engineering intake. Does NOT certify this scientific level.\n'
        'from __future__ import annotations\n'
        'import re\n'
        f'LEVEL = {level}\n'
        f'LEVEL_NAME = {name!r}\n'
        f'REQUIRED_FIELDS = {fields!r}\n'
        f'REVIEW_QUESTIONS = {tuple(questions)!r}\n'
        'NCT = re.compile(r"NCT[0-9]{8}\\Z")\n\n'
        'def assess(record: dict) -> dict:\n'
        '    if not isinstance(record, dict):\n'
        '        raise ValueError("Expected one research intake record")\n'
        '    nct = record.get("nct")\n'
        '    if not isinstance(nct, str) or not NCT.fullmatch(nct):\n'
        '        raise ValueError("Exact NCT identifier required")\n'
        '    observed = record.get("evidence_fields", {})\n'
        '    if not isinstance(observed, dict):\n'
        '        raise ValueError("Evidence fields must be keyed source observations")\n'
        '    # Only identify documentary gaps; absence is not negative trial evidence.\n'
        '    missing = [key for key in REQUIRED_FIELDS if not isinstance(observed.get(key), str)\n'
        '               or not observed[key].strip()]\n'
        '    return {"nct": nct, "level": LEVEL, "status": "RESEARCH_INTAKE_REVIEW_REQUIRED",\n'
        '            "missing_source_fields": missing, "questions": list(REVIEW_QUESTIONS),\n'
        '            "source_facts_independently_verified": False,\n'
        '            "scientific_stage_complete": False, "fda_prediction": None,\n'
        '            "approval_probability": None, "clinical_score": None}\n'
    )
    tests = (
        '"""Trusted synthetic tests for research-only level scaffold."""\n'
        'import importlib.util\nfrom pathlib import Path\nimport unittest\n'
        'ROOT = Path(__file__).resolve().parents[2]\n'
        f'PATH = ROOT / "scripts/continuous_stage_drafts/{slug}.py"\n'
        'SPEC = importlib.util.spec_from_file_location("review_module", PATH)\n'
        'MODULE = importlib.util.module_from_spec(SPEC)\nSPEC.loader.exec_module(MODULE)\n\n'
        'class EvidenceIntakeTests(unittest.TestCase):\n'
        '    def test_missing_sources_are_not_negative_trial_results(self):\n'
        '        x = MODULE.assess({"nct": "NCT00000001", "evidence_fields": {}})\n'
        '        self.assertEqual(len(x["missing_source_fields"]), len(MODULE.REQUIRED_FIELDS))\n'
        '        self.assertFalse(x["scientific_stage_complete"])\n'
        '        self.assertFalse(x["source_facts_independently_verified"])\n'
        '        self.assertIsNone(x["approval_probability"])\n'
        '        self.assertIsNone(x["fda_prediction"])\n'
        '    def test_all_keys_are_present_but_science_remains_unverified(self):\n'
        '        fields = {k: "UNVERIFIED source receipt" for k in MODULE.REQUIRED_FIELDS}\n'
        '        x = MODULE.assess({"nct": "NCT00000001", "evidence_fields": fields})\n'
        '        self.assertEqual(x["missing_source_fields"], [])\n'
        '        self.assertFalse(x["scientific_stage_complete"])\n'
        '        self.assertIsNone(x["clinical_score"])\n'
        '    def test_bad_nct_rejected(self):\n'
        '        for nct in ("NCT1", "NCT١٢٣٤٥٦٧٨", "../NCT00000001"):\n'
        '            with self.assertRaises(ValueError):\n'
        '                MODULE.assess({"nct": nct})\n'
        '    def test_invalid_source_structure_rejected(self):\n'
        '        with self.assertRaises(ValueError):\n'
        '            MODULE.assess({"nct": "NCT00000001", "evidence_fields": []})\n'
        '\nif __name__ == "__main__":\n    unittest.main()\n'
    )
    return source, tests


def stage_paths(level: int) -> tuple[str, str]:
    slug = f"level_{level:02d}_intake"
    return (f"scripts/continuous_stage_drafts/{slug}.py",
            f"tests/continuous_stage_drafts/test_{slug}.py")


def new_branch(level: int, attempt: int) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"automation/continuous-l{level:02d}-{stamp}-a{attempt}"


def create_review_pr(level: int, name: str, source: str, tests: str) -> str:
    paths = stage_paths(level)
    branch = new_branch(level, 1)
    working = WORKTREES / branch.rsplit("/", 1)[-1]
    if working.exists():
        raise RuntimeError("UNEXPECTED_WORKTREE_EXISTS")
    WORKTREES.mkdir(parents=True, exist_ok=True)
    require_ok(cmd(["git", "fetch", "--no-tags", "origin",
                    "+refs/heads/" + REVIEW_BASE + ":refs/remotes/origin/" + REVIEW_BASE],
                   timeout=180), "FETCH_AUDITED_REVIEW_BASE")
    require_ok(cmd(["git", "worktree", "add", "-b", branch, str(working),
                    "origin/" + REVIEW_BASE], timeout=90), "CREATE_ISOLATED_BRANCH")
    try:
        # Fail closed if the pinned review base itself fails the retirement policy.
        # Never accept the policy test from the main worktree as evidence for a PR.
        base_guard = cmd([sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
                         cwd=working, timeout=240)
        require_ok(base_guard, "REVIEW_BASE_RETIREMENT_POLICY")
        for relative, value in zip(paths, (source, tests)):
            file = working / relative
            if file.exists() or file.is_symlink():
                raise RuntimeError("APPROVED_FILE_ALREADY_EXISTS")
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(value, encoding="utf-8", newline="\n")
        guard = cmd([sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
                    cwd=working, timeout=240)
        require_ok(guard, "RETIREMENT_POLICY")
        relative_tests = "tests/continuous_stage_drafts"
        test = cmd([sys.executable, "-B", "-I", "-m", "unittest", "discover",
                    "-s", relative_tests, "-p", Path(paths[1]).name, "-v"],
                   cwd=working, timeout=120)
        if test.returncode or not re.search(r"Ran 4 tests? in ", test.stderr + test.stdout):
            raise RuntimeError("SYNTHETIC_REGRESSION_FAILED")
        require_ok(cmd(["git", "add", "--", *paths], cwd=working, timeout=30), "STAGE_FILES")
        staged = require_ok(cmd(["git", "diff", "--cached", "--name-only"],
                                cwd=working, timeout=30), "CHECK_FILE_SCOPE").splitlines()
        if sorted(staged) != sorted(paths):
            raise RuntimeError("UNEXPECTED_FILE_MUTATION")
        require_ok(cmd(["git", "diff", "--cached", "--check"],
                       cwd=working, timeout=30), "DIFF_WHITESPACE")
        # Prohibit local Git hooks in the task worktree; no checkout or push hooks.
        hooks = DATA / "empty-hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        require_ok(cmd(["git", "-c", f"core.hooksPath={hooks}", "commit", "-m",
                        f"Add research-only Level {level} evidence intake scaffold"],
                       cwd=working, timeout=45), "COMMIT_DRAFT_BRANCH")
        require_ok(cmd(["git", "-c", f"core.hooksPath={hooks}", "push",
                        "--set-upstream", "origin", branch],
                       cwd=working, timeout=180), "PUSH_DRAFT_BRANCH")
        body = (
            f"## Level {level}: {name}\n\n"
            "AUTOMATED RESEARCH-ONLY ENGINEERING SCAFFOLD — DRAFT PR.\n\n"
            "The code only identifies missing original-source fields and lists "
            "untrusted research questions. It is NOT a completed scientific assessment, "
            "validated mechanism, approval forecast, calibrated probability, "
            "or production prediction. No FOCUS/POOL records were modified.\n\n"
            "Safety: exact NCT check, retired-systems audit, four synthetic regression "
            "tests, protected branch, no automatic merge or deployment. "
            "Human code/scientific review and normal CI are still required.\n"
            f"Review base: {REVIEW_BASE} (development only, not production).\n"
        )
        require_ok(cmd(["gh", "pr", "create", "--repo", REPO,
                        "--base", REVIEW_BASE, "--head", branch, "--draft",
                        "--title", f"Research-only Level {level} intake: {name}",
                        "--body", body], cwd=working, timeout=100), "CREATE_DRAFT_PR")
        detail = require_ok(cmd(["gh", "pr", "view", branch, "--repo", REPO,
                                 "--json", "isDraft,url,baseRefName,headRefName"],
                                cwd=working, timeout=45), "VERIFY_DRAFT_PR")
        obj = json.loads(detail)
        if (obj.get("isDraft") is not True or obj.get("baseRefName") != REVIEW_BASE
                or obj.get("headRefName") != branch
                or not isinstance(obj.get("url"), str)
                or not obj["url"].startswith("https://github.com/" + REPO + "/pull/")):
            raise RuntimeError("PR_NOT_VERIFIED_DRAFT")
        return obj["url"]
    finally:
        # Always reclaim isolated checkouts, even when audit, tests, or PR
        # creation fails. Never remove branches, pushed code, or evidence.
        cleanup = cmd(["git", "worktree", "remove", "--force", str(working)],
                      cwd=ROOT, timeout=90)
        if cleanup.returncode != 0:
            print("WARNING: Temporary worktree cleanup requires attention")


def one_attempt(state: dict, level: int, levels: list[dict]) -> bool:
    task = state["tasks"][str(level)]
    previous_blocker = task.get("blocker") or ""
    task["attempts"] += 1
    task["last_attempt_utc"] = utc()
    task["status"] = "RUNNING"
    task["blocker"] = None
    save_ledger(state)
    heartbeat("WORKING", state, level)
    try:
        questions = review_questions(level, task["name"], SCOPES[level], feedback=previous_blocker)
        source, tests = render(level, task["name"], SCOPES[level], questions)
        pr = create_review_pr(level, task["name"], source, tests)
        task["draft_pr"] = pr
        task["status"] = "DRAFT_PR_CREATED"
        task["blocker"] = None
        save_ledger(state)
        return True
    except (OSError, TimeoutError, urllib.error.URLError, ValueError,
            RuntimeError, subprocess.TimeoutExpired) as error:
        # Never store or publish raw command output, prompts or credentials.
        blocker = type(error).__name__
        if isinstance(error, (RuntimeError, ValueError)):
            safe = str(error)
            if re.fullmatch(r"[A-Z][A-Z0-9_]{2,80}", safe):
                blocker = safe
        task["status"] = "PENDING" if task["attempts"] < MAX_ATTEMPTS else "BLOCKED"
        task["blocker"] = blocker
        save_ledger(state)
        return False


def heartbeat(mode: str, state: dict, level: int | None = None) -> None:
    atomic_json(HEARTBEAT, {
        "mode": mode, "pid": os.getpid(), "updated_utc": utc(),
        "level": level, "counts": summarize(state),
        "followon_counts": followon.counts(state) if "validation_jobs" in state else None,
    })


def status(require_running: bool = False) -> int:
    if not STATE_FILE.exists():
        print("NOT_INSTALLED: no continuous-development ledger")
        return 2
    state = load_ledger(manifest())
    counts = summarize(state)
    if HEARTBEAT.exists():
        h = json.loads(HEARTBEAT.read_text(encoding="utf-8"))
        age = (datetime.now(timezone.utc)
               - datetime.fromisoformat(h["updated_utc"])).total_seconds()
        mode = h["mode"]
        if require_running and (
            mode not in ("RUNNING", "WORKING", "IDLE") or not 0 <= age <= 35
            or not LOCK_FILE.exists() or STOP_FILE.exists()
        ):
            print("NOT_VERIFIED_RUNNING")
            return 2
        print("Heartbeat:", mode, "age-seconds:", int(age))
    elif require_running:
        print("NO_HEARTBEAT")
        return 2
    print("Engineering drafts:", counts["draft_prs_created"],
          "pending:", counts["pending"], "blocked:", counts["blocked"])
    for number in LEVELS:
        stage = state["tasks"][str(number)]
        if stage.get("blocker") or stage.get("status") == "BLOCKED":
            print("Stage", number, "status:", stage.get("status"),
                  "attempts:", stage.get("attempts"),
                  "blocker:", public_blocker(stage))
    for n in LEVELS:
        item = state["tasks"][str(n)]
        if item["status"] == "PENDING":
            continue
        line = f"Level {n:02d}: {item['status']}"
        if item["status"] == "BLOCKED":
            line += " (" + str(item.get("blocker") or "UNKNOWN") + ")"
        if item["status"] == "DRAFT_PR_CREATED" and item.get("draft_pr"):
            line += " " + item["draft_pr"]
        print(line)
    next_level = next((n for n in LEVELS
                       if state["tasks"][str(n)]["status"] == "PENDING"), None)
    print("Next original engineering task:", next_level if next_level else "None")
    if "validation_jobs" in state:
        v = followon.counts(state)
        print("Follow-on provenance drafts:", v["completed"], "of", v["total"],
              "pending:", v["pending"], "blocked:", v["blocked"])
        print("Next approved provenance task:", next((
            n for n in LEVELS if state["validation_jobs"][str(n)]["status"] == "PENDING"),
            "None"))
    if HEARTBEAT.exists() and mode == "IDLE":
        print("CONTINUOUS_IDLE: worker is alive but not coding; no approved task remains")
    print("Scientific stages independently completed: 0 (not verified)")
    return 0


def publish_status(state: dict) -> None:
    # PUBLIC GitHub issue: generic stage counts only, no prompts or file paths.
    counts = summarize(state)
    content = (
        "# PDUFA continuous-development monitor\n\n"
        "**Safety:** Draft PRs only; no merges, deployments, predictions or "
        "completed scientific-level claims.\n\n"
        f"**As of UTC:** {utc()}\n\n"
        f"**Engineering draft PRs:** {counts['draft_prs_created']} of 17\n\n"
        f"**Pending engineering tasks:** {counts['pending']}\n\n"
        f"**Blocked engineering tasks:** {counts['blocked']}\n\n"
        f"**Phase-first source validation draft PRs:** {followon.counts(state)['completed']} of 17\n\n"
        if "validation_jobs" in state else ""
        "**Scientific levels independently completed by this agent:** 0\n\n"
        "Detailed blockers and development artifacts are stored locally.\n"
    )
    try:
        fd, filename = tempfile.mkstemp(prefix="pdufa-summary-", suffix=".md", dir=DATA)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            cmd(["gh", "issue", "edit", ISSUE, "--repo", REPO,
                 "--body-file", filename], timeout=45)
        finally:
            Path(filename).unlink(missing_ok=True)
    except (OSError, subprocess.TimeoutExpired):
        pass


def process_alive(pid: int) -> bool:
    """Check process presence without killing Windows processes."""
    if type(pid) is not int or pid < 1:
        return True  # Treat uncertain ownership as busy, not a stale lock.
    if os.name == "nt":
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x1000, 0, pid)
        if not handle:
            return ctypes.get_last_error() != 87  # ERROR_INVALID_PARAMETER
        try:
            exit_code = ctypes.c_ulong(0)
            success = kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            return not success or exit_code.value == 259  # STILL_ACTIVE
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def acquire_lock() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.is_symlink():
        raise RuntimeError("UNSAFE_SYMLINK_LOCK")
    if LOCK_FILE.exists():
        try:
            old = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            pid, started = old["pid"], old["started_utc"]
            age = (datetime.now(timezone.utc)
                   - datetime.fromisoformat(started)).total_seconds()
            if (not 60 <= age <= 60 * 60 * 24 * 30
                    or process_alive(pid)):
                raise FileExistsError("Active or indeterminate worker lock")
            # A terminated former process may leave a stale lock on reboot.
            # Do not claim recovery if content changed while we inspected it.
            if json.loads(LOCK_FILE.read_text(encoding="utf-8")) != old:
                raise FileExistsError("Lock changed during recovery")
            LOCK_FILE.unlink()
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            raise FileExistsError("Cannot validate existing worker lock") from None
    fd = os.open(LOCK_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(json.dumps({"pid": os.getpid(), "started_utc": utc()}) + "\n")
    return os.getpid()


def worker(*, pilot: bool) -> int:
    if STOP_FILE.exists():
        # An intentional owner STOP must be a clean exit. Returning a failure
        # would cause Windows Task Scheduler's retry-on-failure policy to
        # repeatedly relaunch a worker that the owner explicitly stopped.
        print("STOPPED_BY_OWNER: no work started; use --clear-stop only to resume")
        return 0
    try:
        acquire_lock()
    except FileExistsError:
        print("RUNNING_OR_STALE_LOCK: do not start a second worker")
        return 2
    try:
        preflight(online=True)
        levels = manifest()
        state = load_ledger(levels)
        state["mode"] = "PILOT" if pilot else "CONTINUOUS_RUNNING"
        save_ledger(state)
        heartbeat("RUNNING", state)
        completed_in_this_run = 0
        while not STOP_FILE.exists():
            level = select_task(state)
            kind = "ORIGINAL"
            if level is None:
                # Preserve the Stage 4-20 ledger and automatically advance to
                # the owner-approved, deterministic provenance work queue.
                if pilot:
                    print("PILOT_BLOCKED: Stage 4 pilot cannot be substituted")
                    return 2
                created = followon.ensure_jobs(state)
                if created:
                    save_ledger(state)
                level = followon.select_job(state)
                kind = "PROVENANCE"
            if level is None:
                # Never exit just because the bounded backlog is finished.
                # Remain visibly idle and STOP-responsive without inventing
                # new development requirements or repeating finished PRs.
                if state.get("mode") != "IDLE_AWAITING_APPROVED_WORK":
                    state["mode"] = "IDLE_AWAITING_APPROVED_WORK"
                    save_ledger(state)
                    publish_status(state)
                    print("CONTINUOUS_IDLE: approved queues exhausted; "
                          "waiting for reviewed new work", flush=True)
                heartbeat("IDLE", state)
                for _ in range(6):
                    if STOP_FILE.exists():
                        break
                    time.sleep(10)
                    heartbeat("IDLE", state)
                continue
            if pilot and (kind != "ORIGINAL" or level != 4):
                print("PILOT_BLOCKED: Stage 4 must pass a verified draft PR first")
                print("Stage 4 blocker:", public_blocker(state["tasks"]["4"]))
                return 2
            state["mode"] = "CONTINUOUS_RUNNING"
            save_ledger(state)
            heartbeat("WORKING", state, level)
            ping_stop = threading.Event()
            def ping() -> None:
                while not ping_stop.wait(10):
                    heartbeat("WORKING", state, level)
            ticker = threading.Thread(target=ping, daemon=True)
            ticker.start()
            try:
                if kind == "ORIGINAL":
                    one_attempt(state, level, levels)
                else:
                    helpers = SimpleNamespace(
                        WORKTREES=WORKTREES, ROOT=ROOT, DATA=DATA, REPO=REPO,
                        REVIEW_BASE=REVIEW_BASE, SCOPES=SCOPES, cmd=cmd,
                        require_ok=require_ok, save_ledger=save_ledger,
                        heartbeat=heartbeat, utc=utc)
                    followon.one_attempt(helpers, state, level, levels)
            finally:
                ping_stop.set()
                ticker.join(timeout=3)
            completed_in_this_run += 1
            publish_status(state)
            if pilot:
                if state["tasks"][str(level)]["status"] != "DRAFT_PR_CREATED":
                    stage = state["tasks"][str(level)]
                    print("PILOT_NOT_PASSED: Stage", level, "status", stage["status"],
                          "attempts", stage["attempts"],
                          "blocker", public_blocker(stage))
                    return 2
                state["mode"] = "PILOT_PASSED_NOT_RUNNING"
                save_ledger(state)
                heartbeat("PILOT_PASSED", state, level)
                print("PILOT_PASSED: verified a tested draft PR for level", level)
                return 0
            heartbeat("RUNNING", state)
            if not STOP_FILE.exists():
                time.sleep(COOLDOWN_SECONDS)
        state["mode"] = "STOPPED_BY_OWNER"
        save_ledger(state)
        heartbeat("STOPPED", state)
        return 0
    finally:
        # Never delete a lock that another process replaced while we ran.
        try:
            lock_data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            if lock_data.get("pid") == os.getpid():
                LOCK_FILE.unlink(missing_ok=True)
        except (OSError, ValueError, TypeError):
            pass


def self_test() -> int:
    levels = manifest()
    ledger = initial_ledger(levels)
    assert list(map(int, ledger["tasks"])) == list(LEVELS)
    assert select_task(ledger) == 4
    sample = render(4, levels[3]["name"], SCOPES[4], [
        "Which study endpoints were prespecified in the protocol?",
        "What source supports the statistical analysis plan?",
        "How was allocation concealment documented?",
        "What multiplicity correction was prespecified?",
    ])
    assert "scientific_stage_complete" in sample[0]
    assert "assertFalse(x[" in sample[1]
    assert "approval_probability" in sample[0]
    assert sum(int(t["status"] == "DRAFT_PR_CREATED")
               for t in ledger["tasks"].values()) == 0
    # Only trusted deterministic source is generated; no model Python is run.
    import ast
    ast.parse(sample[0]); ast.parse(sample[1])
    print("PASS: 17 approved Level 4–20 tasks validated")
    print("PASS: Trusted code and tests parse; no AI-authored Python executed")
    print("PASS: Queue ordering, default abstention, draft-only safety")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    for flag in ("preflight", "base-check", "commit-check", "retry-stage4", "self-test",
                 "pilot", "run", "status", "stop", "clear-stop"):
        actions.add_argument("--" + flag, action="store_true")
    parser.add_argument("--require-running", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            return self_test()
        if args.preflight:
            preflight(online=True)
            print("PREFLIGHT_PASS: GitHub, localhost Ollama, repo and retirement guard")
            return 0
        if args.base_check:
            preflight(online=True)
            verify_review_base()
            return 0
        if args.commit_check:
            preflight(online=True)
            verify_local_commit()
            return 0
        if args.retry_stage4:
            preflight(online=True)
            reset_blocked_stage4_after_commit_check()
            return 0
        if args.stop:
            DATA.mkdir(parents=True, exist_ok=True)
            STOP_FILE.write_text("STOP REQUESTED\n", encoding="utf-8")
            print("STOP_REQUESTED: worker will exit after current bounded task")
            return 0
        if args.clear_stop:
            STOP_FILE.unlink(missing_ok=True)
            print("STOP_CONTROL_CLEARED")
            return 0
        if args.status:
            return status(require_running=args.require_running)
        return worker(pilot=args.pilot)
    except (OSError, ValueError, RuntimeError, urllib.error.URLError,
            subprocess.TimeoutExpired) as error:
        reason = type(error).__name__
        if isinstance(error, (RuntimeError, ValueError)) and re.fullmatch(r"[A-Z][A-Z0-9_]{2,80}", str(error)):
            reason = str(error)
        print("STOP:", reason)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
