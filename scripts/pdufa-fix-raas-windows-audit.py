#!/usr/bin/env python3
"""Safely repair the RAAS archival audit for Windows CRLF checkouts.

Changes only the audit logic, never archived records or pinned hashes.
Rejects any historical file whose contents differ for reasons other than
the Windows Git LF -> CRLF transformation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

AUDIT = "scripts/audit_raas_retirement.py"
MANIFEST = "archives/raas/read-only-record-manifest.json"
OLD = """                elif hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
                    add('HISTORICAL_RECORD_MODIFIED', path, 'Pinned read-only historical record differs from its preserved baseline.')"""
NEW = r"""                else:
                    raw = path.read_bytes()
                    checksum_matches = hashlib.sha256(raw).hexdigest() == record['sha256']
                    # Git for Windows may expand canonical LF into checkout CRLF.
                    # Accept only that exact EOL transformation and only on Windows;
                    # the pinned manifest and all other content remain immutable.
                    windows_eol_only = (os.name == 'nt' and b'\r\n' in raw and
                                        hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest() == record['sha256'])
                    if not (checksum_matches or windows_eol_only):
                        add('HISTORICAL_RECORD_MODIFIED', path, 'Pinned read-only historical record differs from its preserved baseline.')"""


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args],
                            text=True, encoding="utf-8", capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Git {args[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worktree", type=Path)
    args = parser.parse_args()
    root = args.worktree.resolve(strict=True)
    branch = git(root, "branch", "--show-current")
    if not re.fullmatch(r"integration/level123-\d{8}-\d{6}", branch):
        raise RuntimeError(f"Expected the dedicated Level 1-3 integration branch; got {branch}")
    if git(root, "status", "--porcelain", "--", AUDIT):
        raise RuntimeError("Audit source has uncommitted changes; refused to overwrite.")

    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    records = manifest.get("files")
    if manifest.get("schemaVersion") != 1 or not isinstance(records, list) or len(records) != 104:
        raise RuntimeError("Unexpected pinned history manifest; refused to change the audit.")
    raw_matches = 0
    windows_only_matches = 0
    unexplained = []
    for entry in records:
        item = root / entry["path"]
        if not item.is_file():
            unexplained.append(entry["path"] + " (missing)")
            continue
        raw = item.read_bytes()
        expected = entry["sha256"]
        if hashlib.sha256(raw).hexdigest() == expected:
            raw_matches += 1
        elif b"\r\n" in raw and hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == expected:
            windows_only_matches += 1
        else:
            unexplained.append(entry["path"])
    if unexplained:
        raise RuntimeError(
            "Pinned historical records have non-line-ending differences: "
            + ", ".join(unexplained[:5])
            + f" (total {len(unexplained)}). Nothing changed."
        )
    if raw_matches + windows_only_matches != 104:
        raise RuntimeError("Pinned history count mismatch.")
    if windows_only_matches == 0:
        print("No Windows CRLF-only archive differences detected.")

    audit_path = root / AUDIT
    original = audit_path.read_bytes()
    before = original.decode("utf-8")
    newline = "\r\n" if b"\r\n" in original else "\n"
    normalized = before.replace("\r\n", "\n")
    if normalized.count(OLD) != 1:
        if normalized.count(NEW) == 1:
            print("The RAAS source fix is already present.")
            changed = False
        else:
            raise RuntimeError("Unexpected audit source. Refused to patch any file.")
    else:
        changed = True
        patched = normalized.replace(OLD, NEW).replace("\n", newline)
        audit_path.write_bytes(patched.encode("utf-8"))

    try:
        completed = subprocess.run(
            [sys.executable, "-X", "utf8", str(audit_path), "--check"],
            cwd=root, text=True, encoding="utf-8", capture_output=True
        )
        try:
            report = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Audit did not produce valid JSON: "
                + (completed.stderr or completed.stdout)[-500:]
            ) from exc
        failures = report.get("violations", [])
        if (completed.returncode != 0 or report.get("passed") is not True
                or report.get("activeDependenciesRemaining") != 0
                or failures or report.get("historicalPinnedRecordFileCount") != 104):
            samples = ", ".join(
                f"{x.get('kind')}:{x.get('path')}" for x in failures[:5]
            )
            raise RuntimeError(
                f"RAAS audit still failed ({len(failures)} violations): {samples}"
            )
        if changed:
            # --only stages and commits this exact tracked file and nothing else.
            git(root, "-c", "user.name=PDUFA local integration",
                "-c", "user.email=pdufa-integration@localhost",
                "commit", "--only", "-m",
                "Handle Windows CRLF historical archives without weakening RAAS retirement",
                "--", AUDIT)
        print(f"PINNED ARCHIVE VERIFIED: {raw_matches} exact, "
              f"{windows_only_matches} Windows CRLF-only; 104 total.")
        print("RAAS RETIREMENT AUDIT PASSED: 0 active dependencies, 0 violations.")
        print("Only the audit source was updated; historical files and manifests untouched.")
        print("No GitHub push, production merge, deployment, scans, scores or trading.")
    except Exception:
        if changed:
            audit_path.write_bytes(original)
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        sys.exit(1)
