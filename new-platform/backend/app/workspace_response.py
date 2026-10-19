"""One prepared representation per immutable published-source snapshot.

Full responses bypass FastAPI's recursive per-request JSON conversion. Pages,
full loads and startup verification share permanent IDs and a content version.
The cache retains only the most recent source and its encoded response.
"""
from __future__ import annotations

import gzip
import json
import threading

_LOCK = threading.RLock()
_CACHE: dict = {"source": None, "snapshot": None, "raw": None, "gzip": None}


def prepared(source: dict) -> dict:
    from .program_registry import number_workspace
    from .workspace_delta import publish

    with _LOCK:
        if _CACHE["source"] is source and _CACHE["snapshot"] is not None:
            return _CACHE["snapshot"]
        snapshot = number_workspace(source)
        try:
            version = publish(snapshot)["version"]
        except ValueError:
            # Preserve explicit stale-source behavior, without ever assigning
            # a verified version or overwriting the last prepared response.
            return snapshot
        snapshot = {**snapshot, "workspaceVersion": version}
        _CACHE.update(source=source, snapshot=snapshot, raw=None, gzip=None)
        return snapshot


def encoded(source: dict, accept_encoding: str) -> tuple[bytes, bool]:
    with _LOCK:
        snapshot = prepared(source)
        cached = _CACHE["snapshot"] is snapshot
        raw = _CACHE["raw"] if cached else None
        if raw is None:
            raw = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")
            if cached:
                _CACHE["raw"] = raw
        accepts_gzip = False
        for part in accept_encoding.lower().split(","):
            coding, *parameters = part.strip().split(";")
            if coding != "gzip":
                continue
            try:
                quality = next((float(p.strip()[2:]) for p in parameters
                                if p.strip().startswith("q=")), 1.0)
            except ValueError:
                quality = 0.0
            accepts_gzip = quality > 0
        if not accepts_gzip:
            return raw, False
        compressed = _CACHE["gzip"] if cached else None
        if compressed is None:
            compressed = gzip.compress(raw, compresslevel=1, mtime=0)
            if cached:
                _CACHE["gzip"] = compressed
        return compressed, True
