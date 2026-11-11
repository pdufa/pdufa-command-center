#!/usr/bin/env python3
"""Level 1: produce a strictly bounded AI patch proposal, never apply it.

This demonstration uses the local Ollama model to draft one small URL guard
for an existing provenance validator. It makes a unified diff outside the
Git checkout. It NEVER runs generated code, changes repository files, commits,
pushes, opens PRs, or deploys. A human must review any proposal.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import difflib
import json
from pathlib import Path
import re
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "automation/scientific-20-level-development-queue.json"
TARGET = "scripts/stage4_evidence_provenance.py"
SANDBOX = Path.home() / "PDUFA-Agent-Sandbox"
REPORTS = Path.home() / "PDUFA-Agent-Reports"
API = "http://127.0.0.1:11434/api/generate"
ANCHOR = "    parsed = urlparse(url)\n"
REFERENCE_EXPRESSION = "any(ch.isspace() for ch in url) or parsed.fragment"


def review_guard(raw: str) -> str:
    """Accept only an exact, side-effect-free URL check with one ValueError."""
    if not isinstance(raw, str) or len(raw) > 800 or "\x00" in raw:
        raise ValueError("Guard response is not a small text snippet")
    clean = raw.strip()
    fenced = re.fullmatch(
        r"```(?:python)?\s*\n(.*?)\n```", clean, flags=re.DOTALL | re.IGNORECASE
    )
    if fenced:
        clean = fenced.group(1)
    clean = textwrap.dedent(clean).strip()
    if len(clean.splitlines()) != 2:
        raise ValueError("Guard must have exactly two Python lines")
    try:
        tree = ast.parse(clean, filename="<untrusted_ollama_guard>")
        reference = ast.parse(
            "if " + REFERENCE_EXPRESSION + ":\n"
            "    raise ValueError('Invalid URL')\n"
        )
    except SyntaxError as exc:
        raise ValueError("Guard must be valid Python") from exc
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.If):
        raise ValueError("Only one conditional guard is allowed")
    condition = tree.body[0]
    if ast.dump(condition.test) != ast.dump(reference.body[0].test):
        raise ValueError("Guard expression differs from the approved check")
    if len(condition.body) != 1 or condition.orelse:
        raise ValueError("Guard must contain exactly one raise and no else")
    statement = condition.body[0]
    if not isinstance(statement, ast.Raise) or not isinstance(statement.exc, ast.Call):
        raise ValueError("Guard must raise ValueError")
    call = statement.exc
    if (not isinstance(call.func, ast.Name) or call.func.id != "ValueError"
            or len(call.args) != 1 or call.keywords
            or not isinstance(call.args[0], ast.Constant)
            or not isinstance(call.args[0].value, str)
            or len(call.args[0].value) > 120):
        raise ValueError("Guard may only raise ValueError with a short message")
    return "    " + clean.splitlines()[0].strip() + "\n" + (
        "        " + clean.splitlines()[1].strip() + "\n"
    )


def self_test() -> None:
    ok = (
        "if any(ch.isspace() for ch in url) or parsed.fragment:\n"
        "    raise ValueError('URL contains whitespace or a fragment')"
    )
    assert review_guard(ok).startswith("    if ")
    for bad in (
        "if parsed.fragment:\n    raise ValueError('Invalid URL')",
        "if any(ch.isspace() for ch in url) or parsed.fragment:\n"
        "    print('hello')",
        "import os\n" + ok,
    ):
        try:
            review_guard(bad)
        except ValueError:
            continue
        raise AssertionError("Unsafe or out-of-scope code was accepted")
    print("PASS: Restricted AI patch guard self-tests")


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        self_test()
        return 0
    if len(sys.argv) != 1:
        print("Usage: py -3.13 scripts\\windows_local_agent_patch_proposal.py [--self-test]")
        return 2

    task_queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    levels = task_queue.get("levels", [])
    if (len(levels) != 20 or levels[0].get("level") != 1
            or levels[0].get("verified_installation") != "NOT_AUDITED"):
        print("STOP: Level 1 queue has changed; review scope before generating a patch")
        return 2
    target_path = ROOT / TARGET
    if (target_path.is_symlink() or not target_path.is_file()
            or not target_path.resolve().is_relative_to(ROOT.resolve())):
        print("STOP: Approved source file is missing or unsafe")
        return 2
    original = target_path.read_text(encoding="utf-8")
    if (original.count(ANCHOR) != 1 or 're.fullmatch(r"NCT[0-9]{8}", nct)' not in original
            or 'if parsed.scheme != "https"' not in original
            or '"scientifically_verified": False' not in original):
        print("STOP: Provenance validator differs from the approved baseline")
        return 2
    audit = subprocess.run(
        [sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
        cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=240,
    )
    if audit.returncode != 0:
        print("STOP: RAAS retirement audit failed")
        return 2
    print("PASS: Mandatory retirement safety audit")
    prompt = (
        "Create a two-line Python guard to insert into a validation function, "
        "immediately after parsed = urlparse(url). It must reject whitespace "
        "anywhere in the URL or a nonempty URL fragment. Write exactly the "
        "following Python structure with your own short error message:\n"
        "if any(ch.isspace() for ch in url) or parsed.fragment:\n"
        "    raise ValueError('Invalid source URL')\n"
        "Output ONLY these two Python lines, without extra text. "
        "Do not use any imports, file operations, networking, subprocesses, "
        "FDA predictions, or any other functions."
    )
    request = urllib.request.Request(
        API, data=json.dumps({
            "model": "qwen2.5-coder:1.5b", "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 160, "temperature": 0.0},
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            raw = json.load(response).get("response", "")
        injection = review_guard(raw)
    except (ValueError, OSError, urllib.error.URLError, TimeoutError) as exc:
        print("STOP: Generated guard rejected or Ollama unavailable:", type(exc).__name__)
        return 2
    candidate = original.replace(ANCHOR, ANCHOR + injection, 1)
    try:
        ast.parse(candidate, filename="<untrusted_patch_candidate>")
    except SyntaxError:
        print("STOP: Proposed complete file does not parse")
        return 2
    diff = "".join(difflib.unified_diff(
        original.splitlines(keepends=True), candidate.splitlines(keepends=True),
        fromfile="a/" + TARGET, tofile="b/" + TARGET,
    ))
    if not diff or len(diff) > 8000:
        print("STOP: Missing or oversized review diff")
        return 2
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    SANDBOX.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    output = SANDBOX / f"level1-url-guard-review-{stamp}.diff.txt"
    with output.open("x", encoding="utf-8", newline="\n") as file:
        file.write("# REVIEW ONLY — generated source not executed or applied\n")
        file.write(diff)
    status = REPORTS / f"level1-patch-proposal-status-{stamp}.json"
    status.write_text(json.dumps({
        "timestamp_utc": stamp, "level": 1,
        "state": "DIFF_FOR_HUMAN_REVIEW",
        "target": TARGET, "proposed_diff": str(output),
        "source_file_modified": False, "generated_source_executed": False,
        "production_modified": False, "regression_tests_on_candidate": "NOT_RUN",
    }, indent=2) + "\n", encoding="utf-8")
    print("PASS: Bounded Level 1 code-change proposal created")
    print("Proposed diff:", output)
    print("PASS: Original repository file untouched; generated code NOT executed")
    print("Human review and regression tests required before any integration")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print("STOP: Controlled patch proposal failed:", type(exc).__name__)
        raise SystemExit(1)
