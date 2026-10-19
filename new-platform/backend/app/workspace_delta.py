"""Bounded, process-local workspace change feed.

Version hashes are content-derived. A worker restart or unknown base version
returns a full-reset instruction rather than an unsafe partial patch.
"""
from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict

_LOCK = threading.Lock()
_HISTORY: OrderedDict[str, dict] = OrderedDict()
_MAX_VERSIONS = 3


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _index(rows):
    indexed = {}
    for row in rows:
        key = row.get("id") or row.get("programId")
        if not isinstance(key, str) or not key or key in indexed:
            raise ValueError("Workspace contains missing or duplicate record identity")
        indexed[key] = row
    return indexed


def _view(snapshot):
    if snapshot.get("mode") == "STALE_PREVIOUS_FETCH" or snapshot.get("sourceHealth", {}).get("state") == "STALE":
        raise ValueError("Stale published sources cannot be versioned as current")
    return {
        "PIPELINE": _index(snapshot["pipeline"]),
        "GEM_JR": _index(snapshot["members"]["GEM_JR"]["rows"]),
        "GEM": _index(snapshot["members"]["GEM"]["rows"]),
    }


def publish(snapshot, since=None):
    """Return either a complete-reset marker or changes against a known version."""
    current = _view(snapshot)
    # Fetch timestamps change every source poll even when no candidate changes.
    # Hash actual rows and stable stage membership metadata, not fetchedAt/asOf.
    stable = {
        "stages": current,
        "membership": {
            stage: {k: v for k, v in snapshot["members"][stage].items()
                    if k not in ("rows", "asOf")}
            for stage in ("GEM_JR", "GEM")
        },
    }
    digest = hashlib.sha256(_canonical(stable).encode("utf-8")).hexdigest()
    with _LOCK:
        previous = _HISTORY.get(since) if since else None
        _HISTORY[digest] = current
        _HISTORY.move_to_end(digest)
        while len(_HISTORY) > _MAX_VERSIONS:
            _HISTORY.popitem(last=False)
    if since == digest:
        return {"version": digest, "unchanged": True, "reset": False}
    if previous is None:
        return {"version": digest, "unchanged": False, "reset": True,
                "reason": "Unknown or expired base version; fetch full workspace"}
    changes = {}
    for stage in ("PIPELINE", "GEM_JR", "GEM"):
        before, after = previous[stage], current[stage]
        changes[stage] = {
            "upsert": [row for key, row in after.items()
                       if key not in before or _canonical(before[key]) != _canonical(row)],
            "remove": [key for key in before if key not in after],
            "count": len(after),
            "order": list(after),
        }
    return {"version": digest, "baseVersion": since, "unchanged": False,
            "reset": False, "changes": changes,
            "asOf": snapshot.get("asOf"),
            "membersMetadata": {
                stage: {key: value for key, value in snapshot["members"][stage].items() if key != "rows"}
                for stage in ("GEM_JR", "GEM")
            },
            "metadata": {key: value for key, value in snapshot.items()
                         if key not in ("pipeline", "members")}}
