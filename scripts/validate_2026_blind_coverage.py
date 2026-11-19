#!/usr/bin/env python3
"""Validate historical L01-L06 assessment tracking without treating missing data as predictions.

Usage: python scripts/validate_2026_blind_coverage.py
Optional: --backlog PATH --coverage PATH --require-complete
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKLOG = ROOT / "data/backtest/2026-clinical-evidence-backlog.csv"
DEFAULT_COVERAGE = ROOT / "data/backtest/2026-level01-06-blind-assessment-coverage.csv"
LEVELS = {f"L{i:02d}" for i in range(1, 7)}
EXPOSURES = {"OBSERVED", "POTENTIAL", "NOT_DOCUMENTED"}
UNISSUED = "NOT_ISSUED"
UNLOCKED = "NOT_LOCKED"
UNSCORED = "NOT_SCORED"

def load(path, fields):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = set(fields) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)

def audit(backlog, coverage):
    errors = []
    by_id = {}
    for row in backlog:
        event_id = row["event_id"]
        if not event_id or event_id in by_id:
            errors.append(f"Missing/duplicate backlog event ID: {event_id!r}")
        by_id[event_id] = row
        if row["researcher_outcome_exposure"] not in EXPOSURES:
            errors.append(f"{event_id}: unknown exposure status")
    by_event = {}
    for row in coverage:
        event_id, level = row["event_id"], row["level"]
        if event_id not in by_id:
            errors.append(f"{event_id}/{level}: not present in backlog")
            continue
        if level not in LEVELS:
            errors.append(f"{event_id}/{level}: unexpected level")
        key = (event_id, level)
        if key in by_event:
            errors.append(f"{event_id}/{level}: duplicate")
        by_event[key] = row
        base = by_id[event_id]
        if row["researcher_outcome_exposure"] != base["researcher_outcome_exposure"]:
            errors.append(f"{event_id}/{level}: exposure mismatch")
        if row["event_eligibility"] != base["identity_status"]:
            errors.append(f"{event_id}/{level}: eligibility mismatch")
        if row["evidence_status"] != base["evidence_status"]:
            errors.append(f"{event_id}/{level}: evidence status mismatch")
        pred, lock, score = (row[k] for k in ("blind_prediction", "prediction_lock_status", "scoring_status"))
        if pred == UNISSUED and (lock != UNLOCKED or score != UNSCORED):
            errors.append(f"{event_id}/{level}: unissued prediction marked locked/scored")
        if score != UNSCORED and lock == UNLOCKED:
            errors.append(f"{event_id}/{level}: scored without prediction lock")
        if lock != UNLOCKED and row["researcher_outcome_exposure"] != "NOT_DOCUMENTED":
            errors.append(f"{event_id}/{level}: exposure-flagged candidate marked locked; independent review required")
    expected = {(event_id, level) for event_id in by_id for level in LEVELS}
    for event_id, level in sorted(expected - set(by_event)):
        errors.append(f"{event_id}/{level}: missing coverage row")
    exposure_counts = Counter(row["researcher_outcome_exposure"] for row in backlog)
    lock_counts = Counter(row["prediction_lock_status"] for row in coverage)
    score_counts = Counter(row["scoring_status"] for row in coverage)
    print(f"Candidates: {len(backlog)} | Level rows: {len(coverage)} | Expected level rows: {len(expected)}")
    print("Exposure: " + ", ".join(f"{k}={exposure_counts[k]}" for k in sorted(EXPOSURES)))
    print("Prediction locks: " + ", ".join(f"{k}={v}" for k, v in sorted(lock_counts.items())))
    print("Scoring: " + ", ".join(f"{k}={v}" for k, v in sorted(score_counts.items())))
    for error in errors:
        print("ERROR: " + error, file=sys.stderr)
    return errors, coverage

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backlog", type=Path, default=DEFAULT_BACKLOG)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--require-complete", action="store_true",
                        help="Fail until every level has a locked prediction and a score")
    args = parser.parse_args()
    try:
        backlog = load(args.backlog, ["event_id", "identity_status", "researcher_outcome_exposure", "evidence_status"])
        coverage = load(args.coverage, ["event_id", "level", "event_eligibility", "researcher_outcome_exposure",
                                        "evidence_status", "blind_prediction", "prediction_lock_status", "scoring_status"])
        errors, rows = audit(backlog, coverage)
        if args.require_complete:
            pending = sum(row["prediction_lock_status"] == UNLOCKED or row["scoring_status"] == UNSCORED for row in rows)
            if pending:
                errors.append(f"{pending} level records not both locked and scored")
                print("ERROR: " + errors[-1], file=sys.stderr)
        return 1 if errors else 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
