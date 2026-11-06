"""Versioned Pipeline-only workspace change feed.

Old tier membership is not an active payload, input or version component.
Changes are fail-closed on stale sources or duplicate immutable identities.
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
    return {"PIPELINE": _index(snapshot["pipeline"])}


def publish(snapshot, since=None):
    """Return full reset on an unknown version, otherwise Pipeline-only changes."""
    current = _view(snapshot)
    fingerprints = {
        stage: {key: hashlib.sha256(_canonical(row).encode("utf-8")).hexdigest()
                for key, row in rows.items()}
        for stage, rows in current.items()
    }
    stable = {"stages": current, "order": {stage: list(rows) for stage, rows in current.items()}}
    digest = hashlib.sha256(_canonical(stable).encode("utf-8")).hexdigest()
    with _LOCK:
        previous = _HISTORY.get(since) if since else None
        _HISTORY[digest] = fingerprints
        _HISTORY.move_to_end(digest)
        while len(_HISTORY) > _MAX_VERSIONS:
            _HISTORY.popitem(last=False)
    if since == digest:
        return {"version": digest, "unchanged": True, "reset": False, "asOf": snapshot.get("asOf")}
    if previous is None:
        return {"version": digest, "unchanged": False, "reset": True,
                "reason": "Unknown or expired base version; fetch full workspace"}
    before, after = previous["PIPELINE"], current["PIPELINE"]
    changed = {
        "upsert": [row for key, row in after.items() if key not in before or before[key] != fingerprints["PIPELINE"][key]],
        "remove": [key for key in before if key not in after],
        "count": len(after),
        "order": list(after),
    }
    return {
        "version": digest, "baseVersion": since, "unchanged": False, "reset": False,
        "changes": {"PIPELINE": changed},
        "asOf": snapshot.get("asOf"),
        "metadata": {key: value for key, value in snapshot.items() if key != "pipeline"},
    }
