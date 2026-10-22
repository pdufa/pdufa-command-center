"""Record one Pacific calendar day's published PDUFA scan totals without guessing missing values.

Triggered after the complete overnight chain finishes. Each Pacific date is
updated in place; past dates are retained. Stage counts are taken only from
the same-day saved membership ledger, not from clinical result records.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "data" / "nightly_scan_report.json"
TRIALS = ROOT / "data" / "all_phase_trials.csv"
MEMBERSHIP = ROOT / "data" / "gem_stage_membership.json"
ARCHIVE = ROOT / "data" / "daily_scan_results.json"
PACIFIC = ZoneInfo("America/Los_Angeles")


def parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


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


def record(run_id: int, started: str, conclusion: str) -> dict:
    day = parse_date(started).astimezone(PACIFIC).date().isoformat()
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
        and parse_date(report["latest_run_started_at_utc"]).astimezone(PACIFIC).date().isoformat() == day
    )
    status = "RUN_FAILED" if conclusion != "success" else "UNVERIFIED"
    if same_run:
        status = "PARTIAL" if conclusion == "success" else "RUN_FAILED"
        sections["master"] = trial_total()
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
        "registered_at_utc": now, "sections": sections, "notes": notes,
    }


def publish(run_id: int, started: str, conclusion: str) -> None:
    if run_id < 1 or conclusion not in ("success", "failure", "cancelled", "timed_out"):
        raise ValueError("Invalid GitHub run metadata")
    entry = record(run_id, started, conclusion)
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
    args = parser.parse_args()
    publish(args.run_id, args.started_at, args.conclusion)
