#!/usr/bin/env python3
"""Bounded, free-tier coding proposal worker. Never deploys or merges."""
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
TASK = ROOT / "automation" / "coding-task.md"
API = "https://api.groq.com/openai/v1/chat/completions"
ALLOWED = ("tests/", "docs/", "scripts/")
FORBIDDEN = (".github/", "data/", "research/", "archives/", "config/")

def run(*args):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)

def main():
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        print("SKIPPED: GROQ_API_KEY is not configured; no API request made.")
        return 0
    task = TASK.read_text(encoding="utf-8")
    policy = (ROOT / "AGENTS.md").read_text(encoding="utf-8")[:18000]
    prompt = (
        "You are a cautious maintenance coding agent. Follow repository policy. "
        "Return ONLY a valid unified git diff with a/ and b/ paths, no markdown. "
        "Only edit existing files under tests/, docs/, or scripts/. "
        "Never modify production logic, workflows, secrets, data, model weights, "
        "POOL/FOCUS membership, predictions, or archived evidence. "
        "If no safe change is possible, return NO_CHANGE. "
        "Make one small, testable improvement.\n\nPOLICY:\n" + policy +
        "\n\nTASK:\n" + task
    )
    body = json.dumps({
        "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0, "max_tokens": 4096,
    }).encode()
    request = urllib.request.Request(API, data=body, headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            answer = json.load(response)["choices"][0]["message"]["content"].strip()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        print("API unavailable or free-tier limit reached; no changes:", type(exc).__name__)
        return 0
    if answer == "NO_CHANGE" or not answer.startswith("diff --git "):
        print("No usable diff returned; no changes.")
        return 0
    import re
    paths = re.findall(r"^diff --git a/(\S+) b/(\S+)$", answer, re.M)
    if not paths or len(paths) > 3 or any(
        a != b or not a.startswith(ALLOWED) or a.startswith(FORBIDDEN)
        or ".." in pathlib.PurePosixPath(a).parts or not (ROOT / a).is_file()
        for a, b in paths
    ):
        print("Rejected patch: invalid or restricted file paths.")
        return 0
    patch = ROOT / ".agent-proposal.patch"
    patch.write_text(answer + "\n", encoding="utf-8")
    try:
        check = run("git", "apply", "--check", str(patch))
        if check.returncode:
            print("Patch does not apply; no changes.")
            return 0
        applied = run("git", "apply", str(patch))
        if applied.returncode:
            print("Patch application failed.")
            return 1
        checks = [
            ("python", "-m", "compileall", "-q", "scripts", "tests"),
            ("python", "scripts/audit_raas_retirement.py", "--check"),
            ("python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_focus_registry_fetch.py"),
        ]
        for command in checks:
            result = run(*command)
            print("CHECK", " ".join(command), result.returncode)
            if result.returncode:
                print(result.stdout[-1500:], result.stderr[-1500:])
                run("git", "reset", "--hard", "HEAD")
                return 0
        print("Safe proposal passed validation.")
        return 0
    finally:
        patch.unlink(missing_ok=True)

if __name__ == "__main__":
    sys.exit(main())
