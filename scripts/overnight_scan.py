#!/usr/bin/env python3
"""Run the existing nightly clinical collectors and audit coverage without claiming all-source completion."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ("all_phase_inventory", "scripts/all_phase_scan.py", "all_phase_scan_state.json"),
    ("clinical_pipeline", "scripts/phase_pipeline.py", "phase_pipeline_state.json"),
    ("phase3_posted_results", "scripts/phase3_results_intake.py", "phase3_intake_status.json"),
]
VALID = {"COMPLETE", "COMPLETE WITH WARNINGS", "PARTIAL", "FAILED"}

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

def summarize(data_dir, executions):
    checks = {}
    for key, script, filename in SOURCES:
        state = read_json(data_dir / filename)
        result = executions.get(key, {})
        status = state.get("status", "FAILED")
        if status not in VALID:
            status = "PARTIAL" if state.get("complete") else "FAILED"
        if result.get("returncode", 1) != 0 and status == "COMPLETE":
            status = "COMPLETE WITH WARNINGS"
        checks[key] = {
            "status": status, "finished_at": state.get("finished_at"),
            "registry_companies": state.get("registry_companies"),
            "studies_checked": state.get("studies_checked", state.get("studies_scanned")),
            "companies_checked": state.get("companies_checked"),
            "companies_due": state.get("registry_companies"),
            "errors": state.get("errors", []),
            "exit_code": result.get("returncode"),
            "source_scope": state.get("scope", script),
        }
    # ClinicalTrials.gov is only one of the required source families.
    missing = ["FDA regulatory decisions", "SEC financing and dilution",
               "issuer investor relations", "cash and runway",
               "price, volume and ownership", "all-company coverage audit"]
    completed = sum(x["status"] in ("COMPLETE", "COMPLETE WITH WARNINGS") for x in checks.values())
    overall = "PARTIAL" if completed else "FAILED"
    return {
        "started_at": executions.get("started_at"),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": overall,
        "complete": False,
        "source_checks": checks,
        "completed_collectors": completed,
        "total_collectors": len(SOURCES),
        "missing_required_source_families": missing,
        "note": "Collector completion does not establish full-universe completion. Historical verified records retained.",
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--skip-collectors", action="store_true", help="Reconcile existing states only")
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    executions = {"started_at": datetime.now(timezone.utc).isoformat()}
    for key, script, filename in SOURCES:
        if args.skip_collectors:
            executions[key] = {"returncode": 0}
            continue
        try:
            process = subprocess.run([sys.executable, str(ROOT / script),
                                      "--data-dir", str(args.data_dir)],
                                     cwd=ROOT, timeout=3300, check=False)
            executions[key] = {"returncode": process.returncode}
        except (OSError, subprocess.TimeoutExpired) as exc:
            executions[key] = {"returncode": 1, "error": str(exc)}
    report = summarize(args.data_dir, executions)
    (args.data_dir / "overnight_scan_status.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] != "FAILED" else 1

if __name__ == "__main__":
    raise SystemExit(main())
