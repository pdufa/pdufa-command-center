#!/usr/bin/env python3
"""Repair Windows CRLF portability for the 741-trial census tests.

No input files, research data, trial mappings, or saved SHA256 manifest are changed.
The patch converts CRLF to LF only in memory when the generator/tests hash text.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

GENERATOR = "scripts/build_phase3_census_sources.py"
TEST = "new-platform/frontend/tests/phase3-census-sources.test.cjs"
MANIFEST = "new-platform/frontend/public/phase3-census-sources-2026-10-26.json"
CANONICAL = {
    "data/company_registry.csv": "91c2613d43aad5a8054cb4e0f7ef0179b53f8d8ad2e7aa2229c38692288c2498",
    "config/snapshots/issuer_sources_2026-10-26.json": "abdab6f42d91e67047663135a5c0f4a48f4444688324445dca0b689a6d3e1094",
}
OLD_BUILDER = 'raw = {name: (ROOT / name).read_bytes() for name in INPUTS}'
NEW_BUILDER = 'raw = {name: (ROOT / name).read_bytes() for name in INPUTS}\n    for name in ("data/company_registry.csv", "config/snapshots/issuer_sources_2026-10-26.json"):\n        raw[name] = raw[name].replace(b"\\r\\n", b"\\n")'
OLD_TEST = 'crypto.createHash("sha256").update(fs.readFileSync(path.join(root,item.path))).digest("hex")'
NEW_TEST = 'crypto.createHash("sha256").update(["data/company_registry.csv","config/snapshots/issuer_sources_2026-10-26.json"].includes(item.path) ? Buffer.from(fs.readFileSync(path.join(root,item.path),"utf8").replace(/\\r\\n/g,"\\n"),"utf8") : fs.readFileSync(path.join(root,item.path))).digest("hex")'


def cmd(*args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8")


def replace_once(content, old, new, label):
    if content.count(old) == 1 and new not in content:
        return content.replace(old, new)
    if old not in content and content.count(new) == 1:
        return content
    raise RuntimeError(f"Unexpected {label} layout; no changes made.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worktree", type=Path)
    args = parser.parse_args()
    root = args.worktree.resolve(strict=True)
    result = cmd("git", "-C", str(root), "branch", "--show-current")
    if result.returncode or not re.fullmatch(
        r"integration/level123-\d{8}-\d{6}", result.stdout.strip()
    ):
        raise RuntimeError("Refusing changes outside local Level 1-3 integration branch.")

    result = cmd("git", "-C", str(root), "status", "--porcelain",
                 "--", GENERATOR, TEST, MANIFEST)
    if result.returncode or result.stdout.strip():
        raise RuntimeError("One of the repair targets or the manifest is already modified.")

    manifest_path = root / MANIFEST
    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    original_manifest = manifest_path.read_bytes()
    if saved.get("trialCount") != 741 or saved.get("companyCount") != 130:
        raise RuntimeError("Not the expected source inventory.")
    expected = {x["path"]: x["sha256"] for x in saved["inputs"]}
    for path, digest in CANONICAL.items():
        if expected.get(path) != digest:
            raise RuntimeError(f"Saved manifest hash changed unexpectedly: {path}")
        raw = (root / path).read_bytes()
        canonical = raw.replace(b"\r\n", b"\n")
        if hashlib.sha256(canonical).hexdigest() != digest:
            raise RuntimeError(f"Content differs beyond line endings: {path}")
    generator_path = root / GENERATOR
    test_path = root / TEST
    old_generator = generator_path.read_bytes()
    old_test = test_path.read_bytes()
    new_generator = replace_once(old_generator.decode("utf-8"), OLD_BUILDER,
                                 NEW_BUILDER, GENERATOR)
    new_test = replace_once(old_test.decode("utf-8"), OLD_TEST,
                            NEW_TEST, TEST)
    try:
        generator_path.write_bytes(new_generator.encode("utf-8"))
        test_path.write_bytes(new_test.encode("utf-8"))
        result = cmd(sys.executable, str(generator_path), "--check")
        if result.returncode:
            raise RuntimeError(f"Reproducibility check failed: {result.stderr or result.stdout}")
        if manifest_path.read_bytes() != original_manifest:
            raise RuntimeError("Saved research manifest unexpectedly changed")
        print(result.stdout.strip())
        print("WINDOWS CRLF PORTABILITY FIX PASSED: original research hashes preserved.")
        print("Only Python generator and frontend test files changed; no source data changed.")
    except Exception:
        generator_path.write_bytes(old_generator)
        test_path.write_bytes(old_test)
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        sys.exit(1)
