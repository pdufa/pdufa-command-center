"""Persistent exact-Pipeline-ID membership history for GEM JR and GEM.

Tracks first observed in each stage, reentries and exits; no historical discovery
dates are backfilled from trial readout or SEC filing timestamps. Never call
update_history when a complete trustworthy scan was not verified.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

STAGES = ("GEM_JR", "GEM")
VERSION = 1
FILENAME = "gem_stage_membership.json"


def empty_history():
    return {"schema_version": VERSION, "stages": {
        stage: {"last_complete_snapshot": None, "entries": {}} for stage in STAGES
    }}


def read_history(data_dir="data"):
    file = Path(data_dir) / FILENAME
    if not file.is_file():
        return empty_history()
    state = json.loads(file.read_text(encoding="utf-8"))
    if state.get("schema_version") != VERSION or not isinstance(state.get("stages"), dict):
        raise ValueError("Unsupported GEM membership ledger schema")
    for stage in STAGES:
        saved = state["stages"].get(stage)
        if not isinstance(saved, dict) or not isinstance(saved.get("entries"), dict):
            raise ValueError(f"Missing or corrupt {stage} membership history")
    return state


def _identity(row):
    identifier = str(row.get("Pipeline ID") or "").strip()
    ticker = str(row.get("Ticker") or "").strip().upper()
    if (not identifier.startswith(("APPLICATION|", "TRIAL|"))
            or not ticker):
        raise ValueError("Stage membership requires an exact Pipeline ID and ticker")
    return identifier, ticker


def update_history(old, stage_members, *, observed_on):
    """Record one complete, evidence-reconciled snapshot for EACH stage.

    Stage lists may differ. A candidate leaving GEM JR for GEM gets two
    independent dated transitions. Missing/incomplete snapshot must never
    be supplied here, as disappearance otherwise looks like an exit.
    """
    day = date.fromisoformat(str(observed_on)).isoformat()
    if set(stage_members) != set(STAGES):
        raise ValueError("Both complete stage snapshots are required")
    result = json.loads(json.dumps(old))
    for stage in STAGES:
        slot = result["stages"][stage]
        prior = slot.get("last_complete_snapshot")
        if prior and day < prior:
            raise ValueError("Refuse backdated stage snapshot")
        active = {}
        for row in stage_members[stage]:
            identifier, ticker = _identity(row)
            if identifier in active and active[identifier]["ticker"] != ticker:
                raise ValueError("Conflicting issuer for one Pipeline ID")
            active[identifier] = {
                "ticker": ticker,
                "drug": str(row.get("Drug") or "").strip(),
                "nct_id": str(row.get("NCT ID") or "").strip(),
                "exact_program": str(row.get("Exact program") or "").strip(),
            }
        history = slot["entries"]
        for identifier, record in active.items():
            if identifier not in history:
                history[identifier] = {
                    "pipeline_id": identifier, **record,
                    "first_found": day, "latest_found": day,
                    "last_seen": day, "left_date": None, "status": "ACTIVE",
                    "periods": [{"found": day, "left": None}],
                }
            else:
                entry = history[identifier]
                if entry["ticker"] != record["ticker"]:
                    raise ValueError("Pipeline ID changed issuer across snapshots")
                entry.update(record)
                if entry["status"] == "LEFT":
                    entry["latest_found"] = day
                    entry["left_date"] = None
                    entry["periods"].append({"found": day, "left": None})
                entry["status"] = "ACTIVE"
                entry["last_seen"] = day
        for identifier, entry in history.items():
            if identifier in active or entry["status"] != "ACTIVE":
                continue
            entry["status"] = "LEFT"
            entry["left_date"] = day
            if entry["periods"] and entry["periods"][-1]["left"] is None:
                entry["periods"][-1]["left"] = day
        slot["last_complete_snapshot"] = day
    return result


def membership_fields(state, stage, pipeline_id):
    slot = state.get("stages", {}).get(stage, {})
    entry = slot.get("entries", {}).get(str(pipeline_id or ""), {})
    if not entry:
        return {"Date Found": "NOT YET TRACKED", "Date Left": "",
                "Date Re-entered": "", "Listing status": "NOT YET TRACKED"}
    periods = entry.get("periods", [])
    return {
        "Date Found": entry.get("first_found") or "NOT YET TRACKED",
        "Date Left": entry.get("left_date") or "",
        "Date Re-entered": (entry.get("latest_found") or "")
                            if len(periods) > 1 else "",
        "Listing status": entry.get("status", "UNKNOWN"),
    }


def enrich_stage_rows(rows, stage, state):
    if stage not in STAGES:
        raise ValueError("Unknown stage")
    return [{
        **row, **membership_fields(state, stage, row.get("Pipeline ID"))
    } for row in rows]


def enrich_gem_master_rows(rows, state):
    """Expose GEM listing dates without implying unqualified programs entered GEM."""
    history = state["stages"]["GEM"]["entries"]
    result = []
    for row in rows:
        pid = row.get("Pipeline ID")
        if pid in history or row.get("_eligible") is True:
            fields = membership_fields(state, "GEM", pid)
        else:
            fields = {"Date Found": "NOT GEM-QUALIFIED", "Date Left": "",
                      "Date Re-entered": "", "Listing status": "RESEARCH ONLY"}
        result.append({**row, **fields})
    return result


def departed_stage_rows(state, stage):
    """Retain all past exits, even after a later re-entry."""
    slot = state["stages"][stage]
    records = []
    for entry in slot["entries"].values():
        for period in entry.get("periods", []):
            if period.get("left"):
                records.append({
                    "Pipeline ID": entry["pipeline_id"],
                    "Ticker": entry["ticker"],
                    "Drug": entry.get("drug", ""),
                    "NCT ID": entry.get("nct_id", ""),
                    "Date Found": period["found"],
                    "Date Left": period["left"],
                    "Listing status": (
                        "RETURNED / ACTIVE" if entry["status"] == "ACTIVE"
                        else "LEFT"
                    ),
                })
    return sorted(records, key=lambda r: (r["Date Left"], r["Ticker"]), reverse=True)


def write_history(data_dir, state):
    target = Path(data_dir) / FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(state, indent=2, sort_keys=True) + "\n"
    if target.exists() and target.read_text(encoding="utf-8") == serialized:
        return False
    staging = target.with_suffix(".tmp")
    staging.write_text(serialized, encoding="utf-8")
    staging.replace(target)
    return True
