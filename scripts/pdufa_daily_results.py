"""Record one Pacific calendar day's published PDUFA scan totals without guessing missing values.

Triggered after the complete overnight chain finishes. Each Pacific date is
updated in place; past dates are retained. Stage counts are taken only from
the same-day saved membership ledger, not from clinical result records.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "data" / "nightly_scan_report.json"
TRIALS = ROOT / "data" / "all_phase_trials.csv"
MEMBERSHIP = ROOT / "data" / "gem_stage_membership.json"
SOURCES = ROOT / "data" / "pdufa_source_report.json"
ARCHIVE = ROOT / "data" / "daily_scan_results.json"
PACIFIC = ZoneInfo("America/Los_Angeles")


def parse_date(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Scan timestamp must contain an explicit UTC offset")
    return parsed.astimezone(timezone.utc)


def empty(reason: str) -> dict:
    return {
        "previous": None, "new": None, "updated": None, "removed": None,
        "total": None, "basis": reason,
    }


def trial_total() -> dict:
    result = empty("Published registry inventory; not proof of full nightly source coverage or qualification.")
    try:
        with TRIALS.open(newline="", encoding="utf-8-sig") as handle:
            rows = csv.DictReader(handle)
            if "nct_id" not in (rows.fieldnames or []):
                return result
            ids = [r.get("nct_id", "") for r in rows]
        if len(ids) >= 10000 and len(ids) == len(set(ids)) and all(
            len(nct) == 11 and nct.startswith("NCT") and nct[3:].isdigit() for nct in ids
        ):
            result["total"] = len(ids)
            result["basis"] = ("Distinct NCT IDs in the published registry feed available "
                               "when this day's report was archived; not necessarily a complete same-run scan.")
    except (OSError, ValueError):
        pass
    return result


def same_run_trial_inventory(report: dict, run_id: int) -> dict | None:
    """Show same-run tracked trial totals and record changes, not invented additions."""
    for scan in report.get("scans", []):
        if (not isinstance(scan, dict) or str(scan.get("scan")) != "2"
                or scan.get("run_id") != run_id
                or scan.get("collector_status") != "COMPLETE"):
            continue
        metrics = scan.get("metrics", {})
        total = metrics.get("tracked_trials_total") if isinstance(metrics, dict) else None
        changed = scan.get("changed_trials_this_execution")
        if not isinstance(total, int) or isinstance(total, bool) or total < 0:
            continue
        counts = empty(
            "Same-night verified collector: tracked clinical trial inventory. "
            "This is not the qualified Pipeline total or an independently certified "
            "unique-NCT published master feed. Updated means trial records changed, "
            "not new trials or new GEM candidates."
        )
        counts["total"] = total
        if isinstance(changed, int) and not isinstance(changed, bool) and 0 <= changed <= total:
            counts["updated"] = changed
        return counts
    return None


def same_run_source_note(run_id: int) -> str | None:
    """Show only source-category counts that reconcile to this exact run."""
    try:
        sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(sources, dict) or str(sources.get("latest_run_id")) != str(run_id):
        return None

    categories = ("findings_verified", "findings_unresolved",
                  "findings_unavailable", "findings_not_applicable")
    expected = sources.get("findings_due")
    if (type(expected) is not int or expected < 0
            or any(type(sources.get(key)) is not int or sources[key] < 0
                   for key in categories)):
        return ("Same-run source audit: status-category counts incomplete or invalid; "
                "counts withheld. Full coverage verified: no.")

    # Older complete audit indexes omitted an explicit conflict field when zero.
    # Never infer zero if omitting the field leaves any source checks unaccounted for.
    conflicts = sources.get("findings_conflicted", 0)
    if type(conflicts) is not int or conflicts < 0:
        return ("Same-run source audit: conflicted-source count invalid; "
                "counts withheld. Full coverage verified: no.")
    accounted = sum(sources[key] for key in categories) + conflicts
    if accounted != expected:
        return ("Same-run source audit: source-category counts do not reconcile "
                f"({accounted} recorded of {expected} due); counts withheld. "
                "Full coverage verified: no.")

    coverage = (
        sources.get("full_coverage_verified") is True
        and sources["findings_verified"] == expected
        and not (sources["findings_unresolved"] or conflicts
                 or sources["findings_unavailable"])
        and not sources.get("missing_required_source_families")
    )
    return (
        f"Same-run source audit: {sources['findings_verified']} of "
        f"{expected} verified; {sources['findings_unresolved']} unresolved, "
        f"{conflicts} conflicted, {sources['findings_unavailable']} unavailable, "
        f"{sources['findings_not_applicable']} not applicable. "
        f"Full coverage verified: {'yes' if coverage else 'no'}."
    )

def stage_total(ledger: dict, stage: str, day: str) -> dict:
    title = stage.replace("_", " ")
    result = empty("No verified same-day saved " + title + " membership snapshot.")
    info = ledger.get("stages", {}).get(stage, {})
    if not isinstance(info, dict) or info.get("last_complete_snapshot") != day:
        return result
    entries = info.get("entries")
    if not isinstance(entries, dict):
        return result
    active = 0
    added = set()
    removed = set()
    for identity, row in entries.items():
        if not isinstance(row, dict):
            continue
        if row.get("status") == "ACTIVE":
            active += 1
        for period in row.get("periods", []):
            if not isinstance(period, dict):
                continue
            if period.get("found") == day:
                added.add(identity)
            if period.get("left") == day:
                removed.add(identity)
    old = active - len(added) + len(removed)
    if old < 0:
        return result
    result.update({
        "previous": old, "new": len(added), "removed": len(removed),
        "total": active,
        "basis": ("Same-day saved " + title + " membership ledger; independent FS/FA settings "
                  "are preserved. No assumption about unseen scores or Phase 3 readout counts."),
    })
    return result


def record(run_id: int, started: str, conclusion: str, night_date_pacific: str = "") -> dict:
    started_at = parse_date(started)
    actual_pacific_date = started_at.astimezone(PACIFIC).date()
    if night_date_pacific:
        try:
            night_date = date.fromisoformat(night_date_pacific)
        except ValueError as exc:
            raise ValueError("Invalid guarded Pacific scan night") from exc
        if (actual_pacific_date - night_date).days not in (0, 1):
            raise ValueError("Guarded scan night is inconsistent with run start")
    else:
        night_date = actual_pacific_date
    # GitHub run_started_at is the observable workflow start, NOT proof
    # that GitHub's 8 PM cron triggered punctually.
    scheduled_target = datetime.combine(night_date, time(20, 0), tzinfo=PACIFIC).astimezone(timezone.utc)
    delay_minutes = int((started_at - scheduled_target).total_seconds() // 60)
    if night_date_pacific and delay_minutes < 0:
        raise ValueError("Guarded scan night begins after actual workflow start")
    day = night_date.isoformat()
    now = datetime.now(timezone.utc).isoformat()
    run_url = "https://github.com/pdufa/pdufa-command-center/actions/runs/" + str(run_id)
    sections = {
        "master": empty("Same-run inventory evidence unavailable."),
        "pipeline": empty("Full mandatory Pipeline qualification totals are not established by clinical source collection."),
        "designations": empty("FDA special designation grant records and dates require authoritative verification."),
        "gem_jr": empty("No verified same-day GEM JR membership snapshot."),
        "gem": empty("No verified same-day GEM membership snapshot."),
    }
    notes = []
    try:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        report = {}
    same_run = (
        report.get("latest_run_id") == run_id
        and isinstance(report.get("latest_run_started_at_utc"), str)
        and parse_date(report["latest_run_started_at_utc"]) == started_at
    )
    status = "RUN_FAILED" if conclusion != "success" else "UNVERIFIED"
    if same_run:
        status = "PARTIAL" if conclusion == "success" else "RUN_FAILED"
        # Prefer exact-run inventory evidence to a feed copied at an unrelated time.
        sections["master"] = same_run_trial_inventory(report, run_id) or trial_total()
        if sections["master"].get("updated") is not None:
            notes.append(
                f"{sections['master']['updated']} tracked trial records changed during "
                "this run; newly added trials and qualified Pipeline additions remain unverified."
            )
        source_note = same_run_source_note(run_id)
        if source_note:
            notes.append(source_note)
        try:
            ledger = json.loads(MEMBERSHIP.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            ledger = {}
        sections["gem_jr"] = stage_total(ledger, "GEM_JR", day)
        sections["gem"] = stage_total(ledger, "GEM", day)
        notes.append("Clinical collection and the full overnight sequence are different verification standards; full-source certification is not implied.")
        if report.get("status") in ("FAILED", "UNVERIFIED"):
            status = "RUN_FAILED" if conclusion != "success" else "UNVERIFIED"
        if report.get("missing_required_source_families"):
            notes.append("FDA, SEC, issuer and/or market source families remain unverified.")
    else:
        notes.append("The published source report does not match this exact overnight run; counts deliberately withheld.")
    if conclusion != "success":
        notes.append("Nightly workflow conclusion: " + conclusion + ".")
    return {
        "date_pacific": day, "run_id": run_id, "run_url": run_url, "status": status,
        "run_started_at_utc": started_at.isoformat(),
        "scheduled_8pm_pacific_utc": scheduled_target.isoformat(),
        "start_delay_minutes": delay_minutes,
        "scan_night_source": "GUARDED_SCHEDULER_INPUT" if night_date_pacific else "ACTUAL_START_DATE_FALLBACK",
        "registered_at_utc": now, "sections": sections, "notes": notes,
    }


def publish(run_id: int, started: str, conclusion: str, night_date_pacific: str = "") -> None:
    if run_id < 1 or conclusion not in ("success", "failure", "cancelled", "timed_out"):
        raise ValueError("Invalid GitHub run metadata")
    entry = record(run_id, started, conclusion, night_date_pacific)
    try:
        previous = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    existing = previous.get("days", [])
    if not isinstance(existing, list):
        existing = []
    records = {
        x["date_pacific"]: x for x in existing
        if isinstance(x, dict) and isinstance(x.get("date_pacific"), str)
    }
    old = records.get(entry["date_pacific"])
    # A later publication must never replace an already-recorded newer run.
    if old and isinstance(old.get("run_id"), int) and old["run_id"] > run_id:
        print("Newer run already registered for", entry["date_pacific"])
        return
    # A failed, source-unmatched retry must not erase same-day recorded evidence.
    if (old and old.get("status") == "PARTIAL" and entry["status"] != "PARTIAL"
            and old.get("run_id") != run_id):
        prior_notes = list(old.get("notes") or [])
        failure_note = "Another run on this date did not publish matching evidence: #" + str(run_id)
        if failure_note not in prior_notes:
            prior_notes.append(failure_note)
        old["notes"] = prior_notes
        records[entry["date_pacific"]] = old
    else:
        records[entry["date_pacific"]] = entry
    archive = {
        "schema_version": 1,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "days": sorted(records.values(), key=lambda r: r["date_pacific"], reverse=True),
    }
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    temp = ARCHIVE.with_suffix(".json.tmp")
    temp.write_text(json.dumps(archive, indent=2) + "\n", encoding="utf-8")
    temp.replace(ARCHIVE)
    print("Registered Pacific date", entry["date_pacific"], "run", run_id, "status", entry["status"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--conclusion", required=True)
    parser.add_argument("--night-date-pacific", default="")
    args = parser.parse_args()
    publish(args.run_id, args.started_at, args.conclusion, args.night_date_pacific)
