#!/usr/bin/env python3
"""Read-only PDUFA #2/#3/#4 scan input inventory and baseline readiness preflight.

This script does NOT contact remote sources, perform scans or certify current
FDA/SEC/clinical/market evidence. It inventories existing local snapshots,
calculates reproducible source fingerprints, and outputs a truthful report for
building the baseline-first collector orchestrator.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "scan_234.json"


def file_audit(path: Path) -> dict:
    if not path.is_file():
        return {"state": "MISSING", "records": 0, "sha256": "", "columns": []}
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                return {"state": "INVALID", "records": 0, "sha256": digest.hexdigest(),
                        "columns": [], "issue": "No header row"}
            records = sum(1 for _ in reader)
            return {
                "state": "PRESENT_UNVERIFIED",
                "records": records,
                "sha256": digest.hexdigest(),
                "columns": reader.fieldnames,
                "note": "File checksum does not verify whether its external source is current.",
            }
    except (OSError, UnicodeError, csv.Error) as exc:
        return {"state": "INVALID", "records": 0, "sha256": "",
                "columns": [], "issue": type(exc).__name__ + ": " + str(exc)[:200]}


def build_report(root: Path = ROOT, config_path: Path | None = None) -> dict:
    root = Path(root)
    config_path = config_path or root / "config" / "scan_234.json"
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    tabs = config["tabs"]
    if [tab["id"] for tab in tabs] != [2, 3, 4]:
        raise ValueError("Expected exactly the ordered #2, #3, #4 scan scopes")
    source_files = set()
    for tab in tabs:
        source_files.update(tab["source_files"])
    for location in config["universe_sources"]:
        source_files.add(Path(location).name)
    files = {filename: file_audit(root / "data" / filename)
             for filename in sorted(source_files)}
    tabs_report = []
    for tab in tabs:
        needed = tab["source_files"]
        missing = [name for name in needed if files[name]["state"] != "PRESENT_UNVERIFIED"]
        tabs_report.append({
            "id": tab["id"],
            "name": tab["name"],
            "configured_sources": len(needed),
            "available_saved_sources": len(needed) - len(missing),
            "missing_or_invalid_files": missing,
            "baseline_verified": False,
            "external_source_checks_run": 0,
        })
    absent_universe = [Path(name).name for name in config["universe_sources"]
                       if files[Path(name).name]["state"] != "PRESENT_UNVERIFIED"]
    registry = files.get("company_registry.csv", {})
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "PREFLIGHT_ONLY",
        "status": "MISSING_INPUT_FILES" if absent_universe or
                  any(item["missing_or_invalid_files"] for item in tabs_report)
                  else "INPUTS_PRESENT_SOURCE_SCAN_PENDING",
        "baseline_verified": False,
        "nightly_automation_enabled": False,
        "external_network_requests_made": 0,
        "registry_rows_saved_not_reverified": registry.get("records", 0),
        "universe_files_missing": absent_universe,
        "tabs": tabs_report,
        "source_file_audit": files,
        "missing_required_source_families": [
            family["name"] for family in config["shared_source_families"]
            if family.get("required")
        ],
        "next_step": "Run per-source full-baseline collectors with exact-ID ledger; "
                     "do not activate nightly delta until all required checks are audited.",
        "disclaimer": "Existing CSVs are historical snapshots, not proof that an "
                      "external source has been scanned, is complete or is fresh.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="Repository root with config/ and data/")
    parser.add_argument("--config", type=Path,
                        help="Override configuration path")
    parser.add_argument("--output", type=Path,
                        help="JSON output path; default <root>/reports/scan_234_preflight.json")
    args = parser.parse_args()
    report = build_report(args.root, args.config)
    target = args.output or args.root / "reports" / "scan_234_preflight.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)
    print(json.dumps({
        "status": report["status"],
        "baseline_verified": False,
        "registry_rows_saved_not_reverified": report["registry_rows_saved_not_reverified"],
        "tabs": report["tabs"],
        "output": str(target),
    }, indent=2))
    return 0 if report["status"] == "INPUTS_PRESENT_SOURCE_SCAN_PENDING" else 2


if __name__ == "__main__":
    raise SystemExit(main())
