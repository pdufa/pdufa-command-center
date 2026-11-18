#!/usr/bin/env python3
"""Validate separate 2026 FDA application review cycles without claiming coverage."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data/2026-rp1-review-cycle-primary-source-crosswalk.csv"
REQUIRED = {"application_id","review_cycle","pdufa_goal_date","fda_action_date","fda_outcome","goal_source","action_source","assessment_type","l1_prediction"}

def validate(rows):
    errors, seen = [], set()
    for line, row in enumerate(rows, 2):
        missing = REQUIRED.difference(row)
        if missing:
            errors.append(f"line {line}: missing columns {sorted(missing)}")
            continue
        key = (row["application_id"], row["review_cycle"])
        if key in seen:
            errors.append(f"line {line}: duplicate application/review-cycle {key}")
        seen.add(key)
        if not row["goal_source"].startswith("https://") or not row["action_source"].startswith("https://"):
            errors.append(f"line {line}: missing primary-source links")
        if row["assessment_type"] == "OUTCOME_AWARE_REFERENCE" and row["l1_prediction"].strip():
            errors.append(f"line {line}: outcome-aware reference must not invent L1 prediction")
    return errors

if __name__ == "__main__":
    with PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    problems = validate(rows)
    print(f"RP1 review-cycle rows: {len(rows)}; distinct identities: {len(set((r.get('application_id'), r.get('review_cycle')) for r in rows))}")
    for problem in problems:
        print("ERROR:", problem)
    raise SystemExit(bool(problems))
