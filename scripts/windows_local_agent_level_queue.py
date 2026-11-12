#!/usr/bin/env python3
"""Generate a *planning-only* engineering task from the 20-level queue.

Never executes generated text, edits the repo, changes assessments, opens PRs,
or deploys. Does not infer that any level is incomplete or complete.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "automation/scientific-20-level-development-queue.json"
REPORTS = Path.home() / "PDUFA-Agent-Reports"
OLLAMA = "http://127.0.0.1:11434/api/generate"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", type=int, default=1,
                        help="One of the owner-established scientific levels 1–20")
    args = parser.parse_args()
    if not 1 <= args.level <= 20:
        print("STOP: Level must be 1 through 20")
        return 2
    manifest = json.loads(QUEUE.read_text(encoding="utf-8"))
    levels = manifest["levels"]
    if len(levels) != 20 or [i["level"] for i in levels] != list(range(1, 21)):
        print("STOP: Invalid or incomplete 20-level manifest")
        return 2

    check = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_raas_retirement.py"), "--check"],
        cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=240
    )
    if check.returncode:
        print("STOP: Mandatory RAAS retirement guard failed")
        return 2
    task = levels[args.level - 1]
    name = task["name"]
    print(f"PASS: Retirement guard. Preparing Level {args.level}: {name}")

    prompt = (
        "You are preparing an ENGINEERING PLAN only for the owner-established "
        "PDUFA scientific assessment system. You cannot access the real project "
        "implementation in this prompt: do not claim any level is implemented, "
        "tested, or complete. Preserve past progress. Retired RAAS cannot be "
        "reactivated. Use exact NCT and application-cycle provenance, phase-"
        "appropriate evidence, missing-vs-nonpublic distinction, chronological "
        "outcome-blind evaluation, and immutable version history. No fabricated "
        "scientific observations, approval probabilities, or results. "
        "Write at most five numbered next engineering actions: (1) inspect "
        "existing code/test coverage, (2) identify reusable implementations, "
        "(3) propose one small isolated code/test change, (4) name exact "
        "regression/safety checks, (5) specify review gate. Do not propose "
        "editing or executing archived RAAS. Keep this review-only.\n"
        f"LEVEL {args.level}: {name}\n"
        "Existing implementation status: NOT AUDITED.\n"
    )
    request = urllib.request.Request(
        OLLAMA, data=json.dumps({
            "model": "qwen2.5-coder:1.5b", "prompt": prompt,
            "stream": False, "options": {"num_predict": 500, "temperature": 0.1}
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=360) as resp:
            answer = json.load(resp).get("response")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print("STOP: Ollama planning request failed:", exc)
        return 1
    if not isinstance(answer, str) or not answer.strip():
        print("STOP: No local planning output")
        return 1

    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORTS / f"level-{args.level:02d}-plan-{stamp}.md"
    with path.open("x", encoding="utf-8", newline="\n") as file:
        file.write(f"# Level {args.level}: {name}\n\n")
        file.write("**UNVERIFIED PLANNING DRAFT — NOT CODE, NOT SCIENTIFIC EVIDENCE, NOT COMPLETION**\n\n")
        file.write(answer.strip() + "\n")
    print(f"PASS: Review-only level plan saved: {path}")
    print("No code or predictions changed; no completion status advanced.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("STOP:", exc)
        raise SystemExit(1)
