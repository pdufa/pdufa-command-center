#!/usr/bin/env python3
"""Read-only inventory of existing PDUFA implementation for one scientific level.

Reports *possible* relevant active source and tests, never asserts implementation,
scientific correctness, or completion. No files inside the checkout are changed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "automation/scientific-20-level-development-queue.json"
REPORTS = Path.home() / "PDUFA-Agent-Reports"
ALLOWED = {".py", ".ts", ".tsx", ".js", ".jsx", ".md"}
SKIP_DIRS = {
    ".git", ".next", "node_modules", "__pycache__", "archives", "data",
    "reports", "research", "dist", "build", "cache", ".venv",
}
SCAN_FOLDERS = [
    "new-platform/frontend/app", "new-platform/frontend/lib",
    "new-platform/frontend/components", "new-platform/backend",
    "scripts", "tests",
]
KEYWORDS = {
    1: ["document", "extract", "source", "provenance", "citation", "nct", "evidence"],
    2: ["hypothesis", "mechanism", "rationale", "indication", "biological"],
    3: ["biology", "pathway", "target", "mechanism", "biomarker"],
    4: ["statistic", "endpoint", "validation", "randomiz", "reproduc"],
    5: ["contradict", "conflict", "negative", "challenge", "uncertain"],
    6: ["integrat", "pharmacology", "clinical", "discipline", "regulatory"],
    7: ["predict", "uncertainty", "calibrat", "scenario", "confidence"],
    8: ["synthesis", "benefit", "risk", "judgment", "evidence"],
    9: ["causal", "counterfactual", "confound", "assumption"],
    10: ["systems", "computational", "pathway", "simulation"],
    11: ["adversarial", "challenge", "robustness", "falsif"],
    12: ["adjudicat", "model", "disagree", "ensemble"],
    13: ["pharmacokinetic", "pharmacodynamic", "pkpd", "dose", "exposure"],
    14: ["subgroup", "heterogen", "biomarker", "patient", "responder"],
    15: ["bayes", "posterior", "prior", "uncertainty"],
    16: ["external", "generaliz", "real-world", "population"],
    17: ["historical", "precedent", "failure", "comparab"],
    18: ["regulatory", "counterfactual", "fda", "pathway"],
    19: ["reproduc", "audit", "calculation", "consistency"],
    20: ["red-team", "adversarial", "independent", "challenge", "adjudicat"],
}


def candidates(level: int) -> tuple[list[dict], Counter]:
    found = []
    counts = Counter()
    scanned = 0
    for folder in SCAN_FOLDERS:
        base = ROOT / folder
        if not base.is_dir():
            continue
        for folder_path, child_dirs, filenames in os.walk(base, followlinks=False):
            child_dirs[:] = sorted(
                name for name in child_dirs
                if name.lower() not in SKIP_DIRS
                and "raas" not in name.lower()
                and not (Path(folder_path) / name).is_symlink()
            )
            for filename in sorted(filenames):
                path = Path(folder_path) / filename
                if path.is_symlink() or not path.is_file() or path.suffix.lower() not in ALLOWED:
                    continue
                if "raas" in filename.lower() or not path.resolve().is_relative_to(ROOT.resolve()):
                    continue
                rel = path.relative_to(ROOT).as_posix()
                try:
                    if path.stat().st_size > 250_000:
                        continue
                    body = path.read_text(encoding="utf-8", errors="replace").lower()
                except OSError:
                    continue
                scanned += 1
                basename = filename.lower()
                hits = [word for word in KEYWORDS[level] if word in body or word in basename]
                if len(hits) < 2:
                    continue
                is_test = (
                    "tests" in path.parts or basename.startswith("test_")
                    or basename.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
                )
                role = "test_candidate" if is_test else "source_candidate"
                score = len(hits) + 2 * sum(word in basename for word in hits)
                found.append({
                    "path": rel, "role": role, "matched_topics": hits,
                    "relevance_score": score,
                })
                counts[role] += 1
    found.sort(key=lambda item: (-item["relevance_score"], item["path"]))
    return found, Counter(counts, files_scanned=scanned)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", type=int, default=1)
    args = parser.parse_args()
    if args.level not in KEYWORDS:
        print("STOP: level must be from 1 through 20")
        return 2
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    levels = queue.get("levels")
    if not isinstance(levels, list) or len(levels) != 20:
        print("STOP: unexpected 20-level queue")
        return 2
    item = levels[args.level-1]
    if item.get("level") != args.level:
        print("STOP: queue level mismatch")
        return 2
    check = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audit_raas_retirement.py"), "--check"],
        cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=240
    )
    if check.returncode:
        print("STOP: Mandatory retirement safety audit failed")
        return 2
    found, counts = candidates(args.level)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    REPORTS.mkdir(parents=True, exist_ok=True)
    target = REPORTS / f"level-{args.level:02d}-code-inventory-{stamp}.json"
    report = {
        "timestamp_utc": stamp,
        "level": args.level,
        "name": item["name"],
        "status": "CANDIDATES_IDENTIFIED_NOT_VERIFIED",
        "already_implemented": "UNKNOWN",
        "safety_audit": "PASS",
        "production_modified": False,
        "files_scanned": counts["files_scanned"],
        "source_candidate_count": counts["source_candidate"],
        "test_candidate_count": counts["test_candidate"],
        "top_candidates": found[:30],
        "next_action": "Human inspect the candidates, run appropriate tests, then prepare a bounded review PR.",
    }
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: Level {args.level} - {item['name']}")
    print(f"Active files scanned: {counts['files_scanned']}")
    print(f"Possible source files: {counts['source_candidate']}")
    print(f"Possible test files: {counts['test_candidate']}")
    print(f"Local report: {target}")
    for f in found[:8]:
        print(f"  {f['role']}: {f['path']}")
    print("These are keyword matches only, NOT proof of completed levels.")
    print("No repository files, research data, or production predictions changed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print("STOP:", exc)
        raise SystemExit(1)
