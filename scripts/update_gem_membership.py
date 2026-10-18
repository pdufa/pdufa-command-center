#!/usr/bin/env python3
"""Update GEM JR/GEM stage membership dates after a fully validated scan only.

Called from the GEM scan workflow after clinical registry, exact trial and
financing rechecks succeed. A failed/partial run MUST NOT record departures.
Dates are first observed in the audit ledger, not retrospectively guessed.
"""
from __future__ import annotations

import argparse
import json
import sys
import csv
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gem_membership_history import read_history, update_history, write_history
from gem_potential_list import build_potential_list
from gem_verified_snapshot import source_cleared_gems
from pipeline_source_scope import pipeline_origins


def current_stage_members(data_dir, *, as_of):
    pids, _ = pipeline_origins(data_dir, today=as_of)
    if not pids:
        raise ValueError("Empty Pipeline universe: refuse stage departure inference")
    junior, _timing_holds = build_potential_list(data_dir, as_of=as_of)
    cleared, _historical, _sec_current = source_cleared_gems(data_dir, as_of=as_of)
    gem_ids = {str(row.get("Pipeline ID") or "") for row in cleared}
    jr = [row for row in junior if row.get("Pipeline ID") not in gem_ids]
    # Pre-Oct-15 discovery policy: a sound issuer/trial research lead need
    # not be in Pipeline already. The canonical ID check is not an admission
    # gate; date/exit tracking still uses stable exact APPLICATION/TRIAL IDs.
    return {"GEM_JR": jr, "GEM": cleared}



def stage_exit_reasons(data_dir, prior, current, *, as_of):
    """Explain exactly why a tracked Pipeline ID left its previous stage.

    A promotion is not a PDUFA expiry. A verified FDA resolution may close
    the program early. Unknown absences are flagged as scan membership changes
    rather than falsely called PDUFA expiries.
    """
    source_events = {}
    path = Path(data_dir) / "pdufa_candidates.csv"
    if path.is_file():
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                identifier = "APPLICATION|" + str(row.get("event_key") or "").strip()
                if identifier not in source_events:
                    source_events[identifier] = row
    future = {stage: {row["Pipeline ID"] for row in members}
              for stage, members in current.items()}
    reasons = {stage: {} for stage in current}
    for stage in current:
        for pid, entry in prior["stages"][stage]["entries"].items():
            if entry.get("status") != "ACTIVE" or pid in future[stage]:
                continue
            if stage == "GEM_JR" and pid in future["GEM"]:
                reasons[stage][pid] = "PROMOTED_TO_GEM"
                continue
            source = source_events.get(pid, {})
            outcome = str(source.get("outcome") or "").strip().upper()
            if outcome in {"APPROVED", "CRL", "REJECTED", "WITHDRAWN", "REFUSED"}:
                reasons[stage][pid] = "FDA_RESOLVED_" + outcome
                continue
            try:
                pdufa = date.fromisoformat(str(source.get("pdufa_date") or "")[:10])
            except ValueError:
                pdufa = None
            if pdufa is not None and pdufa < as_of:
                reasons[stage][pid] = "PDUFA_EXPIRED"
            else:
                reasons[stage][pid] = "NO_LONGER_IN_VERIFIED_STAGE_SNAPSHOT"
    return reasons

def validate_registry_snapshot(data_dir, observed_on):
    """Fail closed unless the current run actually completed its registry scan.

    A saved COMPLETE flag from yesterday is not a dated GEM JR/GEM
    membership snapshot. This blocks accidental mass departures from
    a stale or partially published ClinicalTrials.gov feed.
    """
    root = Path(data_dir)
    status = json.loads(
        (root / "phase3_intake_status.json").read_text(encoding="utf-8"))
    if (status.get("status") != "COMPLETE"
            or status.get("complete") is not True
            or status.get("errors")):
        raise ValueError("Incomplete Phase 3 registry: preserve existing found/left dates")
    finished = str(status.get("finished_at") or "")
    started = str(status.get("started_at") or "")
    try:
        completed = datetime.fromisoformat(finished)
        commenced = datetime.fromisoformat(started)
    except (ValueError, TypeError) as e:
        raise ValueError("Missing dated registry collection timestamps") from e
    if (completed.tzinfo is None or commenced.tzinfo is None or
            completed < commenced or
            completed.astimezone(ZoneInfo("America/Los_Angeles")).date() != observed_on or
            commenced.astimezone(ZoneInfo("America/Los_Angeles")).date() != observed_on):
        raise ValueError(
            "Registry scan not complete on the specified Pacific observation date")
    expected = status.get("stored_results")
    if type(expected) is not int or expected < 0:
        raise ValueError("Registry result count absent or invalid")
    with (root / "phase3_announcements.csv").open(newline="", encoding="utf-8-sig") as f:
        actual = sum(1 for _ in csv.DictReader(f))
    if actual != expected:
        raise ValueError("Registry count does not match published trial observations")
    return status


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--as-of", default="")
    args = parser.parse_args(argv)
    day = (date.fromisoformat(args.as_of) if args.as_of
           else datetime.now(ZoneInfo("America/Los_Angeles")).date())
    # Check the collector date and saved-row totals even on manual invocation.
    # Do not archive a prior GEM/JR member using yesterday's successful scan.
    validate_registry_snapshot(args.data_dir, day)
    stages = current_stage_members(args.data_dir, as_of=day)
    prior = read_history(args.data_dir)
    reasons = stage_exit_reasons(args.data_dir, prior, stages, as_of=day)
    ledger = update_history(prior, stages, observed_on=day, exit_reasons=reasons)
    changed = write_history(args.data_dir, ledger)
    print(json.dumps({
        "date_pacific": day.isoformat(), "changed": changed,
        "first_tracked_after_ledger_install": True,
        "members": {stage: len(rows) for stage, rows in stages.items()},
        "departures_total": {
            stage: sum(r["status"] == "LEFT" for r in ledger["stages"][stage]["entries"].values())
            for stage in stages
        },
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
