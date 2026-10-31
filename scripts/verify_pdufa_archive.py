"""Read-only structural checks for the published PDUFA daily RESULTS archive.

Passing does not certify source-family completeness, scan punctuality, or FDA evidence.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

ARCHIVE = Path(__file__).resolve().parents[1] / "data" / "daily_scan_results.json"
REQUIRED = ("master", "pipeline", "designations", "gem_jr", "gem")
NUMBERS = ("previous", "new", "updated", "removed", "total")


def _timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError:
        return False


def check_archive(path: Path = ARCHIVE) -> tuple[list[str], dict]:
    errors: list[str] = []
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"Unable to load archive: {exc}"], {}
    if not isinstance(document, dict):
        return ["Archive must be a JSON object"], {}
    if document.get("schema_version") != 1:
        errors.append("Unexpected archive schema version")
    if not _timestamp(document.get("updated_at_utc")):
        errors.append("Missing timezone-aware archive updated_at_utc")

    days = document.get("days")
    if not isinstance(days, list) or not days:
        return errors + ["days must be a nonempty list"], {}
    dates: set[str] = set()
    runs: set[int] = set()
    last_date: str | None = None
    counts: dict[str, int] = {}
    for index, item in enumerate(days):
        prefix = f"days[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: expected object")
            continue
        day = item.get("date_pacific")
        try:
            if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
                raise ValueError()
        except ValueError:
            errors.append(f"{prefix}: invalid Pacific date")
            day = None
        if day:
            if day in dates:
                errors.append(f"{prefix}: duplicate Pacific date {day}")
            if last_date and day > last_date:
                errors.append(f"{prefix}: days are not in descending order")
            dates.add(day)
            last_date = day
        run = item.get("run_id")
        if type(run) is not int or run <= 0:
            errors.append(f"{prefix}: missing/invalid run_id")
        else:
            if run in runs:
                errors.append(f"{prefix}: duplicate run_id {run}")
            runs.add(run)
            expected_suffix = f"/actions/runs/{run}"
            url = item.get("run_url")
            if not isinstance(url, str) or urlparse(url).scheme != "https" or urlparse(url).netloc != "github.com" or not urlparse(url).path.endswith(expected_suffix):
                errors.append(f"{prefix}: run URL does not match run_id")
        if not _timestamp(item.get("registered_at_utc")):
            errors.append(f"{prefix}: registration timestamp missing timezone")
        # New scan reports carry a verifiable start timestamp and 8 PM
        # Pacific target. Legacy entries predate this feature and remain
        # readable; partially populated new timing fields are rejected.
        timing_fields = ("run_started_at_utc", "scheduled_8pm_pacific_utc",
                         "start_delay_minutes", "scan_night_source")
        if any(field in item for field in timing_fields):
            if not all(field in item for field in timing_fields):
                errors.append(f"{prefix}: incomplete scan timing provenance")
            elif (not _timestamp(item["run_started_at_utc"]) or
                  not _timestamp(item["scheduled_8pm_pacific_utc"]) or
                  type(item["start_delay_minutes"]) is not int or
                  item["scan_night_source"] not in
                  ("GUARDED_SCHEDULER_INPUT", "ACTUAL_START_DATE_FALLBACK",
                   "HISTORICAL_REPORT_RECONCILIATION")):
                errors.append(f"{prefix}: invalid scan timing provenance")
            elif day:
                started = datetime.fromisoformat(item["run_started_at_utc"].replace("Z", "+00:00"))
                target = datetime.combine(date.fromisoformat(day), time(20), tzinfo=ZoneInfo("America/Los_Angeles"))
                expected_delay = int((started - target).total_seconds() // 60)
                if expected_delay != item["start_delay_minutes"]:
                    errors.append(f"{prefix}: scan start delay does not match source timestamps")
                expected_target = target.astimezone(timezone.utc)
                claimed_target = datetime.fromisoformat(item["scheduled_8pm_pacific_utc"].replace("Z", "+00:00"))
                if expected_target != claimed_target:
                    errors.append(f"{prefix}: 8 PM Pacific target mismatch")
                if item["scan_night_source"] == "GUARDED_SCHEDULER_INPUT" and started < target:
                    errors.append(f"{prefix}: guarded scan starts before 8 PM Pacific")
                if item["scan_night_source"] == "HISTORICAL_REPORT_RECONCILIATION":
                    url = item.get("timing_evidence_url")
                    parts = urlparse(url) if isinstance(url, str) else None
                    path = parts.path.split("/") if parts else []
                    valid_evidence = bool(
                        parts and parts.scheme == "https" and parts.netloc == "github.com"
                        and len(path) == 7 and path[1:4] == ["pdufa", "pdufa-command-center", "blob"]
                        and len(path[4]) == 40 and all(c in "0123456789abcdef" for c in path[4])
                        and path[5:] == ["data", "nightly_scan_report.json"]
                    )
                    if not valid_evidence:
                        errors.append(f"{prefix}: historical scan timing requires immutable source provenance")

        status = item.get("status")
        if not isinstance(status, str) or not status.strip():
            errors.append(f"{prefix}: status is missing")
        else:
            counts[status] = counts.get(status, 0) + 1
        sections = item.get("sections")
        if not isinstance(sections, dict):
            errors.append(f"{prefix}: sections missing")
            continue
        for name in REQUIRED:
            section = sections.get(name)
            if not isinstance(section, dict):
                errors.append(f"{prefix}: missing {name} section")
                continue
            if not isinstance(section.get("basis"), str) or not section["basis"].strip():
                errors.append(f"{prefix}: {name} source-basis explanation missing")
            for key in NUMBERS:
                value = section.get(key)
                if value is not None and (type(value) is not int or value < 0):
                    errors.append(f"{prefix}: {name}.{key} must be null or a nonnegative integer")

        # A full scan must not be advertised when the mandatory qualified
        # Pipeline and original FDA-designation counts or source certification
        # remain unknown. A healthy clinical inventory alone is insufficient.
        if status == "COMPLETE":
            if any(not isinstance(sections.get(name), dict) or
                   sections[name].get("total") is None for name in ("pipeline", "designations")):
                errors.append(f"{prefix}: COMPLETE requires qualified Pipeline and FDA designation totals")
            if item.get("full_source_coverage_verified") is not True:
                errors.append(f"{prefix}: COMPLETE requires explicit same-run source coverage certification")

    summary = {
        "archive_date_count": len(days),
        "unique_dates": len(dates),
        "unique_run_ids": len(runs),
        "latest_pacific_date": days[0].get("date_pacific") if isinstance(days[0], dict) else None,
        "statuses": counts,
        "full_source_coverage_certified": False,
        "punctual_8pm_schedule_certified": False,
    }
    return errors, summary


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ARCHIVE
    errors, summary = check_archive(target)
    print(json.dumps({"structural_integrity": "FAIL" if errors else "PASS", "summary": summary,
                      "errors": errors, "limitation": "Structural checks only; partial runs and unknown source-family counts remain unverified."}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
