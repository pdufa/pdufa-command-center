#!/usr/bin/env python3
"""Run one real PDUFA clinical collector and write an honest per-scan audit.

Invoked inside run_scan_with_email: START notification is required before
collection; END notification is attempted after success, failure or timeout.
Clinical evidence alone never certifies the full FDA/SEC/issuer/market baseline.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "2": ("scripts/all_phase_scan.py", "all_phase_scan_state.json",
          ["--data-dir", "data"]),
    "3": ("scripts/phase_pipeline.py", "phase_pipeline_state.json",
          ["--data-dir", "data", "--lookback-days", "730", "--page-limit", "60"]),
    "4": ("scripts/phase3_results_intake.py", "phase3_intake_status.json",
          ["--mode", "daily", "--max-pages", "120", "--data-dir", "data"]),
}
MISSING = [
    "FDA regulatory decisions", "SEC financing/dilution",
    "issuer announcements", "cash/runway",
    "full price/volume/ownership", "full identity-coverage audit",
]


def summarize(scan, source, returncode, fresh):
    ok = fresh and returncode == 0 and source.get("status") in (
        "COMPLETE", "COMPLETE WITH WARNINGS"
    )
    state = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scan": scan,
        "scan_kind": "CLINICAL_SOURCE_COLLECTION_ONLY",
        "status": "PARTIAL" if ok else "FAILED",
        "collector_status": source.get("status") if fresh else "NO_FRESH_REPORT",
        "collector_exit_code": returncode,
        "full_coverage_verified": False,
        "complete": False,
        "missing_required_source_families": MISSING,
        "note": "Clinical source-only; FDA/SEC/issuer/market coverage remains unverified.",
    }
    fields = (
        "registry_companies", "companies_checked", "studies_checked",
        "studies_scanned", "tracked_trials_total", "tracked_trials_checked",
        "new_records", "changed_trials_this_execution", "companies_with_warnings",
        "tracked_trials_with_warnings", "market_cap_source_unavailable",
        "matched_trials", "matched_posted_results",
    )
    for key in fields:
        if fresh and isinstance(source.get(key), int) and not isinstance(source[key], bool):
            state[key] = source[key]
    if "registry_companies" in state:
        state["companies_due"] = state["registry_companies"]
    if "studies_checked" not in state and "studies_scanned" in state:
        state["studies_checked"] = state["studies_scanned"]
    errors = source.get("errors", []) if fresh else []
    state["errors_count"] = len(errors) if isinstance(errors, list) else 1
    return state


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", choices=sorted(SOURCES), required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    script, state_filename, flags = SOURCES[args.scan]
    status_path = ROOT / "data" / state_filename
    before = status_path.stat().st_mtime_ns if status_path.exists() else None
    code = 1
    try:
        outcome = subprocess.run([sys.executable, str(ROOT / script), *flags],
                                 cwd=ROOT, check=False, timeout=6600)
        code = outcome.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("Clinical collector stopped: " + type(exc).__name__, file=sys.stderr)
    state = {}
    fresh = False
    try:
        after = status_path.stat().st_mtime_ns
        fresh = before is None or after != before
        if fresh:
            state = json.loads(status_path.read_text(encoding="utf-8"))
            if not isinstance(state, dict):
                fresh, state = False, {}
    except (OSError, ValueError, UnicodeError):
        fresh = False
    report = summarize(args.scan, state, code, fresh)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PDUFA NIGHTLY AUDIT")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PARTIAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
