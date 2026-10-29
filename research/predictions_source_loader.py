"""Load externally generated trial snapshots into PREDICTIONS.

A snapshot must contain real trial rows with source URLs. This loader does not
run scans or modify original Pipeline/GEM JR/GEM/WT filters.
"""
from __future__ import annotations

import json
from pathlib import Path

from research.predictions_trial_source import build_prediction_candidates

FEEDS = ("phase3_released", "gem_jr", "gem", "wt")


def load_trial_snapshot(snapshot_path: str | Path) -> list[dict]:
    """Return deduplicated, sourced trial candidates from a JSON snapshot."""
    path = Path(snapshot_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Snapshot must be a JSON object")
    feeds = {}
    for name in FEEDS:
        rows = document.get(name, [])
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError(f"Invalid trial feed: {name}")
        feeds[name] = rows
    return build_prediction_candidates(**feeds)
