#!/usr/bin/env python3
"""Read-only comparison of saved scan metadata with the executable night clock.

This command never dispatches a scan, writes configuration, contacts GitHub, or
changes a schedule. Exit 2 means saved metadata needs review; exit 3 means the
runtime clock could not be reconciled. A green unit test is not clock alignment.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CONFIG = "config/scan_234.json"
WORKFLOW = ".github/workflows/pdufa-nightly-pacific-start.yml"
GATE = "scripts/nightly_start.py"


def _start_hour(source: str) -> int:
    """Read the admission's literal start assignment; do not execute source code."""
    values = []
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "start" for t in node.targets)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "replace"):
            values.extend(k.value.value for k in node.value.keywords
                          if k.arg == "hour" and isinstance(k.value, ast.Constant))
    if len(values) != 1 or type(values[0]) is not int or not 0 <= values[0] <= 23:
        raise ValueError("Night admission requires one auditable literal start hour")
    return values[0]


def audit_schedule(root: Path = ROOT) -> dict:
    """Keep operational consistency separate from nonauthoritative saved labels."""
    root = Path(root)
    report = {
        "status": "NOT_VERIFIED", "runtime_status": "NOT_VERIFIED",
        "metadata_matches_runtime": False, "read_only": True,
        "changes_applied": False, "scan_dispatches": 0,
        "runtime_authority": [WORKFLOW, GATE], "saved_metadata": CONFIG,
        "issues": [], "warnings": [],
    }
    try:
        raw = {name: (root / name).read_bytes() for name in (CONFIG, WORKFLOW, GATE)}
        report["source_sha256"] = {name: hashlib.sha256(data).hexdigest()
                                   for name, data in raw.items()}
        config = json.loads(raw[CONFIG])
        saved = config["clinical_source_schedule"]
        if (saved.get("timezone") != "America/Los_Angeles"
                or not isinstance(saved.get("cron_utc"), list)
                or any(not isinstance(c, str) for c in saved["cron_utc"])
                or any(not isinstance(saved.get(k), str)
                       for k in ("pacific_daylight_time", "pacific_standard_time"))):
            raise ValueError("Saved schedule metadata is incomplete or has an unsupported timezone")
        workflow = raw[WORKFLOW].decode("utf-8")
        hour = _start_hour(raw[GATE].decode("utf-8"))
        actual = re.findall(r"^\s+- cron: ['\"]([^'\"]+)['\"]", workflow, re.M)
        if not actual or len(actual) != len(set(actual)):
            raise ValueError("Launcher cron entries are missing or duplicated")
        if "python scripts/nightly_start.py" not in workflow:
            raise ValueError("Launcher does not invoke the audited admission gate")
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, SyntaxError) as exc:
        report["issues"].append(str(exc))
        return report

    # Representative winter/summer dates check both UTC offsets without making
    # assumptions about the executor timezone. Recovery slots remain distinct.
    pacific = ZoneInfo("America/Los_Angeles")
    utc_hours = sorted({datetime(2026, month, 15, hour, tzinfo=pacific)
                        .astimezone(timezone.utc).hour for month in (1, 7)})
    primary = [f"{minute} {h} * * *" for h in utc_hours for minute in (0, 15, 30)]
    missing = sorted(set(primary) - set(actual))
    effective = f"{hour:02}:00"
    report.update({
        "timezone": "America/Los_Angeles", "effective_pacific_start": effective,
        "saved_pacific_daylight_time": saved["pacific_daylight_time"],
        "saved_pacific_standard_time": saved["pacific_standard_time"],
        "launcher_crons": actual, "saved_crons": saved["cron_utc"],
        "expected_primary_crons": primary, "missing_primary_crons": missing,
        "only_in_launcher": sorted(set(actual) - set(saved["cron_utc"])),
        "only_in_saved_metadata": sorted(set(saved["cron_utc"]) - set(actual)),
    })
    if missing:
        report["status"] = "RUNTIME_CONFLICT"
        report["issues"].append("Launcher lacks DST primary cron slots required by its admission start hour")
        return report
    report["runtime_status"] = "CONSISTENT"
    matches = (saved["pacific_daylight_time"] == effective
               and saved["pacific_standard_time"] == effective
               and saved["cron_utc"] == actual)
    report["metadata_matches_runtime"] = matches
    report["status"] = "CONSISTENT" if matches else "METADATA_DRIFT"
    if not matches:
        report["warnings"].append(
            "Saved scan metadata differs from the executable launcher/admission. "
            "It does not control scan start times; review metadata and documentation separately. "
            "No schedule was changed."
        )
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    report = audit_schedule(args.root)
    print(json.dumps(report, indent=2))
    return {"CONSISTENT": 0, "METADATA_DRIFT": 2}.get(report["status"], 3)


if __name__ == "__main__":
    raise SystemExit(main())
