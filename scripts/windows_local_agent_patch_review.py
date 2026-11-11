#!/usr/bin/env python3
"""Static, read-only reviewer of the latest sandbox-only Level 1 AI diff.

Never applies a patch or executes the AI's code. Reconstructs the exact
expected unified diff against the current provenance validator, rejects all
deletions or unrelated additions, parses the candidate without executing it,
and stores a local review record. Manual approval remains necessary.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import difflib
import json
from pathlib import Path
import textwrap
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = "scripts/stage4_evidence_provenance.py"
ANCHOR = "    parsed = urlparse(url)\n"
SANDBOX = Path.home() / "PDUFA-Agent-Sandbox"
REPORTS = Path.home() / "PDUFA-Agent-Reports"
HEADER = "# REVIEW ONLY — generated source not executed or applied\n"
CONDITION = "any(ch.isspace() for ch in url) or parsed.fragment"
TARGET_PATH = ROOT / TARGET


def check_proposal(original: str, document: str) -> str:
    """Return an exactly approved two-line insertion; fail closed otherwise."""
    if not isinstance(document, str) or len(document) > 12_000:
        raise ValueError("Review document exceeds the allowed size")
    if not document.startswith(HEADER):
        raise ValueError("Review-only header missing")
    diff = document[len(HEADER):]
    if "\r" in diff or "\x00" in diff or original.count(ANCHOR) != 1:
        raise ValueError("Noncanonical line endings or changed baseline")
    lines = diff.splitlines(keepends=True)
    additions = [line[1:] for line in lines if line.startswith("+") and not line.startswith("+++")]
    deletions = [line[1:] for line in lines if line.startswith("-") and not line.startswith("---")]
    if deletions or len(additions) != 2:
        raise ValueError("Only the approved two-line addition is permitted")
    guard = "".join(additions)
    if not guard.endswith("\n"):
        raise ValueError("Missing final newline")
    try:
        tree = ast.parse(textwrap.dedent(guard), filename="<AI_two_line_review>")
        expected = ast.parse(
            f"if {CONDITION}:\n    raise ValueError('Invalid URL')\n"
        )
    except SyntaxError as exc:
        raise ValueError("Proposed guard has invalid syntax") from exc
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.If):
        raise ValueError("Proposed snippet contains unexpected statements")
    node = tree.body[0]
    if ast.dump(node.test) != ast.dump(expected.body[0].test):
        raise ValueError("Proposed guard changes required semantics")
    if len(node.body) != 1 or node.orelse or not isinstance(node.body[0], ast.Raise):
        raise ValueError("Only a direct ValueError raise is allowed")
    exc = node.body[0].exc
    if (not isinstance(exc, ast.Call) or not isinstance(exc.func, ast.Name)
            or exc.func.id != "ValueError" or len(exc.args) != 1 or exc.keywords
            or not isinstance(exc.args[0], ast.Constant)
            or not isinstance(exc.args[0].value, str)
            or not (1 <= len(exc.args[0].value) <= 120)):
        raise ValueError("Unexpected raise expression")

    # Preserve two-line structure and disallow hidden/extra code on either line.
    canonical = (
        "    if " + CONDITION + ":\n"
        "        raise ValueError(" + repr(exc.args[0].value) + ")\n"
    )
    if ast.dump(ast.parse(textwrap.dedent(guard))) != ast.dump(ast.parse(textwrap.dedent(canonical))):
        raise ValueError("Guard AST differs from restricted approved form")
    proposed = original.replace(ANCHOR, ANCHOR + guard, 1)
    try:
        ast.parse(proposed, filename="<AI_proposed_file_not_executed>")
    except SyntaxError as error:
        raise ValueError("Full proposed file does not parse") from error
    exact_diff = "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        proposed.splitlines(keepends=True),
        fromfile="a/" + TARGET,
        tofile="b/" + TARGET,
    ))
    if diff != exact_diff:
        raise ValueError("Diff differs from exactly reconstructed expected patch")
    return guard


def main() -> int:
    source = TARGET_PATH
    if source.is_symlink() or not source.is_file():
        print("STOP: Approved source missing or a symlink")
        return 2
    if not source.resolve().is_relative_to(ROOT.resolve()):
        print("STOP: Approved source is outside the repository")
        return 2
    try:
        audit = subprocess.run(
            [sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
            cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=240,
        )
        if audit.returncode != 0:
            print("STOP: Retirement safety audit failed")
            return 2
        candidates = [
            file for file in SANDBOX.glob("level1-url-guard-review-*.diff.txt")
            if file.is_file() and not file.is_symlink()
            and file.resolve().is_relative_to(SANDBOX.resolve())
        ]
        if not candidates:
            print("STOP: No local Level 1 proposal found")
            return 2
        latest = max(candidates, key=lambda file: (file.stat().st_mtime_ns, file.name))
        if latest.stat().st_size > 12_000:
            print("STOP: Proposal file exceeds size limit")
            return 2
        original = source.read_text(encoding="utf-8")
        content = latest.read_text(encoding="utf-8")
        guard = check_proposal(original, content)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print("STOP: Proposal review failed:", str(exc)[:180])
        return 2

    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    review = REPORTS / f"level1-patch-static-review-{stamp}.json"
    with review.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump({
            "timestamp_utc": stamp,
            "state": "STATICALLY_ACCEPTABLE_FOR_HUMAN_REVIEW_ONLY",
            "reviewed_proposal": str(latest),
            "target": TARGET,
            "source_file_modified": False,
            "generated_code_executed": False,
            "candidate_regression_tested": False,
            "approved_for_merge": False,
            "production_modified": False,
        }, handle, indent=2)
        handle.write("\n")
    print("PASS: Retirement audit")
    print("PASS: Proposed diff matches exactly one restricted URL check")
    print("PASS: Proposed Python file parses without execution")
    print("Proposed code for human review:")
    print(guard, end="")
    print("Review record:", review)
    print("No source edited, no AI-generated code executed, no merge approval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
