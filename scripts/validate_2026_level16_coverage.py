#!/usr/bin/env python3
"""Validate 2026 L01-L06 tracking coverage; never treat tracking rows as predictions."""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "data/backtest/2026-clinical-evidence-backlog.csv"
COVERAGE = ROOT / "data/backtest/2026-level01-06-blind-assessment-coverage.csv"
LEVELS = {f"L{i:02d}" for i in range(1, 7)}
FIELDS = ("event_id", "level", "event_eligibility", "researcher_outcome_exposure",
          "evidence_status", "blind_prediction", "prediction_lock_status",
          "scoring_status", "remaining_work")

def read(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

def validate():
    backlog, coverage = read(BACKLOG), read(COVERAGE)
    if not backlog or len({r["event_id"] for r in backlog}) != len(backlog):
        raise ValueError("Backlog empty or duplicate event IDs")
    if not coverage or tuple(coverage[0]) != FIELDS:
        raise ValueError("Coverage schema mismatch")
    source = {r["event_id"]: r for r in backlog}
    pairs = Counter((r["event_id"], r["level"]) for r in coverage)
    expected = {(event_id, level) for event_id in source for level in LEVELS}
    if set(pairs) != expected or any(n != 1 for n in pairs.values()):
        raise ValueError("Coverage must contain exactly one record per event and L01-L06")
    for row in coverage:
        src = source[row["event_id"]]
        if (row["event_eligibility"] != src["identity_status"]
            or row["researcher_outcome_exposure"] != src["researcher_outcome_exposure"]
            or row["evidence_status"] != src["evidence_status"]
            or row["remaining_work"] != src["remaining_work"]):
            raise ValueError("Coverage tracking drift: " + row["event_id"])
        if (row["blind_prediction"], row["prediction_lock_status"], row["scoring_status"]) != (
            "NOT_ISSUED", "NOT_LOCKED", "NOT_SCORED"):
            raise ValueError("Tracking cannot impersonate locked/scored predictions")
    print(f"Validated {len(source)} candidates and {len(coverage)} unscored level records")

if __name__ == "__main__":
    validate()
