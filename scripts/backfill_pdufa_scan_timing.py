"""Reconcile archived nightly start timing using exact-run saved source history.

Dry-run by default.  --apply updates only missing timing fields and retains
the original scan counts, labels and evidence status without executing scans.
A historical report is not independent proof of scheduler punctuality.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "daily_scan_results.json"
HISTORY = ROOT / "data" / "nightly_scan_report.json"
PACIFIC = ZoneInfo("America/Los_Angeles")
EVIDENCE_COMMIT = "75d980b83081a06389c4ce7e0f13b3e974a50d80"
EVIDENCE_URL = (
    "https://github.com/pdufa/pdufa-command-center/blob/"
    + EVIDENCE_COMMIT + "/data/nightly_scan_report.json"
)
PROVENANCE = "HISTORICAL_REPORT_RECONCILIATION"
FIELDS = ("run_started_at_utc", "scheduled_8pm_pacific_utc",
          "start_delay_minutes", "scan_night_source", "timing_evidence_url")


def aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Run start must contain an explicit UTC offset")
    return parsed.astimezone(timezone.utc)


def reconcile(archive: dict, source: dict) -> tuple[dict, dict]:
    if archive.get("schema_version") != 1 or not isinstance(archive.get("days"), list):
        raise ValueError("Unsupported archive structure")
    if not isinstance(source.get("history"), list):
        raise ValueError("Source report history is unavailable")
    history: dict[int, dict] = {}
    for item in source["history"]:
        if not isinstance(item, dict) or type(item.get("run_id")) is not int:
            continue
        run_id = item["run_id"]
        if run_id in history and history[run_id].get("started_at_utc") != item.get("started_at_utc"):
            raise ValueError(f"Conflicting source starts for run {run_id}")
        history[run_id] = item

    result = json.loads(json.dumps(archive))
    updated: list[str] = []
    preserved: list[str] = []
    unavailable: list[str] = []
    for entry in result["days"]:
        if not isinstance(entry, dict) or type(entry.get("run_id")) is not int:
            raise ValueError("Archive contains invalid run metadata")
        run_id = entry["run_id"]
        day_string = entry.get("date_pacific")
        night = date.fromisoformat(day_string)
        existing = [key for key in FIELDS if key in entry]
        if existing:
            if len(existing) != len(FIELDS):
                raise ValueError(f"Partial timing evidence for run {run_id}; refusing overwrite")
            preserved.append(day_string)
            continue
        record = history.get(run_id)
        if record is None or not isinstance(record.get("started_at_utc"), str):
            unavailable.append(day_string)
            continue
        start = aware(record["started_at_utc"])
        local_date = start.astimezone(PACIFIC).date()
        if (local_date - night).days not in (0, 1):
            raise ValueError(f"History run date mismatches archived night for run {run_id}")
        target = datetime.combine(night, time(20), tzinfo=PACIFIC).astimezone(timezone.utc)
        delta = int((start - target).total_seconds() // 60)
        if delta < 0:
            raise ValueError(f"Run {run_id} predates 8 PM Pacific scan night")
        if record.get("run_url") != entry.get("run_url"):
            raise ValueError(f"Source run URL mismatch for run {run_id}")
        entry.update({
            "run_started_at_utc": start.isoformat(),
            "scheduled_8pm_pacific_utc": target.isoformat(),
            "start_delay_minutes": delta,
            "scan_night_source": PROVENANCE,
            "timing_evidence_url": EVIDENCE_URL,
        })
        updated.append(day_string)
    return result, {"filled": updated, "preserved": preserved, "unavailable": unavailable}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--archive", type=Path, default=ARCHIVE)
    parser.add_argument("--source", type=Path, default=HISTORY)
    args = parser.parse_args()
    before = json.loads(args.archive.read_text(encoding="utf-8"))
    source = json.loads(args.source.read_text(encoding="utf-8"))
    after, report = reconcile(before, source)
    if args.apply and report["filled"]:
        after["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        target = args.archive.with_suffix(".json.tmp")
        target.write_text(json.dumps(after, indent=2) + "\n", encoding="utf-8")
        target.replace(args.archive)
    print(json.dumps({"mode": "APPLIED" if args.apply else "DRY_RUN", **report,
                      "note": "Timing provenance only. No scans or source-family acceptance asserted."}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
