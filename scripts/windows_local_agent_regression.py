#!/usr/bin/env python3
"""Read-only Level 1 regression gate for the Windows local PDUFA agent.

Uses Python's standard-library unittest only. This script runs audited,
synthetic-data safety tests; no model-generated source, evidence, predictions,
or production application code is executed or modified by this runner.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPORTS = Path.home() / "PDUFA-Agent-Reports"

SUITES = (
    ("provenance", "test_stage4_evidence_provenance.py", 9),
    ("science40_integration", "test_level1_science40_integration.py", 3),
    ("level2_phase_first_triage", "test_stage4_phase_first_triage.py", 5),
    ("level2_hypothesis_intake", "test_level2_scientific_hypothesis_intake.py", 10),
    ("patch_generator_safety", "test_windows_local_patch_proposal.py", 4),
    ("patch_reviewer_safety", "test_windows_local_patch_review.py", 8),
)


def run_command(args: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True,
        errors="replace", timeout=timeout,
    )


def main() -> int:
    print("Running read-only PDUFA Level 1 regression gate")
    results: dict[str, dict[str, object]] = {}
    try:
        audit = run_command(
            [sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
            timeout=240,
        )
        audit_ok = audit.returncode == 0
        print("Retirement safety audit:", "PASS" if audit_ok else "FAILED")
        results["retirement_audit"] = {"passed": audit_ok}
        # Fail closed: no further tests or AI job success with failed policy gate.
        if audit_ok:
            for key, pattern, minimum in SUITES:
                proc = run_command([
                    sys.executable, "-B", "-m", "unittest", "discover",
                    "-s", "tests", "-p", pattern, "-v",
                ], timeout=150)
                output = proc.stdout + "\n" + proc.stderr
                match = re.search(r"Ran\s+(\d+)\s+tests?\s+in\s+", output)
                count = int(match.group(1)) if match else 0
                passed = proc.returncode == 0 and count >= minimum
                results[key] = {"passed": passed, "tests_run": count}
                print(
                    f"{key}: {'PASS' if passed else 'FAILED'} "
                    f"({count} tests, required at least {minimum})"
                )
        else:
            print("STOP: Audit failed. Regression suites skipped.")
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("STOP: Regression gate unavailable:", type(exc).__name__)
        results["runner_error"] = {"passed": False, "kind": type(exc).__name__}

    passed = (
        results.get("retirement_audit", {}).get("passed") is True
        and all(results.get(key, {}).get("passed") is True for key, _, _ in SUITES)
    )
    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = REPORTS / f"level1-regression-status-{stamp}.json"
    data = {
        "timestamp_utc": stamp,
        "state": "PASS" if passed else "FAILED",
        "production_modified": False,
        "scientific_result_claimed": False,
        "regression_results": results,
    }
    with target.open("x", encoding="utf-8", newline="\n") as report:
        json.dump(data, report, indent=2)
        report.write("\n")
    print("Local regression report:", target)
    print("No production changes or completed scientific-level claims")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
