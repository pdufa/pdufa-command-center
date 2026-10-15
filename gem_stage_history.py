"""Append-only, per-Pipeline-ID discovery timestamps for GEM JR and GEM.

First observed is a SCAN OBSERVATION date, not the original clinical readout,
FDA action, SEC filing, or stock purchase date. No historical first-seen dates
are inferred from old source files. Updates preserve existing first dates.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HISTORY_FILE = "gem_stage_first_seen.json"
STAGES = {"GEM_JR", "GEM"}
DATE_KEYS = {
    "GEM_JR": "first_seen_gem_jr",
    "GEM": "first_seen_gem",
}
FIRST_QUALIFIED_KEY = "first_qualified_gem"
PACIFIC = ZoneInfo("America/Los_Angeles")


def _date(value):
    try:
        result = date.fromisoformat(str(value or ""))
        return result.isoformat()
    except (ValueError, TypeError):
        return ""


def load_history(data_dir):
    path = Path(data_dir) / HISTORY_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError("GEM stage history unreadable; refusing to reset first-seen dates") from exc
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("records"), dict):
        raise ValueError("GEM stage history format invalid; refusing to reset first-seen dates")
    entries = data["records"]
    if not all(isinstance(k, str) and isinstance(v, dict) for k, v in entries.items()):
        raise ValueError("Invalid GEM stage history entry")
    for item in entries.values():
        for key in (*DATE_KEYS.values(), FIRST_QUALIFIED_KEY):
            if item.get(key) and not _date(item[key]):
                raise ValueError("Invalid first-seen date in history; refusing overwrite")
    return entries


def observe(data_dir, stage, rows, *, observed_on=None, validated_pipeline_ids=None):
    """Record stage entry without rewriting first observations.

    The scanner supplies canonical 'Pipeline ID' and issuer ticker from its
    existing source-identity gate. Rows outside a supplied Pipeline universe
    are ignored. Duplicate IDs under different tickers are rejected.
    """
    if stage not in STAGES:
        raise ValueError("Unknown GEM stage")
    when = observed_on or datetime.now(PACIFIC).date()
    if isinstance(when, datetime):
        raise ValueError("Use a Pacific calendar date")
    date_text = _date(when)
    if not date_text:
        raise ValueError("Invalid observation date")
    saved = load_history(data_dir)
    allowed = set(validated_pipeline_ids) if validated_pipeline_ids is not None else None
    first_key = DATE_KEYS[stage]
    changed = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        identifier = str(row.get("Pipeline ID") or "").strip()
        ticker = str(row.get("Ticker") or "").strip().upper()
        if not identifier or not ticker or not identifier.startswith(("TRIAL|", "APPLICATION|")):
            continue
        if allowed is not None and identifier not in allowed:
            continue
        previous = saved.get(identifier, {})
        if previous.get("ticker") and previous["ticker"] != ticker:
            raise ValueError("Pipeline ID changes ticker: " + identifier)
        if any(_date(previous.get(k)) > date_text for k in (*DATE_KEYS.values(), FIRST_QUALIFIED_KEY)
               if previous.get(k)):
            raise ValueError("Observation predates existing first-seen record")
        record = dict(previous)
        record["ticker"] = ticker
        if not record.get(first_key):
            record[first_key] = date_text
            changed += 1
        if stage == "GEM" and row.get("Two-benchmark eligible") is True and not record.get(FIRST_QUALIFIED_KEY):
            record[FIRST_QUALIFIED_KEY] = date_text
            changed += 1
        saved[identifier] = record
    if changed:
        target = Path(data_dir) / HISTORY_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "tracking_note": (
            "First observed on/after feature activation; no historic discovery dates inferred"
        ), "records": dict(sorted(saved.items()))}
        # Atomic file replacement; failed snapshots must not silently wipe history.
        with tempfile.NamedTemporaryFile("w", dir=target.parent, delete=False,
                                         encoding="utf-8") as tmp:
            name = tmp.name
            json.dump(payload, tmp, indent=2, sort_keys=True)
            tmp.write("\n")
        try:
            os.replace(name, target)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    return {"updated": changed, "observed": len(rows), "history_count": len(saved)}


def dates_for(history, pipeline_id):
    row = history.get(str(pipeline_id or ""), {})
    return {
        "GEM JR first found": row.get("first_seen_gem_jr", "") or "Not recorded",
        "GEM first found": row.get("first_seen_gem", "") or "Not recorded",
        "GEM first qualified": row.get("first_qualified_gem", "") or "Not recorded",
    }
