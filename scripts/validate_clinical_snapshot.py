"""Allow publication only of fresh, reconciled clinical collector outputs."""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

STATES = {"2": "all_phase_scan_state.json", "3": "phase_pipeline_state.json",
          "4": "phase3_intake_status.json"}
LEDGERS = {"2": ("all_phase_trials.csv", "trials_stored"),
           "3": ("phase_pipeline.csv", "stored_trials"),
           "4": ("phase3_announcements.csv", "stored_results")}


def validate(scan, *, root=Path("."), now=None):
    report = json.loads((root / "reports" / f"nightly-clinical-{scan}.json").read_text())
    state = json.loads((root / "data" / STATES[scan]).read_text())
    complete = state.get("complete") is True
    if scan == "2" and state.get("status") == "COMPLETE WITH WARNINGS":
        complete = all(type(state.get(key)) is int and state[key] >= 0 for key in
                       ("companies_checked", "registry_companies", "tracked_trials_checked", "tracked_trials_total"))
        complete = complete and state["companies_checked"] == state["registry_companies"] and state["tracked_trials_checked"] == state["tracked_trials_total"]
    if (report.get("scan") != scan or report.get("status") != "PARTIAL" or
            report.get("collector_exit_code") != 0 or
            report.get("collector_status") not in ("COMPLETE", "COMPLETE WITH WARNINGS") or
            report.get("collector_status") != state.get("status") or
            not complete or
            not report.get("created_at_utc") or
            report.get("full_coverage_verified") is not False):
        raise ValueError("Incomplete or unverified clinical output; keep prior published data")
    clock = now or datetime.now(timezone.utc)
    reported = datetime.fromisoformat(report["created_at_utc"].replace("Z", "+00:00"))
    finished = datetime.fromisoformat(state["finished_at"].replace("Z", "+00:00"))
    if reported.tzinfo is None or finished.tzinfo is None or not (clock - timedelta(hours=4) <= finished <= reported <= clock + timedelta(minutes=5)):
        raise ValueError("Clinical snapshot timestamps are stale, unordered or invalid")
    ledger, count_key = LEDGERS[scan]
    with (root / "data" / ledger).open(newline="", encoding="utf-8-sig") as handle:
        rows = sum(1 for _ in csv.DictReader(handle))
    if type(state.get(count_key)) is not int or state[count_key] != rows:
        raise ValueError("Clinical ledger row count disagrees with the collector state")
    if scan == "4" and state.get("errors"):
        raise ValueError("Phase 3 intake did not publish new records after source errors")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", required=True, choices=STATES)
    args = parser.parse_args()
    validate(args.scan)
    print("Fresh completed clinical collector accepted; full-source coverage remains PARTIAL")


if __name__ == "__main__":
    main()
