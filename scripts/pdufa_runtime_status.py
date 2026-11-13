#!/usr/bin/env python3
"""Read-only installed-code identity and engineering blocker diagnostics.

Startup fingerprints are captured once by the worker, separately from current
disk files. A local authorization receipt records an installer's observations;
it is never, by itself, permission to execute a release or approve science.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import os
import time

REPOSITORY = "pdufa/pdufa-command-center"
INSTALLER = "scripts/windows_pdufa_level6_unblock.ps1"
AUTHORIZATION = "reviewed-release-authorization.json"
SHA1 = re.compile(r"[a-f0-9]{40}\Z")
CORE_FILES = (
    "scripts/pdufa_runtime_status.py", "scripts/pdufa_engineering_review_lanes.py",
    "scripts/pdufa_level_completion.py", "scripts/pdufa_strict_level_runner.py",
    "scripts/level7_model_validation_readiness.py",
    "scripts/level7_source_readiness_inventory.py",
    "automation/scientific-level-completion-queue.json",
)
LEGACY_BLOCKERS = {
    "DOMAIN_SOURCE_COLLECTION_NOT_REVIEWED", "DOMAIN_IMPLEMENTATION_NOT_APPROVED",
    "DOMAIN_REGRESSION_SUITE_NOT_APPROVED", "DOMAIN_IMPLEMENTATION_PR_NOT_AVAILABLE",
}


def read_json(path: Path) -> dict:
    if path.is_symlink():
        raise ValueError("Symlink is not a local status receipt")
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Status receipt must be an object")
    return value


def timestamp(value) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Timestamp must be a string")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Timestamp must have a timezone")
    return stamp


def safe_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str):
        raise ValueError("Unsafe relative release path")
    path = PurePosixPath(relative)
    if ("\\" in relative or ":" in relative
            or path.is_absolute() or str(path) != relative
            or any(part in {"", ".", ".."} for part in path.parts)):
        raise ValueError("Unsafe relative release path")
    target = root / relative
    if any((root / Path(*path.parts[:n])).is_symlink()
           for n in range(1, len(path.parts) + 1)):
        raise ValueError("Symlink in release path")
    return target


def blob_hash(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except (OSError, ValueError):
        return None
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def install_pins(root: Path) -> dict[str, str]:
    body = safe_file(root, INSTALLER).read_text(encoding="utf-8-sig")
    section = re.search(r"\$allowed=@\{(.*?)\n\}", body, re.S)
    paths = re.search(r"\$files=@\((.*?)\n\)", body, re.S)
    if not section or not paths:
        raise ValueError("Installer pin manifest is unavailable")
    pairs = re.findall(r"'([^']+)'='([a-f0-9]{40})'", section[1])
    pins = dict(pairs)
    listed = re.findall(r"'([^']+)'", paths[1])
    if (not pins or len(pins) != len(pairs) or len(listed) != len(set(listed))
            or set(pins) != set(listed)):
        raise ValueError("Installer pin manifest is inconsistent")
    for path in pins:
        safe_file(root, path)
    return pins


def file_hashes(root: Path, paths) -> dict:
    values = {}
    for relative in sorted(paths):
        try:
            values[relative] = blob_hash(safe_file(root, relative))
        except (ValueError, OSError):
            values[relative] = None
    return values


def git_value(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                text=True, timeout=5, check=False)
        return result.stdout.strip() or None if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def capture_runtime(root: Path) -> dict:
    try:
        paths = set(install_pins(root)) | set(CORE_FILES) | {INSTALLER}
    except (ValueError, OSError):
        paths = set(CORE_FILES) | {INSTALLER}
    return {
        "schema_version": 1, "pid": os.getpid(),
        "process_started_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "checkout_branch": git_value(root, "branch", "--show-current"),
        "checkout_commit": git_value(root, "rev-parse", "HEAD"),
        "startup_files": file_hashes(root, paths),
    }


def authorization(root: Path, data: Path) -> dict:
    receipt = read_json(data / AUTHORIZATION)
    files = receipt.get("files")
    pins = install_pins(root)
    if (receipt.get("schema_version") != 1 or receipt.get("repository") != REPOSITORY
            or receipt.get("approved_base") != "main"
            or receipt.get("approval_verified") is not True
            or receipt.get("required_checks_verified") is not True
            or type(receipt.get("approved_pr")) is not int or receipt["approved_pr"] < 1
            or not isinstance(receipt.get("release_commit"), str)
            or not SHA1.fullmatch(receipt["release_commit"])
            or not isinstance(receipt.get("source_main_commit"), str)
            or not SHA1.fullmatch(receipt["source_main_commit"])
            or receipt.get("installer_path") != INSTALLER
            or not isinstance(files, dict) or files != pins
            or not set(CORE_FILES).issubset(files)
            or receipt.get("installer_git_blob_sha1") != blob_hash(safe_file(root, INSTALLER))):
        raise ValueError("Invalid reviewed-release authorization receipt")
    timestamp(receipt.get("authorization_verified_at_utc"))
    return receipt


def runtime_version(snapshot: dict, root: Path, data: Path) -> dict:
    startup = snapshot["startup_files"]
    disk = file_hashes(root, startup)
    changed = sorted(path for path in startup if startup[path] != disk[path])
    status, release, match = "ABSENT", None, False
    try:
        receipt = authorization(root, data)
        expected = {**receipt["files"], INSTALLER: receipt["installer_git_blob_sha1"]}
        match = (not changed and all(startup.get(p) == sha and disk.get(p) == sha
                                    for p, sha in expected.items()))
        status = "FILES_MATCH_LOCAL_AUTHORIZATION" if match else "FILES_MISMATCH"
        release = receipt["release_commit"] if match else None
    except FileNotFoundError:
        pass
    except (ValueError, OSError, KeyError, TypeError):
        status = "INVALID"
    return {**snapshot, "disk_files": disk, "disk_changed_since_start": changed,
            "authorization_status": status, "release_commit": release,
            "files_match_authorization": match,
            "authorization_is_scientific_approval": False,
            "local_receipt_requires_online_release_reverification": True}


def diagnose(state: dict, level: int | None, root: Path, data: Path, runtime: dict) -> dict:
    missing, changed, pin_error = [], [], False
    try:
        pins = install_pins(root)
        hashes = file_hashes(root, set(pins) | set(CORE_FILES))
        missing = sorted(p for p, value in hashes.items() if value is None)
        changed = sorted(p for p, value in hashes.items() if value is not None
                         and p in pins and value != pins[p])
    except (ValueError, OSError):
        pin_error = True
    changed = sorted(set(changed) | set(runtime.get("disk_changed_since_start", [])))
    installed = ("MISSING_INSTALLATION" if missing else
                 "VERSION_MISMATCH" if changed or runtime.get("authorization_status") in
                 {"INVALID", "FILES_MISMATCH"} else
                 "UNVERIFIED_INSTALL_MANIFEST" if pin_error else "INSTALLED_FILES_MATCH")
    levels = state.get("levels", {})
    row = levels.get(str(level), {}) if isinstance(levels, dict) else {}
    steps = row.get("steps", {}) if isinstance(row, dict) else {}
    if not isinstance(steps, dict):
        steps = {}
    codes = sorted({row.get("blocker") for row in steps.values()
                    if isinstance(row, dict) and isinstance(row.get("blocker"), str)})
    source_status = "NOT_CHECKED_FOR_LEVEL"
    if level == 7:
        try:
            prior = read_json(data / "level6/dated-cross-domain-source-gap-inventory.json")
            if prior.get("level") != 6 or prior.get("total") != 32 or prior.get("retrieved") != 32:
                raise ValueError("Incomplete Level6 source inventory")
            source_status = "SOURCE_RECEIPTS_PRESENT_NOT_ADJUDICATED"
        except FileNotFoundError:
            source_status = "SOURCE_EVIDENCE_MISSING"
        except (ValueError, OSError):
            source_status = "SOURCE_EVIDENCE_INVALID"
    tests = steps.get("RUN_REGRESSION_TESTS", {})
    tests = tests if isinstance(tests, dict) else {}
    evidence = tests.get("evidence", {})
    results = evidence.get("tests", []) if isinstance(evidence, dict) else []
    test_status = "NOT_RUN"
    if tests.get("status") == "RUNNING":
        test_status = "RUNNING"
    elif (tests.get("status") in {"BLOCKED", "PENDING"}
          and isinstance(tests.get("blocker"), str)
          and re.search(r"FAILED|FAILURE|ERROR|TIMEOUT|TEST_COUNT_MISMATCH", tests["blocker"])):
        test_status = "REGRESSION_TESTS_FAILED"
    elif tests.get("status") == "DONE":
        test_status = ("PASSED" if isinstance(results, list) and results and all(isinstance(r, dict) and
                       (r.get("passed") is True or type(r.get("passed")) is int
                        and r["passed"] > 0) for r in results) else "REGRESSION_TESTS_FAILED")
    return {
        "installation": {"status": installed, "missing_files": missing,
                         "changed_files": changed},
        "source_evidence": {"status": source_status},
        "tests": {"status": test_status, "verification": "RECORDED_CHECKPOINT_NOT_RERUN"},
        "blocker_codes": codes,
        "legacy_placeholders_require_verified_retry": bool(set(codes) & LEGACY_BLOCKERS),
        "scientific_acceptance": False, "state_modified": False,
    }


def verify_reviewed_release(root: Path, data: Path, run) -> dict:
    """Revalidate release authority online; local receipt flags grant no authority.

    `run` is the worker's bounded, noninteractive command runner. Only GETs and
    read-only git metadata commands are used. Failures never fall back to a
    permissive draft check when a reviewed-install receipt is present.
    """
    try:
        receipt = authorization(root, data)
        expected = {**receipt["files"], INSTALLER: receipt["installer_git_blob_sha1"]}
        if file_hashes(root, expected) != expected:
            raise ValueError("Installed files do not match the release")
        # A start-up gate must finish within the installer's verification window.
        # Each subprocess remains bounded, including an unavailable GitHub host.
        deadline = time.monotonic() + 60
        def execute(argv):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("Release verification deadline exceeded")
            return run(argv, timeout=min(10, remaining))
        def query(argv):
            result = execute(argv)
            if result.returncode:
                raise ValueError("Online release verification failed")
            return json.loads(result.stdout)
        protect = query(["gh", "api", f"repos/{REPOSITORY}/branches/main/protection"])
        if (protect.get("required_pull_request_reviews", {}).get("required_approving_review_count", 0) < 1
                or not protect.get("required_status_checks", {}).get("contexts")):
            raise ValueError("Independent review and required CI are not enforced")
        pr = query(["gh", "pr", "view", str(receipt["approved_pr"]), "--repo", REPOSITORY,
                    "--json", "number,state,isDraft,mergedAt,baseRefName,reviewDecision,mergeCommit"])
        if (pr.get("number") != receipt["approved_pr"] or pr.get("state") != "MERGED"
                or pr.get("isDraft") is not False or not pr.get("mergedAt")
                or pr.get("baseRefName") != "main" or pr.get("reviewDecision") != "APPROVED"
                or pr.get("mergeCommit", {}).get("oid") != receipt["release_commit"]):
            raise ValueError("Release PR is not approved and merged")
        check = execute(["gh", "pr", "checks", str(receipt["approved_pr"]), "--repo", REPOSITORY,
                         "--required"])
        if check.returncode:
            raise ValueError("Required release tests failed")
        comparison = query(["gh", "api", f"repos/{REPOSITORY}/compare/{receipt['release_commit']}...main"])
        if comparison.get("status") not in {"ahead", "identical"}:
            raise ValueError("Release is not an ancestor of main")
        tree = query(["gh", "api", f"repos/{REPOSITORY}/git/trees/{receipt['release_commit']}?recursive=1"])
        if tree.get("truncated") is not False:
            raise ValueError("Incomplete release tree")
        blobs = {item["path"]: item["sha"] for item in tree.get("tree", []) if item.get("type") == "blob"}
        if any(blobs.get(path) != sha for path, sha in expected.items()):
            raise ValueError("Installed file pins differ from approved commit")
        return receipt
    except (ValueError, OSError, KeyError, TypeError, AttributeError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("REVIEWED_RELEASE_AUTHORIZATION_INVALID") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--data-dir", type=Path, default=Path.home() / "PDUFA-Agent-Continuous")
    parser.add_argument("--heartbeat", type=Path)
    args = parser.parse_args()
    root, data = args.root.resolve(), args.data_dir
    inspection = runtime_version(capture_runtime(root), root, data)
    observed = {"status": "HEARTBEAT_MISSING"}
    try:
        heartbeat = read_json(args.heartbeat or data / "heartbeat.json")
        worker = heartbeat.get("runtime_version")
        observed = {"status": "LEGACY_RUNTIME_UNVERIFIED", "runtime_version": worker}
        if isinstance(worker, dict) and worker.get("schema_version") == 1:
            observed["status"] = ("RUNTIME_REPORTED" if
                worker.get("startup_files") == inspection["startup_files"] and
                not worker.get("disk_changed_since_start") else "RUNTIME_VERSION_MISMATCH")
        stamp = timestamp(heartbeat.get("updated_utc"))
        age = (datetime.now(timezone.utc) - stamp).total_seconds()
        if age > 180 or age < -30:
            observed["status"] = "HEARTBEAT_STALE"
        observed["heartbeat_age_seconds"] = round(age, 1)
    except FileNotFoundError:
        heartbeat = {}
    except (ValueError, OSError, KeyError, TypeError):
        heartbeat = {}
        observed = {"status": "INVALID_HEARTBEAT"}
    state_error = None
    try:
        state = read_json(data / "level_completion_ledger.json")
        levels = state.get("levels")
        if not isinstance(levels, dict) or any(
                not isinstance(row, dict) or not isinstance(row.get("steps"), dict)
                or any(not isinstance(step, dict) or not isinstance(step.get("evidence", {}), dict)
                       for step in row["steps"].values()) for row in levels.values()):
            raise ValueError("Invalid ledger shape")
    except FileNotFoundError:
        state, state_error = {}, "LEDGER_MISSING"
    except (ValueError, OSError):
        state, state_error = {}, "LEDGER_INVALID"
    level = heartbeat.get("level", 7)
    diagnostics = diagnose(state, level, root, data, inspection)
    print(json.dumps({"inspection_version": inspection, "observed_worker": observed,
                      "engineering_diagnostics": diagnostics, "ledger_status": state_error or "READ_ONLY",
                      "scientific_acceptance": False, "state_modified": False}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
