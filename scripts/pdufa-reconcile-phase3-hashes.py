#!/usr/bin/env python3
"""Safely reconcile the frozen 741-trial research-pointer manifest with its inputs.

Only two already-observed source-file hashes may change. Company mappings,
trial identities, dates, market-cap records, and evidence qualifications
must remain byte-for-byte equal after canonical JSON encoding.
Never fetch network sources or promote evidence gates.
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

OUTPUT_REL = "new-platform/frontend/public/phase3-census-sources-2026-10-26.json"
EXPECTED_NEW_HASHES = {
    "data/company_registry.csv": "98f5d6ec1c094c7f9be20886f0dd8270e53cb6b1035c28f8ecb988d64b8e7431",
    "config/snapshots/issuer_sources_2026-10-26.json": "d1a835ada0ceeed6599d079b003ffca7a1b0a596a20f6f33917bb3e835c2dde4",
}
EXPECTED_OLD_HASHES = {
    "data/company_registry.csv": "91c2613d43aad5a8054cb4e0f7ef0179b53f8d8ad2e7aa2229c38692288c2498",
    "config/snapshots/issuer_sources_2026-10-26.json": "abdab6f42d91e67047663135a5c0f4a48f4444688324445dca0b689a6d3e1094",
}


def run_git(root: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(root), *args],
                       text=True, encoding="utf-8", capture_output=True)
    if p.returncode:
        raise RuntimeError(f"Git command failed: {' '.join(args)}: {p.stderr}")
    return p.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worktree", type=Path)
    args = parser.parse_args()
    root = args.worktree.resolve(strict=True)
    branch = run_git(root, "branch", "--show-current")
    import re
    if not re.fullmatch(r"integration/level123-\d{8}-\d{6}", branch):
        raise RuntimeError(f"Unexpected branch {branch}; refused to edit.")
    clean = run_git(root, "status", "--porcelain", "--", OUTPUT_REL)
    if clean:
        raise RuntimeError("Manifest has uncommitted edits; refused to overwrite.")

    output = root / OUTPUT_REL
    before = json.loads(output.read_text(encoding="utf-8"))
    script = root / "scripts/build_phase3_census_sources.py"
    spec = importlib.util.spec_from_file_location("pdufa_census_generator", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot open checked-in census generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = root
    module.OUTPUT = output
    after = module.build()

    if before.get("trialCount") != 741 or before.get("companyCount") != 130:
        raise RuntimeError("Saved manifest is not the expected 741 NCT / 130 company cohort.")
    if len(before.get("companies", [])) != 130:
        raise RuntimeError("Saved company listing does not have 130 entries.")
    for key in ("schemaVersion", "scope", "censusAsOf", "trialCount",
                "companyCount", "companies"):
        if before.get(key) != after.get(key):
            raise RuntimeError(f"Source-derived census field changed: {key}. No repair performed.")

    old_inputs = {r["path"]: r["sha256"] for r in before["inputs"]}
    new_inputs = {r["path"]: r["sha256"] for r in after["inputs"]}
    if set(old_inputs) != set(new_inputs) or len(old_inputs) != 4:
        raise RuntimeError("Input source inventory changed; review required.")
    changed = {k for k in old_inputs if old_inputs[k] != new_inputs[k]}
    if not changed:
        print("Census manifest already reconciled; no edits.")
        return
    if changed != set(EXPECTED_NEW_HASHES):
        raise RuntimeError(f"Unexpected changed input(s): {sorted(changed)}")
    for item in changed:
        if old_inputs[item] != EXPECTED_OLD_HASHES[item]:
            raise RuntimeError(f"Original checksum was not recognized: {item}")
        if new_inputs[item] != EXPECTED_NEW_HASHES[item]:
            raise RuntimeError(f"Current source hash differs from inspected test output: {item}")
    if set(before) != set(after):
        raise RuntimeError("Manifest root schema changed; no repair.")
    if [r["path"] for r in before["inputs"]] != [r["path"] for r in after["inputs"]]:
        raise RuntimeError("Input ordering changed; no repair.")

    # Replace only the two checksum strings and leave all other manifest bytes intact.
    current = output.read_text(encoding="utf-8")
    revised = current
    for item in changed:
        old = EXPECTED_OLD_HASHES[item]
        new = EXPECTED_NEW_HASHES[item]
        if revised.count(old) != 1:
            raise RuntimeError(f"Expected checksum not unique in saved manifest: {item}")
        revised = revised.replace(old, new)
    if json.loads(revised) != after:
        raise RuntimeError("Only two hash replacements were insufficient; no repair.")

    output.write_text(revised, encoding="utf-8", newline="\n")
    try:
        verify = json.loads(output.read_text(encoding="utf-8"))
        if verify != after:
            raise RuntimeError("Post-write manifest validation failed")
        print("RECONCILED: 741 exact NCTs, 130 companies, zero changed company records.")
        print("Two input hashes updated; all trial classifications and source pointers preserved.")
        print("No network, no scores, no source promotion, no deployment.")
        print(f"Modified only: {OUTPUT_REL}")
    except Exception:
        output.write_text(current, encoding="utf-8", newline="\n")
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        sys.exit(1)
