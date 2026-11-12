#!/usr/bin/env python3
"""Predictive preflight inventory across PDUFA engineering Levels 4-20.

Identifies predictable installation/development blockers *before* running a
level. Static GitHub checks cannot prove the state of a private Windows host,
clinical source availability, model calibration, or independent review.
No repairs or scientific predictions are performed by this script.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from typing import Any

LEVEL_FILES = {
    4: ("scripts/level4_scientific_evidence.py", "tests/test_level4_scientific_evidence.py"),
    5: ("scripts/level5_contradictory_evidence.py", "tests/test_level5_contradictory_evidence.py"),
    6: ("scripts/level6_cross_disciplinary_inventory.py", "tests/test_level6_cross_disciplinary_inventory.py"),
    7: ("scripts/level7_model_validation_readiness.py",
        "tests/test_level7_model_validation_readiness.py",
        "scripts/level7_source_readiness_inventory.py",
        "tests/test_level7_source_readiness_inventory.py"),
}
SHARED_PATHS = (
    "AGENTS.md",
    "automation/scientific-level-completion-queue.json",
    "scripts/pdufa_level_completion.py",
    "scripts/pdufa_engineering_review_lanes.py",
    "scripts/pdufa_strict_level_runner.py",
    "scripts/audit_raas_retirement.py",
    "scripts/windows_local_agent_watchdog.ps1",
    "scripts/windows_pdufa_level6_unblock.ps1",
)
REQUIRED_INTEGRATION = {
    6: "tests/test_level6_implementation_integration.py",
    7: "tests/test_level7_implementation_integration.py",
}
REQUIRED_EVIDENCE_KEYS = (
    "exact_application_trial_identity_and_phase",
    "original_source_receipts_with_access_dates_and_sha256",
    "documented_phase_appropriate_evidence_for_required_fields",
    "domain_functionality_implemented_and_regression_tests_pass",
    "independent_scientific_and_code_review_approved",
    "no_unblinded_historical_data_leakage",
    "approved_integrated_acceptance_evidence",
)


def issue(code: str, *, classification: str, details: str) -> dict:
    return {"code": code, "classification": classification, "details": details}


def inspect_installer(root: Path) -> list[dict]:
    """Verify source files in the exact reviewed installer pin-map are unchanged."""
    problems = []
    script = root / "scripts/windows_pdufa_level6_unblock.ps1"
    if not script.is_file():
        return [issue("WINDOWS_INSTALLER_MISSING", classification="KNOWN_BLOCK",
                      details="Cannot prepare reviewed Windows release")]
    body = script.read_text(encoding="utf-8")
    files_match = re.search(r"\$files=@\((.*?)\n\)", body, re.S)
    pins_match = re.search(r"\$allowed=@\{(.*?)\n\}", body, re.S)
    if not files_match or not pins_match:
        return [issue("INSTALLER_PIN_MANIFEST_UNREADABLE", classification="KNOWN_BLOCK",
                      details="No exact bounded release manifest")]
    paths = set(re.findall(r"'([^']+)'", files_match.group(1)))
    blobs = dict(re.findall(r"'([^']+)'='([0-9a-f]{40})'", pins_match.group(1)))
    if paths != set(blobs):
        problems.append(issue("INSTALLER_PIN_LIST_MISMATCH", classification="KNOWN_BLOCK",
                              details="Install paths differ from Git blob allowlist"))
    for path, expected in sorted(blobs.items()):
        dest = root / path
        if not dest.is_file():
            problems.append(issue("PINNED_INSTALL_FILE_MISSING", classification="KNOWN_BLOCK",
                                  details=path))
            continue
        actual = subprocess.run(["git", "hash-object", str(dest)],
                                capture_output=True, text=True, check=False)
        if actual.returncode != 0:
            problems.append(issue("GIT_HASH_OBJECT_FAILED", classification="KNOWN_BLOCK",
                                  details=path))
        elif actual.stdout.strip() != expected:
            problems.append(issue("INSTALL_SOURCE_PIN_DRIFT", classification="KNOWN_BLOCK",
                                  details=path))
    for label in ("[switch]$Preflight", "PDUFA_INSTALL_PREFLIGHT_PASS",
                  "$canRestore=$true", "$startRequestedUtc=", "AssertOwner",
                  "LEVEL6_PR_NO_LONGER_APPROVED_DRAFT"):
        if label not in body:
            problems.append(issue("MISSING_SAFE_INSTALLATION_GATE",
                                  classification="KNOWN_BLOCK", details=label))
    return problems


def audit(manifest: dict, root: Path) -> dict:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("Unapproved manifest schema")
    levels = manifest.get("levels")
    safety = manifest.get("safety")
    if (not isinstance(levels, list) or len(levels) != 17
            or [x.get("level") if isinstance(x, dict) else None for x in levels]
            != list(range(4, 21))
            or not isinstance(safety, dict)
            or not safety or any(v is not False for v in safety.values())):
        raise ValueError("Unapproved level sequence or safety gate")
    shared = []
    for path in SHARED_PATHS:
        if not (root / path).is_file():
            shared.append(issue("SHARED_FILE_MISSING", classification="KNOWN_BLOCK",
                                details=path))
    shared.extend(inspect_installer(root))
    # Runtime checks must not be faked by a GitHub runner or a local code scan.
    for item in ("Windows Task Scheduler owner and idle-state verification",
                 "PowerShell execution policy / Python 3.13 / Git and gh authentication",
                 "ClinicalTrials.gov and GitHub connectivity from the actual Windows host",
                 "disk writes and atomic source backups on the actual Windows host",
                 "post-restart heartbeat and genuine phase-appropriate source retrieval"):
        shared.append(issue("HOST_RUNTIME_PREFLIGHT_REQUIRED",
                            classification="HOST_CHECK_REQUIRED", details=item))
    rows = []
    known_future_unimplemented = []
    for row in levels:
        n = row["level"]
        if (not isinstance(row.get("required_evidence_fields"), list)
                or not row["required_evidence_fields"]
                or not isinstance(row.get("scientific_acceptance_criteria"), list)
                or not set(REQUIRED_EVIDENCE_KEYS).issubset(
                    row["scientific_acceptance_criteria"])
                or row.get("completed_scientific_level") is not False):
            raise ValueError(f"Unsafe or incomplete scientific acceptance for level {n}")
        findings = []
        pr = row.get("implementation_draft_pr")
        if pr is None:
            findings.append(issue("DOMAIN_IMPLEMENTATION_NOT_APPROVED",
                                  classification="KNOWN_FUTURE_DEVELOPMENT_GAP",
                                  details="Missing approved stage-specific domain code and draft PR"))
            known_future_unimplemented.append(n)
        elif not isinstance(pr, int) or pr <= 0:
            raise ValueError(f"Invalid implementation PR for level {n}")
        expected = LEVEL_FILES.get(n)
        if expected:
            for path in expected:
                if not (root / path).is_file():
                    findings.append(issue("REQUIRED_DOMAIN_FILE_MISSING",
                                          classification="KNOWN_BLOCK", details=path))
        elif pr is not None:
            findings.append(issue("APPROVED_DOMAIN_FILE_MAPPING_MISSING",
                                  classification="KNOWN_BLOCK",
                                  details="Cannot validate approved module and tests"))
        integration = REQUIRED_INTEGRATION.get(n)
        if integration and not (root / integration).is_file():
            findings.append(issue("INTEGRATION_TEST_MISSING",
                                  classification="KNOWN_BLOCK", details=integration))
        if n == 7:
            if (root / "scripts/level7_model_validation_readiness.py").is_file():
                findings.append(issue(
                    "PREPARATORY_ONLY_NOT_APPROVED_FOR_ENGINEERING_ADVANCEMENT",
                    classification="CONTEXT",
                    details="Draft readiness checks are not a validated model"))
            else:
                findings.append(issue(
                    "LEVEL7_PREPARATORY_MODULE_NOT_INSTALLED",
                    classification="KNOWN_FUTURE_DEVELOPMENT_GAP",
                    details="Level 7 preparation is absent from this installation; "
                            "it is not an approved domain implementation in either case"))
        rows.append({
            "level": n, "name": row["name"],
            "required_phase_appropriate_evidence": row["required_evidence_fields"],
            "implementation_pr_registered": pr,
            "engineering_release_ready": bool(pr) and not findings,
            "scientific_level_complete": False,
            "predictable_findings": findings,
            "external_source_adjudication": "NOT_VERIFIED_BY_STATIC_PREFLIGHT",
            "actual_pc_installation": "NOT_VERIFIED_BY_STATIC_PREFLIGHT",
        })
    return {
        "status": "STATIC_PREDICTIVE_PREFLIGHT_NOT_WINDOWS_HOST_CERTIFICATION",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "levels": rows,
        "future_levels_with_missing_approved_domain_implementation": known_future_unimplemented,
        "shared_installation_findings": shared,
        "known_shared_installation_blockers": sum(
            x["classification"] == "KNOWN_BLOCK" for x in shared),
        "all_future_levels_implementation_ready": not known_future_unimplemented,
        "windows_restart_confirmed": False,
        "scientific_reviews_automatically_completed": False,
        "automatic_merges_or_deployments": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = json.loads((root / "automation/scientific-level-completion-queue.json")
                          .read_text(encoding="utf-8"))
    result = audit(manifest, root)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 1 if result["known_shared_installation_blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
