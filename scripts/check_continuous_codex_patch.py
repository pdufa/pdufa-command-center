#!/usr/bin/env python3
"""Hard allowlist on all Codex changed paths before accepting a PR patch."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPES = {
    "medical-source-gates-01": frozenset({
        "new-platform/backend/app/medical_method_projection.py",
        "new-platform/backend/app/medical_grading_policy.py",
        "new-platform/backend/tests/test_medical_method_projection.py",
        "new-platform/backend/tests/test_medical_grading_policy.py",
    })
}


def run(*args):
    return subprocess.run(args, cwd=ROOT, text=True, check=True, capture_output=True).stdout


def validate(task):
    allowed = SCOPES.get(task)
    if not allowed:
        raise ValueError("Unknown or unapproved development task")
    changed = []
    for line in run("git", "status", "--porcelain=v1", "-uall").splitlines():
        if not line:
            continue
        # Fail closed on renamed/copied paths, deletion, submodules, or
        # unexpected porcelain status; this pipeline only accepts edits/adds.
        state, path = line[:2], line[3:]
        if "R" in state or "C" in state or "D" in state or "U" in state or "!" in state:
            raise ValueError("Unsupported Git operation: " + state)
        if path not in allowed:
            raise ValueError("Codex changed unapproved path: " + path)
        if (ROOT / path).is_symlink():
            raise ValueError("Symlink not allowed: " + path)
        changed.append(path)
    if not changed:
        raise ValueError("No approved source changes; no PR will be created")
    return changed


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_continuous_codex_patch.py <task-id>")
    changed = validate(sys.argv[1])
    print("Approved changes: " + ", ".join(changed))


if __name__ == "__main__":
    main()
